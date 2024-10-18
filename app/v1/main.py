import streamlit as st
from datetime import datetime, timedelta
import os
import pandas as pd
from auth import login, logout, get_credentials
from s3 import read_car_groups_from_s3
from data_processing import (
    process_doyouspain_data,
    process_holidayautos_data,
    process_rentalcars_data,
)
from utils.data_utils import (
    standardize_column_names,
    extract_available_dates,
    rename_total_price,
    rename_supplier_column,
    clean_combined_data,
    reorder_columns,
    sort_dataframe,
    TIMEZONE,
    combine_dataframes,
    get_most_recent_date,
    filter_data_by_date,
    ensure_correct_data_types,
    get_available_periods,
)
from date_selection import (
    select_date,
    select_time,
    get_date_time_inputs,
    validate_dropoff_date,
    calculate_rental_period,
)
from data_fetching import (
    fetch_data,
    fetch_data_custom,
    handle_sqs_messages,
    fetch_and_process_data,
)
from filters import display_filters, apply_filters
from results_display import (
    display_results_and_download,
    display_filtered_results,
    display_data_availability,
    display_data_availability_custom,
)
from aws_setup import setup_aws_credentials

# Set up AWS credentials and get the account ID
aws_account_id = setup_aws_credentials()

# Set the page configuration
st.set_page_config(page_icon="💰", page_title="Greenmotion Manchester", layout="wide")

# Constants
CAR_GROUPS_S3_PATH = (
    f"s3://greenmotion-bucket-{aws_account_id}/car_groups/car_groups.csv"
)


def process_data(selected_date, selected_hour):
    year, month, day = selected_date.year, selected_date.month, selected_date.day

    df_doyouspain = fetch_data("do_you_spain", year, month, day, selected_hour)
    df_holidayautos = fetch_data("holiday_autos", year, month, day, selected_hour)
    df_rentalcars = fetch_data("rental_cars", year, month, day, selected_hour)

    data_availability = {
        "do_you_spain": "Data available" if not df_doyouspain.empty else "No data",
        "holiday_autos": "Data available" if not df_holidayautos.empty else "No data",
        "rental_cars": "Data available" if not df_rentalcars.empty else "No data",
    }

    car_groups = read_car_groups_from_s3()
    dataframes = []

    dataframes.extend(process_dataframe(df_doyouspain, car_groups, "doyouspain"))
    dataframes.extend(process_dataframe(df_holidayautos, car_groups, "holidayautos"))
    dataframes.extend(process_dataframe(df_rentalcars, car_groups, "rentalcars"))

    if not dataframes:
        return {
            "error": "No data available for any source",
            "data_availability": data_availability,
        }

    df_combined = combine_dataframes_custom(dataframes)
    return {"data": df_combined, "data_availability": data_availability}


def process_dataframe(df, car_groups, source):
    if df.empty:
        return []

    try:
        processed_df = process_data_by_source(df, car_groups, source)
        if processed_df.empty:
            return []
        return [processed_df]
    except Exception as e:
        st.error(f"Error in process_dataframe for {source}: {str(e)}")
        return []


def process_data_by_source(df, car_groups, source):
    try:
        if source == "doyouspain":
            df = process_doyouspain_data(df, car_groups)
        elif source == "holidayautos":
            df = process_holidayautos_data(df, car_groups)
        elif source == "rentalcars":
            df = process_rentalcars_data(df, car_groups)
        else:
            st.error(f"Unknown source: {source}")
            return pd.DataFrame()

        df = standardize_column_names(df)
        df = rename_total_price(df)
        df = rename_supplier_column(df)
        df["source"] = source

        return df
    except Exception as e:
        st.error(f"Error processing data for {source}: {str(e)}")
        return pd.DataFrame()


def combine_dataframes_custom(dataframes):
    df_combined = pd.concat(dataframes, ignore_index=True)
    df_combined = clean_combined_data(df_combined)
    df_combined = reorder_columns(df_combined)
    df_combined = sort_dataframe(df_combined)
    return df_combined


def search_by_date(tab1):
    col1, col2 = st.columns(2)
    with col1:
        selected_date = select_date(col1)
    with col2:
        selected_hour = select_time(col2, selected_date)

    initialize_session_state(selected_date, selected_hour)

    if selected_hour and st.button("Pull Data", key="pull_data_button"):
        load_data(selected_date, selected_hour)

    if st.session_state.data_loaded:
        process_loaded_data(selected_date)
    else:
        st.write("Please pull data to see available rental periods.")


def initialize_session_state(selected_date, selected_hour):
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

    if "last_selected_date" not in st.session_state:
        st.session_state.last_selected_date = selected_date

    if "last_selected_time" not in st.session_state:
        st.session_state.last_selected_time = selected_hour

    if (
        selected_date != st.session_state.last_selected_date
        or selected_hour != st.session_state.last_selected_time
    ):
        st.session_state.data_loaded = False
        st.session_state.last_selected_date = selected_date
        st.session_state.last_selected_time = selected_hour


def load_data(selected_date, selected_hour):
    with st.spinner("Loading data..."):
        try:
            result = process_data(selected_date, selected_hour)
            if "error" in result:
                st.error(f"An error occurred: {result['error']}")
                st.session_state.data_loaded = False
            else:
                st.session_state.df_combined = result["data"]
                st.session_state.data_loaded = True
                st.success("Data loaded successfully")
                display_data_availability_custom(result["data_availability"])

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.session_state.data_loaded = False


def process_loaded_data(selected_date):
    df_combined = st.session_state.df_combined
    available_dates = extract_available_dates(df_combined)

    if not available_dates.empty:
        most_recent_date = get_most_recent_date(available_dates)
        df_combined = ensure_correct_data_types(df_combined)
        filtered_df = filter_data_by_date(df_combined, selected_date)

        if selected_date:
            available_periods = get_available_periods(filtered_df)

            if available_periods:
                rental_period, selected_car_group, num_vehicles, selected_source = (
                    display_filters(filtered_df)
                )

                filtered_df = apply_filters(
                    filtered_df,
                    rental_period,
                    selected_car_group,
                    selected_source,
                    num_vehicles,
                )

                if not filtered_df.empty:
                    display_results_and_download(
                        filtered_df, rental_period, selected_car_group, num_vehicles
                    )
                else:
                    st.write("No data available for the selected filters.")
            else:
                st.write("No available rental periods for the selected date.")
    else:
        st.write("No available dates for selection.")


def custom_date_range(tab2):
    st.header("Custom Date Range Search")
    today = datetime.now().date()

    pickup_date, pickup_time, dropoff_date, dropoff_time = get_date_time_inputs(today)

    validate_dropoff_date(pickup_date, dropoff_date)

    rental_period, pickup_datetime, dropoff_datetime = calculate_rental_period(
        pickup_date, pickup_time, dropoff_date, dropoff_time
    )

    st.info(
        f"Rental period: {rental_period['days']} days, {rental_period['hours']} hours, and {rental_period['minutes']} minutes"
    )

    dates_changed = check_if_dates_changed(
        pickup_date, pickup_time, dropoff_date, dropoff_time
    )

    if "fetching_data" not in st.session_state:
        st.session_state.fetching_data = False

    fetch_button = st.button(
        "Fetch Data",
        key="fetch_custom_date_button",
        disabled=(not dates_changed and "custom_df" in st.session_state)
        or st.session_state.fetching_data,
    )

    if fetch_button:
        st.session_state.fetching_data = True
        fetch_data_custom(pickup_datetime, dropoff_datetime)
        st.session_state.fetching_data = False

    if "custom_df" in st.session_state:
        display_filtered_results(pickup_date, pickup_time, dropoff_date, dropoff_time)
    else:
        st.write("No custom data available. Please fetch data first.")


def check_if_dates_changed(pickup_date, pickup_time, dropoff_date, dropoff_time):
    if "last_pickup_date" not in st.session_state:
        st.session_state.last_pickup_date = pickup_date
        st.session_state.last_pickup_time = pickup_time
        st.session_state.last_dropoff_date = dropoff_date
        st.session_state.last_dropoff_time = dropoff_time
        return True

    dates_changed = (
        pickup_date != st.session_state.last_pickup_date
        or pickup_time != st.session_state.last_pickup_time
        or dropoff_date != st.session_state.last_dropoff_date
        or dropoff_time != st.session_state.last_dropoff_time
    )

    if dates_changed:
        st.session_state.last_pickup_date = pickup_date
        st.session_state.last_pickup_time = pickup_time
        st.session_state.last_dropoff_date = dropoff_date
        st.session_state.last_dropoff_time = dropoff_time

    return dates_changed


def main():
    st.title("Car Rental Data Analysis")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state.get("just_logged_in", False):
        st.session_state["just_logged_in"] = False
        st.rerun()

    if not st.session_state["logged_in"]:
        login()
    else:
        st.sidebar.button("Logout", on_click=logout, key="main_logout_button")

        tab1, tab2 = st.tabs(["Search by Date", "Custom Date Range"])

        with tab1:
            search_by_date(tab1)

        with tab2:
            custom_date_range(tab2)


if __name__ == "__main__":
    main()
