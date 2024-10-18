import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import api.utils
from display_data import display_data_availability, display_filters, apply_filters, display_results, download_filtered_data

def select_date():
    min_date = datetime(2024, 10, 4).date()
    today = datetime.now().date()
    max_date = min(today, min_date + timedelta(days=30))
    default_date = today if today >= min_date and today <= max_date else min_date
    selected_date = st.date_input(
        "Select a date",
        value=default_date,
        min_value=min_date,
        max_value=max_date,
    )
    return selected_date

def select_time(selected_date):
    current_time = datetime.now().time()
    today = datetime.now().date()

    if selected_date < today:
        available_times = ["08:00", "12:00", "17:00"]
    else:
        available_time = get_closest_past_time(
            current_time, datetime(2024, 10, 4).date()
        )
        available_times = [
            t for t in ["08:00", "12:00", "17:00"] if t <= available_time
        ]

    if available_times:
        search_time = st.selectbox(
            "Select search time",
            options=available_times,
            index=len(available_times) - 1,
        )
        return search_time.split(":")[0]
    else:
        st.warning("No data available for the selected date and time.")
        return None

def get_closest_past_time(current_time, reference_date):
    times = ["08:00", "12:00", "17:00"]
    current_datetime = datetime.combine(reference_date, current_time)
    past_times = [t for t in times if datetime.strptime(t, "%H:%M").time() <= current_time]
    return max(past_times) if past_times else times[-1]

def load_data(selected_date, selected_hour):
    year, month, day = selected_date.year, selected_date.month, selected_date.day
    sources = ["do_you_spain", "holiday_autos", "rental_cars"]
    dataframes = []

    for source in sources:
        data = api.utils.get_request(f"/table={source}/limit=1000")
        if data:
            df = pd.DataFrame(data)
            df = df[
                (df['day'] == day) &
                (df['month'] == month) &
                (df['year'] == year) &
                (df['hour'] == int(selected_hour))
            ]
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

    if 'original_df' in st.session_state:
        display_data_availability(st.session_state.original_df)

        rental_period, selected_car_group, num_vehicles, selected_source = display_filters(st.session_state.original_df)
        filtered_df = apply_filters(st.session_state.original_df, rental_period, selected_car_group, selected_source, num_vehicles)

        display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
        download_filtered_data(filtered_df)
    else:
        st.write("Please pull data to see available rental periods.")

if __name__ == "__main__":
    main()
