import streamlit as st
import plotly.graph_objects as go


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
        top_vehicles = (
            df.groupby("car_group")
            .apply(lambda x: x.nsmallest(3, "total_price"))
            .reset_index(drop=True)
        )
    else:
        if num_vehicles == "All":
            top_vehicles = df[df["car_group"] == selected_car_group]
        else:
            top_vehicles = df[df["car_group"] == selected_car_group].nsmallest(
                int(num_vehicles), "total_price"
            )

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


def main(df):
    display_data_availability(df)
    rental_period, selected_car_group, num_vehicles, selected_source = display_filters(
        df
    )
    filtered_df = apply_filters(
        df,
        rental_period,
        selected_car_group,
        selected_source,
    )

    display_results(filtered_df, rental_period, selected_car_group, num_vehicles)
    download_filtered_data(filtered_df)
