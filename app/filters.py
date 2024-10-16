import pandas as pd
import streamlit as st
from utils.data_utils import get_available_periods

def display_filters(filtered_df):
    rental_periods = get_available_periods(filtered_df)
    rental_periods_with_all = ["All"] + [
        int(period)
        for period in rental_periods
        if period != "All" and not pd.isna(period)
    ]
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

def apply_filters(filtered_df, rental_period, selected_car_group, selected_source, num_vehicles):
    if rental_period != "All":
        filtered_df = filtered_df[filtered_df["rental_period"] == rental_period]

    if selected_car_group != "All":
        filtered_df = filtered_df[filtered_df["car_group"] == selected_car_group]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    if num_vehicles == "All":
        num_vehicles = len(filtered_df)
    else:
        num_vehicles = int(num_vehicles)

    return filtered_df
