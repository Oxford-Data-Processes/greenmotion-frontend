# app/ui.py
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def remove_internal_columns(df):
    """Remove internal columns from the DataFrame."""
    return df.drop(columns=['day', 'month', 'year', 'hour'], errors='ignore')

def display_results(top_vehicles, rental_period, filtered_df, selected_car_group):
    """Display the results in Streamlit with a dynamic title."""
    
    # Remove internal columns
    top_vehicles = remove_internal_columns(top_vehicles)
    
    # Create a dynamic title based on user selections
    rental_period_text = f"{int(rental_period)} Days Rental" if rental_period != "All" else "All Rental Periods"
    car_group_text = selected_car_group if selected_car_group != "All" else "All Car Groups"
    
    st.subheader(f"Top {len(top_vehicles)} Cheapest Vehicles in {car_group_text} categories for {rental_period_text}")

    # Display the results table with formatted total price and rental period
    st.dataframe(
        top_vehicles.style
        .set_table_attributes('style="width: 100%; overflow-x: auto;"')
        .format({
            'price_per_day': '{:.2f}', 
            'total_price': '{:.2f}',
            'rental_period': '{:.0f}'  # Format rental period as integer
        })
    )

def display_top_vehicles_per_group(filtered_df, selected_car_group, rental_period, num_vehicles):
    """Display the top N cheapest vehicles for the selected car group and suppliers."""
    
    # Remove internal columns
    filtered_df = remove_internal_columns(filtered_df)
    
    # Check if num_vehicles is "All" and set it to the maximum number of vehicles available
    if num_vehicles == "All":
        num_vehicles = len(filtered_df)  # Set to the total number of vehicles available

    # Get top N cheapest vehicles per supplier, sorted by total price descending
    top_vehicles = (
        filtered_df
        .groupby('supplier')
        .apply(lambda x: x.nsmallest(num_vehicles, 'total_price'))  # Use num_vehicles for filtering
        .reset_index(drop=True)
    )
    
    # Sort by total price descending
    top_vehicles = top_vehicles.sort_values(by='total_price', ascending=False)

    # Check if there's enough data to plot
    if top_vehicles.empty:
        st.write("Not enough data to display for the selected car group.")
        return
    
    # Create a bar plot without confidence intervals
    plt.figure(figsize=(14, 6))  # Increase the width of the figure
    sns.barplot(data=top_vehicles, x='supplier', y='total_price', hue='supplier')
    plt.title(f'Top {num_vehicles} Cheapest Vehicles per supplier in {selected_car_group} categories for {int(rental_period) if rental_period != "All" else "All"} Days Rental')
    plt.xlabel('Supplier')
    plt.ylabel('Total Price')
    plt.xticks(rotation=45, ha='right')  # Rotate labels and align them to the right
    plt.legend(title='Supplier')
    plt.tight_layout()
    
    # Display the plot in Streamlit
    st.pyplot(plt)

def display_results_custom(top_vehicles, rental_period, filtered_df, selected_car_group):
    """Display the results in Streamlit with a dynamic title, grouped by car_group and sorted by total_price."""
    
    # Remove internal columns and the columns we want to hide
    columns_to_remove = ['day', 'month', 'year', 'hour', 'rental_period', 'price_per_day']
    display_df = top_vehicles.drop(columns=columns_to_remove, errors='ignore')
    
    # Create a dynamic title based on user selections
    rental_period_text = f"{rental_period} Days Rental" if rental_period != "All" else "All Rental Periods"
    car_group_text = selected_car_group if selected_car_group != "All" else "All Car Groups"
    
    st.subheader(f"Top Cheapest Vehicles in {car_group_text} categories for {rental_period_text}")

    # Sort the dataframe by car_group and then by total_price
    sorted_df = display_df.sort_values(['car_group', 'total_price'])
    
    # Display the results table with formatted total price
    st.dataframe(
        sorted_df.style
        .set_table_attributes('style="width: 100%; overflow-x: auto;"')
        .format({'total_price': '{:.2f}'})
    )