import streamlit as st
from components.filters import select_car_group, select_rental_period
from components.charts import create_forecast_chart
import pandas as pd

def render(df):
    st.header("Future Trends (Alpha Testing)")
    st.warning("⚠️ This feature is in alpha testing. Predictions may not be accurate.")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = select_car_group(df, key="future")
    with col2:
        rental_period = select_rental_period(df, key="future")
    
    filtered_df = df[df['rental_period'] == rental_period].copy()
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Create date column and check for minimum data points
    filtered_df.loc[:, 'date'] = pd.to_datetime(
        dict(year=filtered_df['year'], 
             month=filtered_df['month'], 
             day=filtered_df['day'])
    ).dt.date
    daily_data = filtered_df.groupby('date')['total_price'].mean().reset_index()
    
    if len(daily_data) < 3:
        st.error("Insufficient data for forecasting. Need at least 3 days of data.")
        st.info("Try selecting a different car group or rental period with more historical data.")
        return
        
    try:
        forecast_fig = create_forecast_chart(filtered_df)
        if forecast_fig is None:
            st.error("Prophet is not installed. Please run: `pip install prophet`")
        else:
            st.plotly_chart(forecast_fig, use_container_width=True)
    except ValueError as e:
        st.error(str(e))
        st.info("Try selecting a different car group or rental period with more data points.")