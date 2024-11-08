import streamlit as st
from datetime import datetime
import pytz

def select_date(input_label, max_value=True):
    today = datetime.now().date()
    selected_date = st.date_input(
        label=input_label,
        value=st.session_state.selected_date if 'selected_date' in st.session_state else today,
        max_value=today if max_value else None,
    )
    return selected_date

def select_time(restricted_times=True, key_suffix="", timezone="UTC"):
    # Set the timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    current_date = now.date()
    current_hour = now.hour
    
    # Fixed scheduled times
    scheduled_times = ["08:00", "12:00", "17:00"]
    
    if st.session_state.selected_date < current_date:
        available_times = scheduled_times  # Show all times for past dates
    elif st.session_state.selected_date == current_date:
        # Show only times that are in the past for today
        available_times = ["08:00"]  # Default to 08:00
        if current_hour >= 12:
            available_times.append("12:00")
        if current_hour >= 17:
            available_times.append("17:00")
    else:
        available_times = scheduled_times  # Show all scheduled times for future dates

    search_time = st.selectbox(
        "Select search time",
        options=available_times,
        index=len(available_times) - 1,
        key=f"pricing_time_{key_suffix}"
    )
    return str(search_time.split(":")[0])
