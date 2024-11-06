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
        
    # Display data availability
    display_data.display_data_availability(
        df, "Scheduled", 
        {"date": datetime.now().strftime("%Y-%m-%d"), "time": "17:00:00"}
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
