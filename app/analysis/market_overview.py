import streamlit as st
from components.filters import select_car_group, select_rental_period
from components.charts import create_price_distribution_plot

def render(df):
    st.header("Market Overview")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = select_car_group(df)
    with col2:
        rental_period = select_rental_period(df)
    
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    display_metrics(filtered_df)
    st.plotly_chart(create_price_distribution_plot(filtered_df), use_container_width=True)

def display_metrics(df):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Price", f"£{df['total_price'].mean():.2f}")
    with col2:
        st.metric("Total Vehicles", len(df))
    with col3:
        st.metric("Price Range", f"£{df['total_price'].min():.2f} - £{df['total_price'].max():.2f}")