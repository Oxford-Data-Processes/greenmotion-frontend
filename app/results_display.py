from datetime import datetime
import streamlit as st
from ui import display_results, display_results_custom, display_top_vehicles_per_group
from utils.data_utils import get_top_vehicles, get_top_vehicles_custom

def display_results_and_download(filtered_df, rental_period, selected_car_group, num_vehicles):
    top_vehicles = get_top_vehicles(filtered_df, rental_period, num_vehicles)

    display_results(top_vehicles, rental_period, filtered_df, selected_car_group)
    display_top_vehicles_per_group(
        filtered_df, selected_car_group, rental_period, num_vehicles
    )

    download_df = filtered_df.drop(
        columns=["day", "month", "year", "hour"], errors="ignore"
    )
    st.download_button(
        label="Download Filtered Data as CSV",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_rental_comparison.csv",
        mime="text/csv",
    )

def display_filtered_results(pickup_date, pickup_time, dropoff_date, dropoff_time):
    df_combined = st.session_state.custom_df

    pickup_datetime = datetime.combine(pickup_date, pickup_time)
    dropoff_datetime = datetime.combine(dropoff_date, dropoff_time)
    rental_period = (dropoff_datetime - pickup_datetime).days

    col1, col2, col3 = st.columns(3)

    with col1:
        car_groups = ["All"] + sorted(df_combined["car_group"].unique().tolist())
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

    filtered_df = df_combined.copy()

    if selected_car_group != "All":
        filtered_df = filtered_df[filtered_df["car_group"] == selected_car_group]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    top_vehicles = get_top_vehicles_custom(filtered_df, num_vehicles)

    display_results_custom(top_vehicles, rental_period, filtered_df, selected_car_group)
    display_top_vehicles_per_group(
        filtered_df, selected_car_group, rental_period, num_vehicles
    )

    download_filtered_data(filtered_df)

def display_data_availability(df_doyouspain, df_holidayautos, df_rentalcars):
    st.subheader("Data Availability")
    col1, col2, col3 = st.columns(3)
    sources = ["do_you_spain", "holiday_autos", "rental_cars"]
    for i, source in enumerate(sources):
        col = [col1, col2, col3][i]
        with col:
            if (
                (source == "do_you_spain" and not df_doyouspain.empty)
                or (source == "holiday_autos" and not df_holidayautos.empty)
                or (source == "rental_cars" and not df_rentalcars.empty)
            ):
                st.markdown(f"**{source}**: ✅")
            else:
                st.markdown(f"**{source}**: ❌")

def display_data_availability_custom(data_availability):
    st.subheader("Data Availability")
    col1, col2, col3 = st.columns(3)
    for i, (source, availability) in enumerate(data_availability.items()):
        col = [col1, col2, col3][i]
        with col:
            if availability == "Data available":
                st.markdown(f"**{source}**: ✅")
            else:
                st.markdown(f"**{source}**: ❌")

def download_filtered_data(filtered_df):
    download_df = filtered_df.drop(
        columns=["day", "month", "year", "hour"], errors="ignore"
    )
    st.download_button(
        label="Download Filtered Data as CSV",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_rental_comparison_custom.csv",
        mime="text/csv",
    )
