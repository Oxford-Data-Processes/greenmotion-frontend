import pandas as pd
import display_data
import streamlit as st
from datetime import datetime
import api.utils as api_utils


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
            json_data = api_utils.get_request(
                f"/items/?table_name={site_name}&pickup_datetime={pickup_datetime}&dropoff_datetime={dropoff_datetime}&limit=10000"
            )
            df = convert_json_to_df(json_data)
        else:
            json_data = api_utils.get_request(
                f"/items/?table_name={site_name}&search_datetime={search_datetime}&limit=10000"
            )
            df = convert_json_to_df(json_data)
        dataframes.append(df)

    return pd.concat(dataframes, ignore_index=True)


def load_data_and_display(
    search_datetime, pickup_datetime=None, dropoff_datetime=None, is_custom_search=False
):
    with st.spinner("Loading data..."):
        df = load_data(
            search_datetime, pickup_datetime, dropoff_datetime, is_custom_search
        )

    if not df.empty:
        st.success("Data loaded successfully")
        st.session_state.df = df
        display_data.main(st.session_state.df)
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


def handle_custom_search():
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

    if st.button("Load data"):
        load_data_and_display(
            None,
            pickup_datetime,
            dropoff_datetime,
            is_custom_search=True,
        )


def main():
    st.title("Data Viewer")

    search_type = st.radio("Search type", options=["Custom", "Scheduled"])

    if search_type == "Scheduled":
        handle_scheduled_search()
    elif search_type == "Custom":
        handle_custom_search()


if __name__ == "__main__":
    main()
