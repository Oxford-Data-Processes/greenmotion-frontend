import streamlit as st
import plotly.graph_objects as go
from datetime import datetime


def display_data_availability(df, search_type=None, search_params=None):
    title = "Data Availability"
    if search_type and search_params:
        if search_type == "Market Analysis":
            title += f" for Market Analysis (From: {search_params['start_date']}, To: {search_params['end_date']})"
        elif search_type == "Scheduled":
            title += f" for Scheduled Search (Date: {search_params['date']}, Time: {search_params['time']})"
        elif search_type == "Custom":
            title += f" for Custom Search (Pickup: {search_params['pickup']}, Dropoff: {search_params['dropoff']})"
    
    st.subheader(title)
    col1, col2, col3 = st.columns(3)
    sources = ["do_you_spain", "holiday_autos", "rental_cars"]
    for i, source in enumerate(sources):
        col = [col1, col2, col3][i]
        with col:
            if not df[df["source"] == source].empty:
                st.markdown(f"**{source}**: ✅")
            else:
                st.markdown(f"**{source}**: ❌")


def display_filters(df):
    if 'original_df' not in st.session_state:
        st.session_state.original_df = df.copy()
    
    # Generate a unique suffix for this instance
    if 'filter_instance' not in st.session_state:
        st.session_state.filter_instance = datetime.now().strftime('%Y%m%d%H%M%S')
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rental_periods = ["All"] + sorted(st.session_state.original_df["rental_period"].unique().tolist())
        rental_period = st.selectbox(
            "Select Rental Period (Days)", 
            options=rental_periods, 
            key=f"rental_period_{st.session_state.search_info['type']}_{st.session_state.filter_instance}"
        )

    with col2:
        car_groups = ["All"] + sorted(st.session_state.original_df["car_group"].unique().tolist())
        selected_car_group = st.selectbox(
            "Select Car Group", 
            options=car_groups, 
            key=f"car_group_{st.session_state.search_info['type']}_{st.session_state.filter_instance}"
        )

    with col3:
        num_vehicles_options = ["All"] + list(range(1, 21))
        num_vehicles = st.selectbox(
            "Select Number of Vehicles to Display",
            options=num_vehicles_options,
            index=3,
            key=f"num_vehicles_{st.session_state.search_info['type']}_{st.session_state.filter_instance}"
        )

    with col4:
        unique_sources = ["All"] + st.session_state.original_df["source"].unique().tolist()
        selected_source = st.selectbox(
            "Select Source", 
            options=unique_sources, 
            key=f"source_{st.session_state.search_info['type']}_{st.session_state.filter_instance}"
        )

    return rental_period, selected_car_group, num_vehicles, selected_source


def apply_filters(df, rental_period, selected_car_group, selected_source):
    if 'original_df' not in st.session_state:
        return df
        
    filtered_df = st.session_state.original_df.copy()

    # Ensure rental_period is treated as a string for comparison
    if rental_period != "All":
        filtered_df = filtered_df[filtered_df["rental_period"].astype(str) == str(rental_period)]

    if selected_car_group != "All":
        filtered_df = filtered_df[filtered_df["car_group"] == selected_car_group]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    filtered_df = filtered_df.sort_values("total_price").reset_index(drop=True)

    return filtered_df


def display_results(df, rental_period, selected_car_group, num_vehicles):
    # Create dynamic title
    num_vehicles_text = str(num_vehicles) if num_vehicles != "All" else "All"
    car_group_text = f"in {selected_car_group}" if selected_car_group != "All" else "across All Car Groups"
    rental_period_text = f"for {rental_period} Day Rental" if rental_period != "All" else "for All Rental Periods"
    
    st.subheader(f"Top {num_vehicles_text} Cheapest Vehicles {car_group_text} {rental_period_text}")
    
    # Create a copy of the dataframe to avoid modifying the original
    display_df = df.copy()

    # Apply num_vehicles filter first
    if num_vehicles != "All":
        n_vehicles = int(num_vehicles)
        if selected_car_group == "All":
            # Get top n vehicles per car group
            top_vehicles = (
                display_df.groupby("car_group")
                .apply(lambda x: x.nsmallest(n_vehicles, "total_price"))
                .reset_index(drop=True)
            )
        else:
            # Get top n vehicles for selected car group
            top_vehicles = display_df.nsmallest(n_vehicles, "total_price")
    else:
        if selected_car_group == "All":
            # Show all vehicles grouped by car group
            top_vehicles = display_df
        else:
            # Show all vehicles for selected car group
            top_vehicles = display_df

    top_vehicles = top_vehicles.sort_values(["car_group", "total_price"])
    display_df = remove_internal_columns(top_vehicles)

    st.dataframe(
        display_df.style.set_table_attributes(
            'style="width: 100%; overflow-x: auto;"'
        ).format(
            {
                "total_price": "{:.2f}",
            }
        )
    )

    display_average_price_chart(df, rental_period)


def display_average_price_chart(df, rental_period):
    avg_prices = (
        df.groupby(["car_group", "supplier"])["total_price"].mean().reset_index()
    )

    fig = go.Figure()
    for car_group in avg_prices["car_group"].unique():
        group_data = avg_prices[avg_prices["car_group"] == car_group]
        fig.add_trace(
            go.Bar(
                x=group_data["supplier"],
                y=group_data["total_price"],
                name=car_group,
                text=group_data["total_price"].round(2),
                textposition="auto",
            )
        )

    fig.update_layout(
        title=f"Average Price per Supplier and Car Group for {rental_period} Rental Period(s)",
        xaxis_title="Supplier",
        yaxis_title="Average Total Price",
        barmode="group",
        xaxis_tickangle=-45,
        height=600,
        width=900,
    )

    st.plotly_chart(fig)


def remove_internal_columns(df):
    return df.drop(columns=["day", "month", "year", "hour"], errors="ignore")


def download_filtered_data(filtered_df):
    download_df = remove_internal_columns(filtered_df)
    st.download_button(
        label="Download Filtered Data as CSV",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_rental_comparison_custom.csv",
        mime="text/csv",
    )


def main(df, search_type=None, search_params=None):
    if 'df' not in st.session_state or st.session_state.df is None:
        st.session_state.df = df.copy()
    
    display_data_availability(st.session_state.df, search_type, search_params)
    rental_period, selected_car_group, num_vehicles, selected_source = display_filters(st.session_state.df)
    
    filtered_df = apply_filters(
        st.session_state.df,
        rental_period,
        selected_car_group,
        selected_source,
    )

    if not filtered_df.empty:
        display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
        download_filtered_data(filtered_df)
    else:
        st.warning("No data available for the selected filters.")
