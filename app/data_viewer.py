import pandas as pd
import display_data
import streamlit as st
from datetime import datetime
import api.utils as api_utils
from aws_utils import logs, iam
import os
import re


def select_date(input_label, max_value=True):
    today = datetime.now().date()
    if max_value:
        selected_date = st.date_input(
            label=input_label,
            value=today,
            max_value=today,
        )
    else:
        selected_date = st.date_input(label=input_label, value=today)
    return selected_date


def select_time(restricted_times=True, key_suffix=""):
    if restricted_times:
        available_times = ["08:00", "12:00", "17:00"]
    else:
        available_times = [f"{hour:02d}:00" for hour in range(6, 22)]
    search_time = st.selectbox(
        "Select search time",
        options=available_times,
        index=len(available_times) - 1,
        key=f"search_time{key_suffix}",
    )
    return str(search_time.split(":")[0])


def convert_json_to_df(json_data):
    return pd.DataFrame(json_data)


def load_data(search_datetime, pickup_datetime, dropoff_datetime, is_custom_search):
    site_names = ["do_you_spain", "rental_cars", "holiday_autos"]
    dataframes = []

    for site_name in site_names:
        if is_custom_search:
            formatted_pickup = pickup_datetime.replace(" ", "T") if " " in pickup_datetime else pickup_datetime
            formatted_dropoff = dropoff_datetime.replace(" ", "T") if " " in dropoff_datetime else dropoff_datetime
            
            api_url = f"/items/?table_name={site_name}&pickup_datetime={formatted_pickup}:00&dropoff_datetime={formatted_dropoff}:00&limit=10000"
            json_data = api_utils.get_request(api_url)
        else:
            formatted_search = search_datetime.replace(" ", "T") if " " in search_datetime else search_datetime
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
        st.session_state.df = df.copy()
        display_data.main(df)
    else:
        st.warning("No data available for the selected date and time.")


def handle_scheduled_search():
    col1, col2 = st.columns(2)

    with col1:
        selected_date = select_date("Select search date", max_value=True)

    with col2:
        selected_hour = select_time(restricted_times=True, key_suffix="_scheduled")
        search_datetime = f"{selected_date}T{selected_hour}:00:00"

    if st.button("Load data"):
        load_data_and_display(search_datetime)


def get_recent_searches():
    """Get recent custom searches from logs"""
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    logs_handler = logs.LogsHandler()
    log_messages = logs_handler.get_logs(bucket_name, "frontend")
    
    # Filter for completed custom searches
    custom_searches = []
    for log in log_messages:
        if "CUSTOM_SEARCH_FINISHED" in log['action']:
            # Extract datetime values using regex
            match = re.search(r'pickup_datetime=(.*?) \| dropoff_datetime=(.*?)$', log['action'])
            if match:
                custom_searches.append({
                    'pickup': match.group(1),
                    'dropoff': match.group(2),
                    'display': f"{log['timestamp']}: Pickup {match.group(1)} - Dropoff {match.group(2)}"
                })
    
    # Sort by timestamp in reverse order (most recent first)
    custom_searches.sort(key=lambda x: x['display'], reverse=True)
    return custom_searches


def handle_custom_search():
    # Add radio selection for new search or previous search
    search_mode = st.radio("Search mode", ["New search", "Load previous search"])
    
    if search_mode == "New search":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            pickup_date = select_date("Select pickup date", max_value=False)
        with col2:
            pickup_time = select_time(restricted_times=False, key_suffix="_pickup")
            pickup_datetime = f"{pickup_date}T{pickup_time}:00:00"
        with col3:
            dropoff_date = select_date("Select dropoff date", max_value=False)
        with col4:
            dropoff_time = select_time(restricted_times=False, key_suffix="_dropoff")
            dropoff_datetime = f"{dropoff_date}T{dropoff_time}:00:00"
    else:
        # Show dropdown of recent searches
        recent_searches = get_recent_searches()
        if not recent_searches:
            st.warning("No previous searches found")
            return
            
        selected_search = st.selectbox(
            "Select previous search",
            options=recent_searches,
            format_func=lambda x: x['display']
        )
        pickup_datetime = selected_search['pickup']
        dropoff_datetime = selected_search['dropoff']

    if st.button("Load data"):
        load_data_and_display(
            None,
            pickup_datetime,
            dropoff_datetime,
            is_custom_search=True,
        )


def main():
    iam.get_aws_credentials(st.secrets["aws_credentials"])  # Add AWS credentials initialization
    st.title("Data Viewer")

    search_type = st.radio("Search type", options=["Custom", "Scheduled"])

    if search_type == "Scheduled":
        handle_scheduled_search()
    elif search_type == "Custom":
        handle_custom_search()


if __name__ == "__main__":
    main()
