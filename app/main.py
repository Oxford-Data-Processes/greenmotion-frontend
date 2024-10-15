# app/main.py
import streamlit as st
from datetime import datetime, timedelta
import os
import pytz
import pandas as pd
from auth import login, logout, get_credentials
from athena import run_athena_query, generate_custom_query
from s3 import read_car_groups_from_s3
from data_processing import (
    process_doyouspain_data,
    process_holidayautos_data,
    process_rentalcars_data,
    extract_available_dates,
    get_most_recent_date,
    filter_data_by_date,
    ensure_correct_data_types,
    get_available_periods,
    get_top_vehicles,
    trigger_lambda,
    get_all_sqs_messages,
)
from utils.data_utils import (
    standardize_column_names,
    rename_total_price,
    rename_supplier_column,
    clean_combined_data,
    reorder_columns,
    sort_dataframe,
    get_closest_past_time,
    TIMEZONE,
    combine_dataframes,
    get_top_vehicles,
    get_available_periods,
)
from ui import display_results, display_results_custom, display_top_vehicles_per_group

if st.secrets["aws"]["stage"] == "prod":
    role = "ProdAdminRole"
else:
    role = "DevAdminRole"

access_key_id, secret_access_key, session_token = get_credentials(
    st.secrets["aws"]["account_id"], role
)

os.environ["AWS_ACCESS_KEY_ID"] = access_key_id
os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key
os.environ["AWS_SESSION_TOKEN"] = session_token

# Set the page configuration
st.set_page_config(page_icon="💰", page_title="Greenmotion Manchester", layout="wide")

# Constants
aws_account_id = st.secrets["aws"]["account_id"]
CAR_GROUPS_S3_PATH = (
    f"s3://greenmotion-bucket-{aws_account_id}/car_groups/car_groups.csv"
)

# Check if the user is logged in
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Check if the user just logged in and force a rerun
if st.session_state.get("just_logged_in", False):
    st.session_state["just_logged_in"] = False
    st.rerun()


def generate_query(database, year, month, day, hour):
    query_template = """
        SELECT * FROM "{database}"."raw"
        WHERE cast(year as integer) = {year} AND cast(month as integer) = {month} AND cast(day as integer) = {day} AND hour = '{hour}';
    """
    return query_template.format(
        database=database, year=year, month=month, day=day, hour=hour
    )


def process_data(selected_date, selected_hour):
    year, month, day = selected_date.year, selected_date.month, selected_date.day

    query_doyouspain = generate_query("do_you_spain", year, month, day, selected_hour)
    df_doyouspain = run_athena_query("do_you_spain", query_doyouspain)

    query_holidayautos = generate_query(
        "holiday_autos", year, month, day, selected_hour
    )
    df_holidayautos = run_athena_query("holiday_autos", query_holidayautos)

    query_rentalcars = generate_query("rental_cars", year, month, day, selected_hour)
    df_rentalcars = run_athena_query("rental_cars", query_rentalcars)

    data_availability = {
        "do_you_spain": "Data available" if not df_doyouspain.empty else "No data",
        "holiday_autos": "Data available" if not df_holidayautos.empty else "No data",
        "rental_cars": "Data available" if not df_rentalcars.empty else "No data",
    }

    # Process available data
    car_groups = read_car_groups_from_s3()
    dataframes = []

    if not df_doyouspain.empty:
        df_doyouspain = process_doyouspain_data(df_doyouspain, car_groups)
        df_doyouspain = standardize_column_names(df_doyouspain)
        df_doyouspain = rename_total_price(df_doyouspain)
        df_doyouspain = rename_supplier_column(df_doyouspain)
        df_doyouspain["source"] = "doyouspain"
        dataframes.append(df_doyouspain)

    if not df_holidayautos.empty:
        df_holidayautos = process_holidayautos_data(df_holidayautos, car_groups)
        df_holidayautos = standardize_column_names(df_holidayautos)
        df_holidayautos = rename_total_price(df_holidayautos)
        df_holidayautos = rename_supplier_column(df_holidayautos)
        df_holidayautos["source"] = "holidayautos"
        dataframes.append(df_holidayautos)

    if not df_rentalcars.empty:
        df_rentalcars = process_rentalcars_data(df_rentalcars, car_groups)
        df_rentalcars = standardize_column_names(df_rentalcars)
        df_rentalcars = rename_total_price(df_rentalcars)
        df_rentalcars = rename_supplier_column(df_rentalcars)
        df_rentalcars["source"] = "rentalcars"
        dataframes.append(df_rentalcars)

    if not dataframes:
        return {
            "error": "No data available for any source",
            "data_availability": data_availability,
        }

    # Combine available dataframes
    df_combined = pd.concat(dataframes, ignore_index=True)
    df_combined = clean_combined_data(df_combined)
    df_combined = reorder_columns(df_combined)
    df_combined = sort_dataframe(df_combined)

    # Don't drop the columns here, keep them for internal logic
    return {"data": df_combined, "data_availability": data_availability}


def display_filters(filtered_df):
    rental_periods = get_available_periods(filtered_df)
    rental_periods_with_all = ["All"] + [
        int(period)
        for period in rental_periods
        if period != "All" and not pd.isna(period)
    ]
    # Sort the integer values and keep "All" at the beginning
    rental_periods_with_all = ["All"] + sorted(
        set(p for p in rental_periods_with_all if p != "All")
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rental_period = st.selectbox(
            "Select Rental Period (Days)", options=rental_periods_with_all
        )

    with col2:
        car_groups = ["All"] + sorted(filtered_df["car_group"].unique().tolist())
        selected_car_group = st.selectbox("Select Car Group", options=car_groups)

    with col3:
        num_vehicles_options = ["All"] + list(range(1, 21))
        num_vehicles = st.selectbox(
            "Select Number of Vehicles to Display",
            options=num_vehicles_options,
            index=3,
        )

    with col4:
        unique_sources = ["All"] + filtered_df["source"].unique().tolist()
        selected_source = st.selectbox("Select Source", options=unique_sources)

    return rental_period, selected_car_group, num_vehicles, selected_source


def main():
    st.title("Car Rental Data Analysis")

    # Check if the user is logged in
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # Check if the user just logged in and force a rerun
    if st.session_state.get("just_logged_in", False):
        st.session_state["just_logged_in"] = False
        st.rerun()

    if not st.session_state["logged_in"]:
        login()
    else:
        st.sidebar.button("Logout", on_click=logout, key="main_logout_button")

        tab1, tab2 = st.tabs(["Search by Date", "Custom Date Range"])

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                # Date selection
                min_date = datetime(2024, 10, 4).date()
                today = datetime.now(TIMEZONE).date()
                max_date = min(today, min_date + timedelta(days=30))

                # Use today's date as the default value
                default_date = (
                    today if today >= min_date and today <= max_date else min_date
                )
                selected_date = st.date_input(
                    "Select a date",
                    value=default_date,
                    min_value=min_date,
                    max_value=max_date,
                )

            with col2:
                # Time selection
                current_time = datetime.now(TIMEZONE).time()
                today = datetime.now(TIMEZONE).date()

                if selected_date < today:
                    available_times = ["08:00", "12:00", "17:00"]
                else:
                    available_time = get_closest_past_time(current_time, min_date)
                    available_times = [
                        t for t in ["08:00", "12:00", "17:00"] if t <= available_time
                    ]

                if available_times:
                    search_time = st.selectbox(
                        "Select search time",
                        options=available_times,
                        index=len(available_times)
                        - 1,  # Default to latest available time
                    )
                    selected_hour = search_time.split(":")[0]
                else:
                    st.warning("No data available for the selected date and time.")
                    selected_hour = None

            if "data_loaded" not in st.session_state:
                st.session_state.data_loaded = False

            if "last_selected_date" not in st.session_state:
                st.session_state.last_selected_date = selected_date

            if "last_selected_time" not in st.session_state:
                st.session_state.last_selected_time = selected_hour

            # Reset data_loaded flag if a new date or time is selected
            if (
                selected_date != st.session_state.last_selected_date
                or selected_hour != st.session_state.last_selected_time
            ):
                st.session_state.data_loaded = False
                st.session_state.last_selected_date = selected_date
                st.session_state.last_selected_time = selected_hour

            if selected_hour and st.button("Pull Data", key="pull_data_button"):
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

                        # Display data availability in a more organized way
                        st.subheader("Data Availability")
                        col1, col2, col3 = st.columns(3)
                        for i, (source, availability) in enumerate(
                            result["data_availability"].items()
                        ):
                            col = [col1, col2, col3][i]
                            with col:
                                if availability == "Data available":
                                    st.markdown(f"**{source}**: ✅")
                                else:
                                    st.markdown(f"**{source}**: ❌")

                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.session_state.data_loaded = False

            if st.session_state.data_loaded:
                df_combined = st.session_state.df_combined

                available_dates = extract_available_dates(df_combined)

                if not available_dates.empty:
                    most_recent_date = get_most_recent_date(available_dates)
                    df_combined = ensure_correct_data_types(df_combined)
                    filtered_df = filter_data_by_date(df_combined, selected_date)
                    if selected_date:
                        filtered_df = filter_data_by_date(df_combined, selected_date)
                        available_periods = get_available_periods(filtered_df)

                        if available_periods:
                            (
                                rental_period,
                                selected_car_group,
                                num_vehicles,
                                selected_source,
                            ) = display_filters(filtered_df)

                            if rental_period != "All":
                                filtered_df = filtered_df[
                                    filtered_df["rental_period"] == rental_period
                                ]

                            if selected_car_group != "All":
                                filtered_df = filtered_df[
                                    filtered_df["car_group"] == selected_car_group
                                ]

                            if not filtered_df.empty:
                                if selected_source != "All":
                                    filtered_df = filtered_df[
                                        filtered_df["source"] == selected_source
                                    ]

                                if num_vehicles == "All":
                                    num_vehicles = len(filtered_df)
                                else:
                                    num_vehicles = int(num_vehicles)

                                top_vehicles = get_top_vehicles(
                                    filtered_df, rental_period, num_vehicles
                                )

                                # Use the original filtered_df for display functions
                                display_results(
                                    top_vehicles,
                                    rental_period,
                                    filtered_df,
                                    selected_car_group,
                                )
                                display_top_vehicles_per_group(
                                    filtered_df,
                                    selected_car_group,
                                    rental_period,
                                    num_vehicles,
                                )

                                # Create a copy without the columns for download
                                download_df = filtered_df.drop(
                                    columns=["day", "month", "year", "hour"],
                                    errors="ignore",
                                )
                                st.download_button(
                                    label="Download Filtered Data as CSV",
                                    data=download_df.to_csv(index=False).encode(
                                        "utf-8"
                                    ),
                                    file_name="filtered_rental_comparison.csv",
                                    mime="text/csv",
                                )
                            else:
                                st.write("No data available for the selected filters.")
                        else:
                            st.write(
                                "No available rental periods for the selected date."
                            )
                else:
                    st.write("No available dates for selection.")
            else:
                st.write("Please pull data to see available rental periods.")

        with tab2:
            st.header("Custom Date Range Search")

            # Get today's date
            today = datetime.now().date()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                pickup_date = st.date_input(
                    "Pick-up Date",
                    value=today + timedelta(days=1),
                    min_value=today + timedelta(days=1),
                    key="custom_pickup_date",
                )
            with col2:
                pickup_time = st.time_input(
                    "Pick-up Time",
                    value=datetime.strptime("10:00", "%H:%M").time(),
                    step=timedelta(minutes=30),
                    key="custom_pickup_time",
                )

            with col3:
                # Set the default drop-off date to 3 days after the pick-up date
                default_dropoff_date = pickup_date + timedelta(days=3)
                dropoff_date = st.date_input(
                    "Drop-off Date",
                    value=default_dropoff_date,
                    min_value=pickup_date + timedelta(days=1),
                    key="custom_dropoff_date",
                )
            with col4:
                dropoff_time = st.time_input(
                    "Drop-off Time",
                    value=datetime.strptime("10:00", "%H:%M").time(),
                    step=timedelta(minutes=30),
                    key="custom_dropoff_time",
                )

            # Ensure drop-off date is always after pick-up date
            if dropoff_date <= pickup_date:
                dropoff_date = pickup_date + timedelta(days=3)
                st.warning(
                    "Drop-off date has been automatically set to 3 days after pick-up date."
                )

            pickup_datetime = datetime.combine(pickup_date, pickup_time)
            dropoff_datetime = datetime.combine(dropoff_date, dropoff_time)
            rental_period = dropoff_datetime - pickup_datetime
            days = rental_period.days
            hours, remainder = divmod(rental_period.seconds, 3600)
            minutes = remainder // 60
            st.info(f"Rental period: {days} days, {hours} hours, and {minutes} minutes")

            fetch_button = st.button(
                "Fetch Data",
                key="fetch_custom_date_button",
                disabled=("custom_df" in st.session_state),
            )

            if fetch_button:
                fetch_initiation_time = datetime.now(TIMEZONE)
                st.session_state.fetch_initiation_time = fetch_initiation_time
                with st.spinner("Fetching data..."):

                    pickup_date_str = pickup_date.strftime("%Y-%m-%d")
                    dropoff_date_str = dropoff_date.strftime("%Y-%m-%d")
                    pickup_time_str = pickup_time.strftime("%H:%M")
                    dropoff_time_str = dropoff_time.strftime("%H:%M")

                    pickup_datetime = f"{pickup_date_str}T{pickup_time_str}:00"
                    dropoff_datetime = f"{dropoff_date_str}T{dropoff_time_str}:00"

                    # Trigger lambda functions for each site

                    response_doyouspain = trigger_lambda(
                        "do_you_spain", pickup_datetime, dropoff_datetime
                    )
                    response_holidayautos = trigger_lambda(
                        "holiday_autos", pickup_datetime, dropoff_datetime
                    )
                    response_rentalcars = trigger_lambda(
                        "rental_cars", pickup_datetime, dropoff_datetime
                    )

                    # Check responses and handle accordingly
                    if (
                        response_doyouspain.status_code == 204
                        and response_holidayautos.status_code == 204
                        and response_rentalcars.status_code == 204
                    ):
                        st.success(
                            "Lambda functions triggered successfully for all sites."
                        )

                        # Get SQS messages
                        aws_account_id = st.secrets["aws"]["account_id"]
                        queue_url = f"https://sqs.eu-west-2.amazonaws.com/{aws_account_id}/greenmotion-sqs-queue"

                        with st.spinner("Waiting for SQS messages..."):
                            messages = get_all_sqs_messages(queue_url)

                        if messages:
                            st.success("Received SQS messages:")
                            for msg in messages:
                                st.write(f"Timestamp: {msg['timestamp']}")
                                st.write(f"Message: {msg['message']}")

                        if "fetch_initiation_time" in st.session_state:
                            fetch_time = st.session_state.fetch_initiation_time
                        else:
                            fetch_time = datetime.now(TIMEZONE)

                        # Generate and run queries for each source using the fetch initiation time
                        query_doyouspain = generate_custom_query(
                            "do_you_spain",
                            fetch_time,
                        )
                        query_holidayautos = generate_custom_query(
                            "holiday_autos",
                            fetch_time,
                        )
                        query_rentalcars = generate_custom_query(
                            "rental_cars",
                            fetch_time,
                        )

                        with st.spinner("Fetching data from Athena..."):
                            df_doyouspain = run_athena_query(
                                "do_you_spain", query_doyouspain
                            )
                            df_holidayautos = run_athena_query(
                                "holiday_autos", query_holidayautos
                            )
                            df_rentalcars = run_athena_query(
                                "rental_cars", query_rentalcars
                            )

                        # Load car_groups
                        car_groups = read_car_groups_from_s3()

                        # Process Do You Spain data
                        if not df_doyouspain.empty:
                            df_doyouspain = process_doyouspain_data(
                                df_doyouspain, car_groups
                            )
                            df_doyouspain = standardize_column_names(df_doyouspain)
                            df_doyouspain = rename_total_price(df_doyouspain)
                            df_doyouspain = rename_supplier_column(df_doyouspain)
                            df_doyouspain["source"] = "doyouspain"

                        # Process Holiday Autos data
                        if not df_holidayautos.empty:
                            df_holidayautos = process_holidayautos_data(
                                df_holidayautos, car_groups
                            )
                            df_holidayautos = standardize_column_names(df_holidayautos)
                            df_holidayautos = rename_total_price(df_holidayautos)
                            df_holidayautos = rename_supplier_column(df_holidayautos)
                            df_holidayautos["source"] = "holidayautos"
                        # Process Rental Cars data
                        if not df_rentalcars.empty:
                            df_rentalcars = process_rentalcars_data(
                                df_rentalcars, car_groups
                            )
                            df_rentalcars = standardize_column_names(df_rentalcars)
                            df_rentalcars = rename_total_price(df_rentalcars)
                            df_rentalcars = rename_supplier_column(df_rentalcars)
                            df_rentalcars["source"] = "rentalcars"
                        # Combine dataframes
                        all_columns = (
                            set(df_doyouspain.columns)
                            | set(df_holidayautos.columns)
                            | set(df_rentalcars.columns)
                        )
                        common_columns = list(
                            all_columns - {"source"}
                        )  # Exclude 'source' from common columns
                        df_combined = combine_dataframes(
                            df_doyouspain,
                            df_holidayautos,
                            df_rentalcars,
                            common_columns,
                        )

                        # Apply additional processing
                        df_combined = clean_combined_data(df_combined)
                        df_combined = reorder_columns(df_combined)
                        df_combined = sort_dataframe(df_combined)

                        st.session_state.custom_df = df_combined
                        st.success("Data fetched and processed successfully!")

                        # Display data availability
                        st.subheader("Data Availability")
                        col1, col2, col3 = st.columns(3)
                        sources = ["do_you_spain", "holiday_autos", "rental_cars"]
                        for i, source in enumerate(sources):
                            col = [col1, col2, col3][i]
                            with col:
                                if (
                                    (
                                        source == "do_you_spain"
                                        and not df_doyouspain.empty
                                    )
                                    or (
                                        source == "holiday_autos"
                                        and not df_holidayautos.empty
                                    )
                                    or (
                                        source == "rental_cars"
                                        and not df_rentalcars.empty
                                    )
                                ):
                                    st.markdown(f"**{source}**: ✅")
                                else:
                                    st.markdown(f"**{source}**: ❌")
                        else:
                            pass
                    else:
                        st.error(
                            "Error triggering one or more Lambda functions. Please check the logs."
                        )

            if "custom_df" in st.session_state:
                df_combined = st.session_state.custom_df

                # Calculate rental period
                pickup_datetime = datetime.combine(pickup_date, pickup_time)
                dropoff_datetime = datetime.combine(dropoff_date, dropoff_time)
                rental_period = (dropoff_datetime - pickup_datetime).days

                # Display filters
                col1, col2, col3 = st.columns(3)

                with col1:
                    car_groups = ["All"] + sorted(
                        df_combined["car_group"].unique().tolist()
                    )
                    selected_car_group = st.selectbox(
                        "Select Car Group", options=car_groups, key="custom_car_group"
                    )

                with col2:
                    num_vehicles_options = ["All"] + list(range(1, 21))
                    num_vehicles = st.selectbox(
                        "Select Number of Vehicles to Display",
                        options=num_vehicles_options,
                        index=3,
                        key="custom_num_vehicles",
                    )

                with col3:
                    unique_sources = ["All"] + df_combined["source"].unique().tolist()
                    selected_source = st.selectbox(
                        "Select Source", options=unique_sources, key="custom_source"
                    )

                # Filter data based on user selection
                filtered_df = df_combined.copy()

                if selected_car_group != "All":
                    filtered_df = filtered_df[
                        filtered_df["car_group"] == selected_car_group
                    ]

                if selected_source != "All":
                    filtered_df = filtered_df[filtered_df["source"] == selected_source]

                # Get top vehicles
                if num_vehicles == "All":
                    top_vehicles = filtered_df
                else:
                    num_vehicles = int(num_vehicles)
                    top_vehicles = (
                        filtered_df.groupby("car_group")
                        .apply(lambda x: x.nsmallest(num_vehicles, "total_price"))
                        .reset_index(drop=True)
                    )

                # Use the new display_results_custom function for Tab 2
                display_results_custom(
                    top_vehicles, rental_period, filtered_df, selected_car_group
                )

                # Add the graph below the results table
                display_top_vehicles_per_group(
                    filtered_df, selected_car_group, rental_period, num_vehicles
                )

                # Create a copy without the columns for download
                download_df = filtered_df.drop(
                    columns=["day", "month", "year", "hour"], errors="ignore"
                )
                st.download_button(
                    label="Download Filtered Data as CSV",
                    data=download_df.to_csv(index=False).encode("utf-8"),
                    file_name="filtered_rental_comparison_custom.csv",
                    mime="text/csv",
                )

            else:
                st.write("Click 'Fetch Data' to see available rental options.")


if __name__ == "__main__":
    main()
