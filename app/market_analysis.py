import streamlit as st
from datetime import datetime
from aws_utils import iam
import display_data
from analysis import (
    market_overview,
    daily_snapshot,
    pace_view,
    future_trends,
    competitor_analysis
)
from components.filters import load_historical_data

def main():
    st.title("Market Analysis Dashboard")
    
    # Initialize AWS credentials
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    
    # Load data
    with st.spinner("Loading market data..."):
        df = load_historical_data()
    
    if df.empty:
        st.error("No data available for analysis")
        return
        
    # Get date range from data
    start_datetime = datetime(
        year=int(df['year'].min()),
        month=int(df['month'].min()),
        day=int(df['day'].min()),
        hour=int(df['hour'].min())
    )
    end_datetime = datetime(
        year=int(df['year'].max()),
        month=int(df['month'].max()),
        day=int(df['day'].max()),
        hour=int(df['hour'].max())
    )
    
    # Display data availability with market analysis parameters
    display_data.display_data_availability(
        df, 
        "Market Analysis",
        {
            "start_date": start_datetime.strftime("%Y-%m-%d %H:%M"),
            "end_date": end_datetime.strftime("%Y-%m-%d %H:%M")
        }
    )
    
    # Create tabs
    tabs = st.tabs([
        "Market Overview", 
        "Daily Snapshot", 
        "Pace View", 
        "Future Trends (Alpha Testing)",
        "Competitor Analysis"
    ])
    
    # Render tabs
    tab_functions = [
        market_overview.render,
        daily_snapshot.render,
        pace_view.render,
        future_trends.render,
        competitor_analysis.render
    ]
    
    for tab, func in zip(tabs, tab_functions):
        with tab:
            func(df)

if __name__ == "__main__":
    main()
