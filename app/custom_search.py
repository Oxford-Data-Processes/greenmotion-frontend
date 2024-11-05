import os
import streamlit as st
from datetime import datetime, timedelta
import requests
import time
from aws_utils import sqs, iam, logs
import re

iam_instance = iam.IAM(stage=st.secrets["aws_credentials"]["STAGE"])
iam.AWSCredentials.get_aws_credentials(
    aws_access_key_id=st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID_ADMIN"],
    aws_secret_access_key=st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY_ADMIN"],
    iam_instance=iam_instance,
)


def transform_sns_messages(messages):
    all_messages = []
    for message in messages:
        timestamp = extract_datetime_from_sns_message(message["Body"])
        message_body = message["Body"]
        all_messages.append({"timestamp": timestamp, "message": message_body})
    all_messages.sort(key=lambda x: x["timestamp"])
    return all_messages


def extract_datetime_from_sns_message(message: str):
    match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", message)
    return match.group(0) if match else None


def select_time(label, restricted_times=True, key_suffix=""):
    if restricted_times:
        available_times = ["08:00", "12:00", "17:00"]
    else:
        available_times = [f"{hour:02d}:00" for hour in range(6, 22)]
    search_time = st.selectbox(
        label,
        options=available_times,
        index=len(available_times) - 1,
        key=f"search_time_{key_suffix}",  # Updated key to ensure uniqueness
    )
    return str(search_time.split(":")[0])


def select_date_range():
    today = datetime.now().date()
    default_pickup_date = today + timedelta(days=1)
    default_dropoff_date = default_pickup_date + timedelta(days=3)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pickup_date = st.date_input("Pick-up Date", value=default_pickup_date).strftime(
            "%Y-%m-%d"
        )
    with col2:
        pickup_time = select_time(
            "Pick-up Time", restricted_times=False, key_suffix="pickup"
        )
    with col3:
        dropoff_date = st.date_input(
            "Drop-off Date", value=default_dropoff_date
        ).strftime("%Y-%m-%d")
    with col4:
        dropoff_time = select_time(
            "Drop-off Time", restricted_times=False, key_suffix="dropoff"
        )

    pickup_datetime = f"{pickup_date}T{pickup_time}:00"
    dropoff_datetime = f"{dropoff_date}T{dropoff_time}:00"

    return pickup_datetime, dropoff_datetime


def trigger_github_actions(repository_name, workflow, branch_name, inputs, token):
    repository_full_name = f"Oxford-Data-Processes/{repository_name}"
    url = f"https://api.github.com/repos/{repository_full_name}/actions/workflows/{workflow}.yml/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    payload = {"ref": branch_name, "inputs": inputs}
    response = requests.post(url, headers=headers, json=payload)
    return response


def trigger_workflow(location, site_name, pickup_datetime, dropoff_datetime):
    token = st.secrets["github"]["token"]
    branch_name = st.secrets["github"]["branch_name"]
    custom_config = "true"
    stage = st.secrets["aws_credentials"]["STAGE"]
    repository_name = "greenmotion"
    workflow = f"trigger_workflow_{stage}"
    inputs = {
        "SITE_NAME": site_name,
        "LOCATION": location,
        "CUSTOM_CONFIG": custom_config,
        "PICKUP_DATETIME": pickup_datetime,
        "DROPOFF_DATETIME": dropoff_datetime,
    }

    response = trigger_github_actions(
        repository_name, workflow, branch_name, inputs, token
    )

    return response


def wait_for_data():
    sqs_handler = sqs.SQSHandler()
    queue_url = "greenmotion-lambda-queue"
    sqs_handler.delete_all_sqs_messages(queue_url)

    messages = sqs_handler.get_all_sqs_messages(queue_url)
    messages = transform_sns_messages(messages)

    rental_cars_found = False
    warning_placeholder = st.empty()
    while not rental_cars_found:
        warning_placeholder.warning("Waiting for rental_cars data...")
        messages = sqs_handler.get_all_sqs_messages(queue_url)
        messages = transform_sns_messages(messages)
        for message in messages:
            if "rental_cars" in message["message"]:
                rental_cars_found = True
                break
        if not rental_cars_found:
            time.sleep(5)

    warning_placeholder.empty()
    st.success("Custom search complete.")


def main():
    st.title("Custom Search")
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    location = "manchester"

    logs_handler = logs.LogsHandler()

    pickup_datetime, dropoff_datetime = select_date_range()

    if st.button("Trigger Custom Search"):
        with st.spinner("Loading data..."):
            site_names = [
                "do_you_spain",
                "holiday_autos",
                "rental_cars",
            ]
            for site_name in site_names:
                trigger_workflow(location, site_name, pickup_datetime, dropoff_datetime)

        st.success(
            f"Successfully triggered custom search with the following parameters: Pickup datetime: {pickup_datetime} | Dropoff datetime: {dropoff_datetime}"
        )
        logs_handler.log_action(
            bucket_name,
            "frontend",
            f"CUSTOM_SEARCH_TRIGGERED | pickup_datetime={pickup_datetime} | dropoff_datetime={dropoff_datetime}",
            "user_1",
        )
        wait_for_data()
        logs_handler.log_action(
            bucket_name,
            "frontend",
            f"CUSTOM_SEARCH_FINISHED | pickup_datetime={pickup_datetime} | dropoff_datetime={dropoff_datetime}",
            "user_1",
        )


if __name__ == "__main__":
    main()
