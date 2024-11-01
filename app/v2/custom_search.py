import streamlit as st
from datetime import datetime, timedelta
import requests


def select_date_range():
    today = datetime.now().date()
    default_pickup_date = today + timedelta(days=1)
    default_dropoff_date = default_pickup_date + timedelta(days=3)
    default_time = datetime.strptime("10:00", "%H:%M").time()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pickup_date = st.date_input(
            "Pick-up Date", value=default_pickup_date, min_value=today
        )
    with col2:
        pickup_time = st.time_input("Pick-up Time", value=default_time)
    with col3:
        dropoff_date = st.date_input(
            "Drop-off Date", value=default_dropoff_date, min_value=pickup_date
        )
    with col4:
        dropoff_time = st.time_input("Drop-off Time", value=default_time)

    pickup_datetime = datetime.combine(pickup_date, pickup_time).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    dropoff_datetime = datetime.combine(dropoff_date, dropoff_time).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
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


def main():
    st.title("Custom Search")
    location = "manchester"

    pickup_datetime, dropoff_datetime = select_date_range()

    if st.button("Trigger Web Scraping"):
        with st.spinner("Loading data..."):
            site_names = [
                "do_you_spain",
                "holiday_autos",
                "rental_cars",
            ]
            for site_name in site_names:
                trigger_workflow(location, site_name, pickup_datetime, dropoff_datetime)


if __name__ == "__main__":
    main()
