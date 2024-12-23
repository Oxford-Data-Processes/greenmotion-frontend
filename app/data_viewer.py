import pandas as pd
import display_data
import streamlit as st
from datetime import datetime
import api.utils as api_utils
from aws_utils import logs, iam
import os
import re
import pytz


def select_date(input_label, max_value=True):
    today = datetime.now().date()
    selected_date = st.date_input(
        label=input_label,
        value=st.session_state.selected_date,
        max_value=today,
    )
    return selected_date


def select_time(restricted_times=True, key_suffix="", timezone="UTC"):
    # Set the timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)  # Get the current time in the specified timezone
    current_date = now.date()
    current_hour = now.hour
    available_times = []

    if st.session_state.selected_date < current_date:
        available_times = [
            "08:00",
            "12:00",
            "17:00",
        ]  # Show all available times for past dates
    elif st.session_state.selected_date == current_date:
        # Show only times that are in the past for today
        available_times = ["08:00"]  # Default to 08:00
        if current_hour >= 12:
            available_times.append("12:00")
        if current_hour >= 17:
            available_times.append("17:00")
    else:
        available_times = [
            f"{hour:02d}:00" for hour in range(6, 22)
        ]  # Show all times for future dates

    search_time = st.selectbox(
        "Select search time",
        options=available_times,
        index=len(available_times) - 1,
        key=f"search_time_{key_suffix}",
    )
    return str(search_time.split(":")[0])


def convert_json_to_df(json_data):
    return pd.DataFrame(json_data)


def load_data(search_datetime, pickup_datetime, dropoff_datetime, is_custom_search):
    site_names = ["do_you_spain", "rental_cars", "holiday_autos"]
    dataframes = []

    for site_name in site_names:
        if is_custom_search:
            formatted_pickup = (
                pickup_datetime.replace(" ", "T")
                if " " in pickup_datetime
                else pickup_datetime
            )
            formatted_dropoff = (
                dropoff_datetime.replace(" ", "T")
                if " " in dropoff_datetime
                else dropoff_datetime
            )

            api_url = f"/items/?table_name={site_name}&pickup_datetime={formatted_pickup}&dropoff_datetime={formatted_dropoff}&limit=10000"
            json_data = api_utils.get_request(api_url)

            if json_data:
                # Convert rental_period to numeric if it's 'custom'
                for item in json_data:
                    if item.get("rental_period") == "custom":
                        # Calculate rental period from pickup and dropoff dates
                        pickup = datetime.strptime(
                            item["pickup_datetime"], "%Y-%m-%dT%H:%M:%S"
                        )
                        dropoff = datetime.strptime(
                            item["dropoff_datetime"], "%Y-%m-%dT%H:%M:%S"
                        )
                        item["rental_period"] = (dropoff - pickup).days

                df = convert_json_to_df(json_data)
                if not df.empty:
                    # Ensure rental_period is numeric
                    df["rental_period"] = pd.to_numeric(
                        df["rental_period"], errors="coerce"
                    )
                    dataframes.append(df)
        else:
            formatted_search = (
                search_datetime.replace(" ", "T")
                if " " in search_datetime
                else search_datetime
            )
            api_url = f"/items/?table_name={site_name}&search_datetime={formatted_search}:00&limit=10000"
            json_data = api_utils.get_request(api_url)

            if json_data:
                df = convert_json_to_df(json_data)
                if not df.empty:
                    dataframes.append(df)

    if dataframes:
        final_df = pd.concat(dataframes, ignore_index=True)
        return final_df
    return pd.DataFrame()


def load_data_and_display(
    search_datetime, pickup_datetime=None, dropoff_datetime=None, is_custom_search=False
):
    with st.spinner("Loading data..."):
        df = load_data(
            search_datetime, pickup_datetime, dropoff_datetime, is_custom_search
        )

    if not df.empty:
        st.success("Data loaded successfully")

        # Clear existing session state
        if "df" in st.session_state:
            del st.session_state.df
        if "original_df" in st.session_state:
            del st.session_state.original_df

        # Update with new data
        st.session_state.df = df.copy()
        st.session_state.original_df = df.copy()

        # Store search parameters
        if is_custom_search:
            st.session_state.search_info = {
                "type": "Custom",
                "params": {"pickup": pickup_datetime, "dropoff": dropoff_datetime},
            }
        else:
            date, time = search_datetime.split("T")
            st.session_state.search_info = {
                "type": "Scheduled",
                "params": {"date": date, "time": time},
            }
    else:
        st.warning("No data available for the selected date and time.")


def handle_scheduled_search():
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = datetime.now().date()

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.selected_date = select_date(
            "Select search date", max_value=True
        )

    with col2:
        selected_hour = select_time(restricted_times=True, key_suffix="_scheduled")
        search_datetime = f"{st.session_state.selected_date}T{selected_hour}:00:00"

    if st.button("Load data"):
        st.session_state.data_loaded = True
        # Instead of calling load_data_and_display, we'll load the data directly
        with st.spinner("Loading data..."):
            df = load_data(search_datetime, None, None, False)

            if not df.empty:
                st.success("Data loaded successfully")

                # Clear existing session state
                if "df" in st.session_state:
                    del st.session_state.df
                if "original_df" in st.session_state:
                    del st.session_state.original_df

                # Update with new data
                st.session_state.df = df.copy()
                st.session_state.original_df = df.copy()

                # Store search parameters
                date, time = search_datetime.split("T")
                st.session_state.search_info = {
                    "type": "Scheduled",
                    "params": {"date": date, "time": time},
                }
            else:
                st.warning("No data available for the selected date and time.")
                return

    # Only display data once after loading or when filters are applied
    if "data_loaded" in st.session_state and st.session_state.data_loaded:
        if "df" in st.session_state and "search_info" in st.session_state:
            display_data.main(
                st.session_state.df,
                st.session_state.search_info["type"],
                st.session_state.search_info["params"],
            )


def get_recent_searches():
    """Get recent custom searches from logs"""
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    logs_handler = logs.LogsHandler()
    log_messages = logs_handler.get_logs(bucket_name, "frontend")

    # Filter for completed custom searches
    custom_searches = []
    for log in log_messages:
        if "CUSTOM_SEARCH_FINISHED" in log["action"]:
            # Extract datetime values using regex
            match = re.search(
                r"pickup_datetime=(.*?) \| dropoff_datetime=(.*?)$", log["action"]
            )
            if match:
                custom_searches.append(
                    {
                        "pickup": match.group(1),
                        "dropoff": match.group(2),
                        "display": f"{log['timestamp']}: Pickup {match.group(1)} - Dropoff {match.group(2)}",
                    }
                )

    # Sort by timestamp in reverse order (most recent first)
    custom_searches.sort(key=lambda x: x["display"], reverse=True)
    return custom_searches


def handle_custom_search():
    recent_searches = get_recent_searches()
    if not recent_searches:
        st.warning("No previous searches found")
        return

    selected_search = st.selectbox(
        "Select previous search",
        options=recent_searches,
        format_func=lambda x: x["display"],
    )
    pickup_datetime = selected_search["pickup"]
    dropoff_datetime = selected_search["dropoff"]

    if st.button("Load data"):
        st.session_state.data_loaded = True
        st.session_state.pickup_datetime = pickup_datetime
        st.session_state.dropoff_datetime = dropoff_datetime
        load_data_and_display(
            None,
            pickup_datetime,
            dropoff_datetime,
            is_custom_search=True,
        )

    if "data_loaded" in st.session_state and st.session_state.data_loaded:
        if "df" in st.session_state and "search_info" in st.session_state:
            display_data.main(
                st.session_state.df,
                st.session_state.search_info["type"],
                st.session_state.search_info["params"],
            )


def main():
    iam.get_aws_credentials(st.secrets["aws_credentials"])

    st.title("Data Viewer")

    search_type = st.radio("Search type", options=["Scheduled", "Custom"])

    if search_type == "Scheduled":
        handle_scheduled_search()
    elif search_type == "Custom":
        handle_custom_search()


if __name__ == "__main__":
    main()
