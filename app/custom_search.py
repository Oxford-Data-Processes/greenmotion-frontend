import os
import streamlit as st
from datetime import datetime, timedelta
import requests
import time
from aws_utils import sqs, iam, logs
import re


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
    # Get current datetime and set defaults (3 days from now at 10:00)
    now = datetime.now()
    default_pickup_date = now.date() + timedelta(days=3)
    default_dropoff_date = default_pickup_date + timedelta(days=3)
    default_time = "10:00"

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pickup_date = st.date_input(
            "Pick-up Date",
            value=default_pickup_date,
            min_value=now.date(),
            key="pickup_date"
        )
    
    with col2:
        pickup_time = st.selectbox(
            "Pick-up Time",
            options=[f"{hour:02d}:00" for hour in range(6, 22)],
            index=[i for i, t in enumerate([f"{hour:02d}:00" for hour in range(6, 22)]) if t == default_time][0],
            key="pickup_time"
        )
    
    # Only adjust dropoff date if pickup date would make it invalid
    if 'dropoff_date' not in st.session_state:
        dropoff_value = default_dropoff_date
    else:
        current_dropoff = st.session_state.dropoff_date
        if pickup_date >= current_dropoff:
            dropoff_value = pickup_date + timedelta(days=3)
        else:
            dropoff_value = current_dropoff
    
    with col3:
        dropoff_date = st.date_input(
            "Drop-off Date",
            value=dropoff_value,
            min_value=pickup_date,
            key="dropoff_date"
        )
    
    with col4:
        dropoff_time = st.selectbox(
            "Drop-off Time",
            options=[f"{hour:02d}:00" for hour in range(6, 22)],
            index=[i for i, t in enumerate([f"{hour:02d}:00" for hour in range(6, 22)]) if t == default_time][0],
            key="dropoff_time"
        )

    # Create datetime objects for validation
    pickup_datetime_obj = datetime.combine(pickup_date, datetime.strptime(pickup_time, "%H:%M").time())
    dropoff_datetime_obj = datetime.combine(dropoff_date, datetime.strptime(dropoff_time, "%H:%M").time())
    
    # Calculate rental period
    rental_period = (dropoff_datetime_obj - pickup_datetime_obj).days
    st.info(f"Rental Period: {rental_period} days")
    
    # Validate dates and times
    if pickup_datetime_obj < now:
        st.error("Pick-up date and time cannot be in the past")
        return None, None
        
    if dropoff_datetime_obj <= pickup_datetime_obj:
        st.error("Drop-off date and time must be after pick-up date and time")
        return None, None

    # Format datetimes for API
    pickup_datetime = f"{pickup_date}T{pickup_time}"
    dropoff_datetime = f"{dropoff_date}T{dropoff_time}"

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
            time.sleep(2)

    warning_placeholder.empty()
    st.success("Custom search complete.")


def main():
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    st.title("Custom Search")
    
    # Add prominent warning at the top
    st.warning("""
        ⚠️ IMPORTANT: Please remain on this page until the search is complete.
        The process may take a few minutes. You will see a success message when it's done.
    """)
    
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    location = "manchester"

    logs_handler = logs.LogsHandler()

    pickup_datetime, dropoff_datetime = select_date_range()

    if st.button("Trigger Custom Search"):
        # Create a placeholder for the progress messages
        progress_placeholder = st.empty()
        
        with st.spinner("Loading data..."):
            site_names = [
                "do_you_spain",
                "holiday_autos",
                "rental_cars",
            ]
            
            progress_placeholder.info("""
                🔄 Search initiated! Please do not close or leave this page.
                
                Current status:
                - Triggering searches for multiple sites
                - Waiting for data collection
                - This process typically takes 2-3 minutes
            """)
            
            for site_name in site_names:
                trigger_workflow(location, site_name, pickup_datetime, dropoff_datetime)

        logs_handler.log_action(
            bucket_name,
            "frontend",
            f"CUSTOM_SEARCH_TRIGGERED | pickup_datetime={pickup_datetime} | dropoff_datetime={dropoff_datetime}",
            "user_1",
        )
        
        # Update progress message
        progress_placeholder.info("""
            🔄 Searches triggered successfully!
            
            Current status:
            - Waiting for data collection
            - Please remain on this page
            - You will see a success message when complete
        """)
        
        wait_for_data()
        
        # Clear the progress messages
        progress_placeholder.empty()
        
        # Show final success message
        st.success("""
            ✅ Custom search complete! 
            
            All data has been collected successfully.
            You can now proceed to the Data Viewer to see the results.
        """)
        
        logs_handler.log_action(
            bucket_name,
            "frontend",
            f"CUSTOM_SEARCH_FINISHED | pickup_datetime={pickup_datetime} | dropoff_datetime={dropoff_datetime}",
            "user_1",
        )


if __name__ == "__main__":
    main()
