import streamlit as st
from datetime import datetime, timedelta
from utils.data_utils import TIMEZONE, get_closest_past_time

def select_date(column):
    min_date = datetime(2024, 10, 4).date()
    today = datetime.now(TIMEZONE).date()
    max_date = min(today, min_date + timedelta(days=30))
    default_date = today if today >= min_date and today <= max_date else min_date
    selected_date = st.date_input(
        "Select a date",
        value=default_date,
        min_value=min_date,
        max_value=max_date,
    )
    return selected_date

def select_time(column, selected_date):
    current_time = datetime.now(TIMEZONE).time()
    today = datetime.now(TIMEZONE).date()

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

def get_date_time_inputs(today):
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

    return pickup_date, pickup_time, dropoff_date, dropoff_time

def validate_dropoff_date(pickup_date, dropoff_date):
    if dropoff_date <= pickup_date:
        dropoff_date = pickup_date + timedelta(days=3)
        st.warning(
            "Drop-off date has been automatically set to 3 days after pick-up date."
        )

def calculate_rental_period(pickup_date, pickup_time, dropoff_date, dropoff_time):
    pickup_datetime = datetime.combine(pickup_date, pickup_time)
    dropoff_datetime = datetime.combine(dropoff_date, dropoff_time)
    rental_period = dropoff_datetime - pickup_datetime
    days = rental_period.days
    hours, remainder = divmod(rental_period.seconds, 3600)
    minutes = remainder // 60

    return (
        {"days": days, "hours": hours, "minutes": minutes},
        pickup_datetime,
        dropoff_datetime,
    )