import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import data_viewer
import custom_search
import custom_search_logs
import market_analysis
import pricing_strategy
from components.ai import render_ai_chat
from utils.data_loader import load_latest_data, load_historical_data

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Car Rental Data Tool",
    page_icon="🚗",
)

def login():
    st.title("Login")

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        st.success("You are already logged in!")
        return

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if (
            username == st.secrets["login_credentials"]["username"]
            and password == st.secrets["login_credentials"]["password"]
        ):
            st.session_state["logged_in"] = True
            st.session_state["just_logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def load_ai_data():
    """Load data for AI analysis"""
    try:
        # Try to load the most recent data
        search_datetime = datetime.now().strftime("%Y-%m-%dT%H:00:00")
        df = load_latest_data(search_datetime)
        
        if df.empty:
            # If no data for current time, try loading historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            df = load_historical_data(start_date, end_date)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.title("Car Rental Data Tool")
        selection = st.sidebar.radio(
            "Select an option:", 
            [
                "AI Market Assistant",
                "Data Viewer", 
                "Custom Search", 
                "Pricing Strategy",
                "Custom Search Logs", 
                "Market Analysis (Beta)"
            ]
        )

        if selection == "AI Market Assistant":
            with st.spinner("Loading market data for AI analysis..."):
                df = load_ai_data()
                
                if df.empty:
                    st.error("""
                        No data available for AI analysis. 
                        Please ensure you have run a recent data collection 
                        or try the Custom Search feature first.
                    """)
                    
                    if st.button("Run Custom Search"):
                        st.switch_page("pages/custom_search.py")
                else:
                    render_ai_chat(df)
        elif selection == "Data Viewer":
            data_viewer.main()
        elif selection == "Custom Search":
            custom_search.main()
        elif selection == "Pricing Strategy":
            pricing_strategy.main()
        elif selection == "Custom Search Logs":
            custom_search_logs.main()
        elif selection == "Market Analysis (Beta)":
            market_analysis.main()

if __name__ == "__main__":
    main()
