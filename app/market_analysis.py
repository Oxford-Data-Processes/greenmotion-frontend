import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from aws_utils import logs, iam
import api.utils as api_utils
import os
from data_viewer import load_data, load_data_and_display

# Cache the data loading function
@st.cache_data(ttl=3600)
def load_historical_data(days=30):
    """Load last 30 days of data using data_viewer pattern"""
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
        
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    dataframes = []
    
    # Get data for each day at 08:00, 12:00, and 17:00
    for date in pd.date_range(start=start_date, end=end_date):
        st.session_state.selected_date = date.date()
        for hour in ['08', '12', '17']:
            search_datetime = f"{date.date()}T{hour}:00:00"
            
            # Use load_data_and_display instead of load_data directly
            df = pd.DataFrame()
            try:
                with st.spinner(f"Loading data for {date.date()} {hour}:00"):
                    df = load_data_and_display(search_datetime)
                    if 'df' in st.session_state and not st.session_state.df.empty:
                        dataframes.append(st.session_state.df.copy())
            except Exception as e:
                st.warning(f"Error loading data for {date.date()} {hour}:00 - {str(e)}")
                continue
    
    if dataframes:
        final_df = pd.concat(dataframes, ignore_index=True)
        return final_df
    return pd.DataFrame()

def calculate_market_stats(df, car_group=None):
    """Calculate market statistics for each vehicle category"""
    if car_group:
        df = df[df['car_group'] == car_group]
    
    stats = df.groupby(['car_group', 'supplier']).agg({
        'total_price': ['mean', 'min', 'max', 'count']
    }).reset_index()
    
    stats.columns = ['car_group', 'supplier', 'mean_price', 'min_price', 'max_price', 'count']
    return stats

def create_price_distribution_plot(df, car_group):
    """Create price distribution plot with GreenMotion highlighted"""
    fig = go.Figure()
    
    # Add box plots for each supplier
    for supplier in df['supplier'].unique():
        supplier_data = df[df['supplier'] == supplier]
        color = '#1f77b4' if supplier != 'GREEN MOTION' else '#ff7f0e'
        
        fig.add_trace(go.Box(
            y=supplier_data['total_price'],
            name=supplier,
            boxpoints='all',
            marker_color=color,
            marker_size=4
        ))
    
    fig.update_layout(
        title=f'Price Distribution for {car_group}',
        yaxis_title='Total Price',
        showlegend=True,
        height=400
    )
    
    return fig

def market_overview_page(df):
    st.header("Market Overview (30-day Historical View)")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=['All'] + sorted(df['car_group'].unique().tolist())
        )
    
    with col2:
        rental_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(df['rental_period'].unique().tolist())
        )
    
    # Filter data
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Calculate and display statistics
    stats = calculate_market_stats(filtered_df)
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Market Price", 
                 f"£{stats['mean_price'].mean():.2f}")
    with col2:
        st.metric("Lowest Price Available", 
                 f"£{stats['min_price'].min():.2f}")
    with col3:
        st.metric("Total Vehicles", 
                 str(stats['count'].sum()))
    
    # Price distribution plot
    st.plotly_chart(
        create_price_distribution_plot(filtered_df, selected_car_group),
        use_container_width=True
    )
    
    # Display detailed statistics table
    st.subheader("Detailed Market Statistics")
    st.dataframe(stats.style.format({
        'mean_price': '£{:.2f}',
        'min_price': '£{:.2f}',
        'max_price': '£{:.2f}'
    }))

def daily_snapshot_page(df):
    st.header("Daily Snapshot")
    # Implementation for daily snapshot page
    pass

def pace_view_page(df):
    st.header("Pace View (30-day Trend)")
    # Implementation for pace view page
    pass

def future_trends_page(df):
    st.header("Future Trends (14-day Forecast)")
    # Implementation for future trends page
    pass

def competitor_analysis_page(df):
    st.header("Competitor Analysis")
    # Implementation for competitor analysis page
    pass

def main():
    st.title("Market Analysis Dashboard")
    
    # Initialize AWS credentials
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        ["Market Overview", "Daily Snapshot", "Pace View", 
         "Future Trends", "Competitor Analysis"]
    )
    
    # Load data
    with st.spinner("Loading market data..."):
        df = load_historical_data()
    
    if df.empty:
        st.error("No data available for analysis")
        return
    
    # Page routing
    if page == "Market Overview":
        market_overview_page(df)
    elif page == "Daily Snapshot":
        daily_snapshot_page(df)
    elif page == "Pace View":
        pace_view_page(df)
    elif page == "Future Trends":
        future_trends_page(df)
    else:
        competitor_analysis_page(df)

if __name__ == "__main__":
    main()
