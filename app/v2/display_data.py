# The module which can be reused to display data for all the pages
import streamlit as st
import api.utils
import pandas as pd
import plotly.graph_objects as go


def main():
    table_options = ["do_you_spain", "rental_cars", "holiday_autos"]
    selected_table = st.selectbox("Select a table:", table_options)
    st.write(f"You selected: {selected_table}")

    if selected_table:
        if st.button("Get Data"):
            data = api.utils.get_request(f"/items/?table_name={selected_table}")
            df = pd.DataFrame(data)
            st.dataframe(df)


if __name__ == "__main__":
    main()


def display_data_availability(df):
    st.subheader("Data Availability")
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
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rental_periods = ["All"] + sorted(df["rental_period"].unique().tolist())
        rental_period = st.selectbox(
            "Select Rental Period (Days)", options=rental_periods, key="rental_period"
        )

    with col2:
        car_groups = ["All"] + sorted(df["car_group"].unique().tolist())
        selected_car_group = st.selectbox(
            "Select Car Group", options=car_groups, key="car_group"
        )

    with col3:
        num_vehicles_options = ["All"] + list(range(1, 21))
        num_vehicles = st.selectbox(
            "Select Number of Vehicles to Display",
            options=num_vehicles_options,
            index=3,
            key="num_vehicles",
        )

    with col4:
        unique_sources = ["All"] + df["source"].unique().tolist()
        selected_source = st.selectbox(
            "Select Source", options=unique_sources, key="source"
        )

    return rental_period, selected_car_group, num_vehicles, selected_source


def apply_filters(df, rental_period, selected_car_group, selected_source):
    filtered_df = df.copy()

    if rental_period != "All":
        filtered_df = filtered_df[filtered_df["rental_period"] == int(rental_period)]

    if selected_car_group != "All":
        filtered_df = filtered_df[filtered_df["car_group"] == selected_car_group]

    if selected_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == selected_source]

    filtered_df = filtered_df.sort_values("total_price").reset_index(drop=True)

    return filtered_df


def display_results(df, rental_period, selected_car_group, num_vehicles):
    st.subheader("Top Cheapest Vehicles")

    if selected_car_group == "All":
        # Group by car_group and get top 3 cheapest for each
        top_vehicles = (
            df.groupby("car_group")
            .apply(lambda x: x.nsmallest(3, "total_price"))
            .reset_index(drop=True)
        )
    else:
        # If a specific car group is selected, just get the top vehicles for that group
        if num_vehicles == "All":
            top_vehicles = df[df["car_group"] == selected_car_group]
        else:
            top_vehicles = df[df["car_group"] == selected_car_group].nsmallest(
                int(num_vehicles), "total_price"
            )

    # Sort the dataframe by car_group and then by total_price
    top_vehicles = top_vehicles.sort_values(["car_group", "total_price"])

    # Remove internal columns
    display_df = remove_internal_columns(top_vehicles)

    # Display the results in a single dataframe
    st.dataframe(
        display_df.style.set_table_attributes(
            'style="width: 100%; overflow-x: auto;"'
        ).format(
            {
                "price_per_day": "{:.2f}",
                "total_price": "{:.2f}",
            }
        )
    )

    # Display average price chart
    display_average_price_chart(df, rental_period, selected_car_group)


def display_average_price_chart(df, rental_period, selected_car_group):
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
