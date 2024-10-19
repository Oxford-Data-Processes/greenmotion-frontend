import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import pytz
from aws_utils.sqs import SQSHandler
from aws_utils.s3 import S3Handler
from display_data import display_data_availability, display_filters, apply_filters, display_results, download_filtered_data
import api

def select_date_range():
    today = datetime.now().date()
    default_pickup_date = today + timedelta(days=1)
    default_dropoff_date = default_pickup_date + timedelta(days=3)
    default_time = datetime.strptime("10:00", "%H:%M").time()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pickup_date = st.date_input("Pick-up Date", value=default_pickup_date, min_value=today)
    with col2:
        pickup_time = st.time_input("Pick-up Time", value=default_time)
    with col3:
        dropoff_date = st.date_input("Drop-off Date", value=default_dropoff_date, min_value=pickup_date)
    with col4:
        dropoff_time = st.time_input("Drop-off Time", value=default_time)

    pickup_datetime = datetime.combine(pickup_date, pickup_time)
    dropoff_datetime = datetime.combine(dropoff_date, dropoff_time)
    rental_period = (dropoff_datetime - pickup_datetime).days

    st.info(f"Rental period: {rental_period} days, {(dropoff_datetime - pickup_datetime).seconds // 3600} hours, and {((dropoff_datetime - pickup_datetime).seconds % 3600) // 60} minutes")

    return pickup_datetime, dropoff_datetime, rental_period

def trigger_lambdas(pickup_datetime, dropoff_datetime):
    # Mock function to simulate triggering lambdas
    st.info("Triggering lambdas for rental sites...")
    # In the future, implement actual lambda triggering here

def load_data(pickup_datetime, dropoff_datetime):
    suppliers = ["rental_cars", "do_you_spain", "holiday_autos"]
    dataframes = []

    start_date = pickup_datetime.strftime("%Y-%m-%d")
    end_date = dropoff_datetime.strftime("%Y-%m-%d")

    for supplier in suppliers:
        data = api.utils.get_request(f"/table={supplier}/start_date={start_date}/end_date={end_date}")
        if data:
            df = pd.DataFrame(data)
            df['source'] = supplier  # Add a 'source' column to identify the supplier
            dataframes.append(df)

    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        return pd.DataFrame()

def main():
    st.title("Custom Date Range Search")

    pickup_datetime, dropoff_datetime, rental_period = select_date_range()

    if st.button("Fetch Data"):
        with st.spinner("Loading data..."):
            df = load_data(pickup_datetime, dropoff_datetime)

        if not df.empty:
            st.success("Data loaded successfully")
            st.session_state.custom_df = df
        else:
            st.warning("No data available for the selected date range.")
            return

    if 'custom_df' in st.session_state:
        display_data_availability(st.session_state.custom_df)

        rental_period, selected_car_group, num_vehicles, selected_source = display_filters(st.session_state.custom_df)
        filtered_df = apply_filters(st.session_state.custom_df, rental_period, selected_car_group, selected_source, num_vehicles)

        display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
        download_filtered_data(filtered_df)
    else:
        st.write("Please fetch data to see available rental options.")

if __name__ == "__main__":
    main()
