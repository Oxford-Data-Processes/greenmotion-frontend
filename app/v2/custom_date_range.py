import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from aws_utils import sqs
from display_data import (
    display_data_availability,
    display_filters,
    apply_filters,
    display_results,
    download_filtered_data,
)
import api
import time
import toml
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


import os
import requests


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


def trigger_workflow(site_name, pickup_datetime, dropoff_datetime):
    token = st.secrets["github"]["token"]
    branch_name = "development"
    location = "manchester"
    custom_config = "true"
    stage = "dev"
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


def load_data(pickup_datetime, dropoff_datetime):
    sqs_handler = sqs.SQSHandler()
    queue_url = "greenmotion-sqs-queue"
    sqs_handler.delete_all_sqs_messages(queue_url)

    suppliers = ["rental_cars", "do_you_spain", "holiday_autos"]
    dataframes = []

    rental_cars_found = False
    warning_placeholder = st.empty()
    while not rental_cars_found:
        warning_placeholder.warning("Waiting for rental_cars data...")
        messages = sqs_handler.get_all_sqs_messages(queue_url)
        for message in messages:
            if "rental_cars" in message["message"]:
                rental_cars_found = True
                break
        if not rental_cars_found:
            time.sleep(2)  # Wait for 5 seconds before checking again

    warning_placeholder.empty()  # Remove the warning message
    st.success("Data received. Loading...")

    # Now load the data for all suppliers
    for supplier in suppliers:
        data = api.utils.get_request(
            f"/items/?table_name={supplier}&pickup_datetime={pickup_datetime}&dropoff_datetime={dropoff_datetime}"
        )
        if data:
            df = pd.DataFrame(data)
            dataframes.append(df)

    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    st.title("Custom Date Range Search")

    pickup_datetime, dropoff_datetime = select_date_range()

    if st.button("Fetch Data"):
        with st.spinner("Loading data..."):
            site_names = ["rental_cars", "do_you_spain", "holiday_autos"]
            for site_name in site_names:
                trigger_workflow(site_name, pickup_datetime, dropoff_datetime)

            df = load_data(pickup_datetime, dropoff_datetime)

        if not df.empty:
            st.success("Data loaded successfully")
            st.session_state.custom_df = df
        else:
            st.warning("No data available for the selected date range.")
            return

    if "custom_df" in st.session_state:
        display_data_availability(st.session_state.custom_df)

        rental_period, selected_car_group, num_vehicles, selected_source = (
            display_filters(st.session_state.custom_df)
        )
        filtered_df = apply_filters(
            st.session_state.custom_df,
            rental_period,
            selected_car_group,
            selected_source,
        )

        display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
        download_filtered_data(filtered_df)
    else:
        st.write("Please fetch data to see available rental options.")


if __name__ == "__main__":
    main()
