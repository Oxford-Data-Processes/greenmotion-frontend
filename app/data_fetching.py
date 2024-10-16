import streamlit as st
from datetime import datetime
from athena import run_athena_query, generate_query, generate_custom_query
from s3 import read_car_groups_from_s3
from data_processing import trigger_lambda, get_all_sqs_messages, process_dataframe
from utils.data_utils import TIMEZONE, combine_dataframes_custom

def fetch_data(source, year, month, day, hour):
    query = generate_query(source, year, month, day, hour)
    return run_athena_query(source, query)

def fetch_data_custom(pickup_datetime, dropoff_datetime):
    fetch_initiation_time = datetime.now(TIMEZONE)
    st.session_state.fetch_initiation_time = fetch_initiation_time
    with st.spinner("Fetching data..."):
        pickup_datetime_str = pickup_datetime.isoformat()
        dropoff_datetime_str = dropoff_datetime.isoformat()

        response_doyouspain = trigger_lambda(
            "do_you_spain", pickup_datetime_str, dropoff_datetime_str
        )
        response_holidayautos = trigger_lambda(
            "holiday_autos", pickup_datetime_str, dropoff_datetime_str
        )
        response_rentalcars = trigger_lambda(
            "rental_cars", pickup_datetime_str, dropoff_datetime_str
        )

        if all(
            response.status_code == 204
            for response in [
                response_doyouspain,
                response_holidayautos,
                response_rentalcars,
            ]
        ):
            st.success("Lambda functions triggered successfully for all sites.")
            handle_sqs_messages()
            df_doyouspain, df_holidayautos, df_rentalcars = fetch_and_process_data()
            
            # Process the data
            car_groups = read_car_groups_from_s3()
            dataframes = []
            dataframes.extend(process_dataframe(df_doyouspain, car_groups, "doyouspain"))
            dataframes.extend(process_dataframe(df_holidayautos, car_groups, "holidayautos"))
            dataframes.extend(process_dataframe(df_rentalcars, car_groups, "rentalcars"))

            if dataframes:
                st.session_state.custom_df = combine_dataframes_custom(dataframes)
            else:
                st.error("No data available after processing.")
        else:
            st.error(
                "Error triggering one or more Lambda functions. Please check the logs."
            )

def handle_sqs_messages():
    aws_account_id = st.secrets["aws_credentials"]["AWS_ACCOUNT_ID"]
    queue_url = (
        f"https://sqs.eu-west-2.amazonaws.com/{aws_account_id}/greenmotion-sqs-queue"
    )

    with st.spinner("Waiting for SQS messages..."):
        messages = get_all_sqs_messages(queue_url)

    if messages:
        st.success("Data scraping completed successfully.")
    else:
        st.warning("No SQS messages received.")

def fetch_and_process_data():
    fetch_time = st.session_state.get("fetch_initiation_time", datetime.now(TIMEZONE))

    query_doyouspain = generate_custom_query("do_you_spain", fetch_time)
    query_holidayautos = generate_custom_query("holiday_autos", fetch_time)
    query_rentalcars = generate_custom_query("rental_cars", fetch_time)

    with st.spinner("Fetching data from Athena..."):
        df_doyouspain = run_athena_query("do_you_spain", query_doyouspain)
        df_holidayautos = run_athena_query("holiday_autos", query_holidayautos)
        df_rentalcars = run_athena_query("rental_cars", query_rentalcars)

    return df_doyouspain, df_holidayautos, df_rentalcars
