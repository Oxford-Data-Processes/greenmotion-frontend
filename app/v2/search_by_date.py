import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import api.utils
from display_data import (
    display_data_availability,
    display_filters,
    apply_filters,
    display_results,
    download_filtered_data,
)


def select_date():
    today = datetime.now().date()
    selected_date = st.date_input(
        "Select a date",
        value=today,
        max_value=today,
    )
    return selected_date


def select_time(selected_date):
    today = datetime.now().date()
    if selected_date <= today:
        available_times = ["08:00", "12:00", "17:00"]
        search_time = st.selectbox(
            "Select search time",
            options=available_times,
            index=len(available_times) - 1,
        )
        return str(search_time.split(":")[0])
    else:
        st.warning("No data available for the selected date and time.")
        return None


def load_data(selected_date, selected_hour):
    search_datetime = f"{selected_date}T{selected_hour}:00:00"
    sources = ["do_you_spain", "holiday_autos", "rental_cars"]
    dataframes = []

    for source in sources:
        data = api.utils.get_request(
            f"/items/?table_name={source}&search_datetime={search_datetime}"
        )
        if data:
            df = pd.DataFrame(data)
            if not df.empty:
                dataframes.append(df)

    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    st.title("Search by Date")

    col1, col2 = st.columns(2)

    with col1:
        selected_date = select_date()

    with col2:
        selected_hour = select_time(selected_date)

    if selected_hour and st.button("Pull Data"):
        with st.spinner("Loading data..."):
            df = load_data(selected_date, selected_hour)

        if not df.empty:
            st.success("Data loaded successfully")
            st.session_state.original_df = df
        else:
            st.warning("No data available for the selected date and time.")
            return

    if "original_df" in st.session_state:
        display_data_availability(st.session_state.original_df)

        rental_period, selected_car_group, num_vehicles, selected_source = (
            display_filters(st.session_state.original_df)
        )
        filtered_df = apply_filters(
            st.session_state.original_df,
            rental_period,
            selected_car_group,
            selected_source,
        )

        display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
        download_filtered_data(filtered_df)
    else:
        st.write("Please pull data to see available rental periods.")


if __name__ == "__main__":
    main()
