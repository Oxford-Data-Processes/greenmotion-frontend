import streamlit as st
from components.filters import select_car_group, select_rental_period
from components.charts import create_competitor_chart

def render(df):
    st.header("Competitor Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = select_car_group(df, key="competitor")
    with col2:
        rental_period = select_rental_period(df, key="competitor")
    
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    st.plotly_chart(create_competitor_chart(filtered_df), use_container_width=True)
