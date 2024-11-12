import streamlit as st
import pandas as pd
from datetime import datetime
import api.utils as api_utils
from aws_utils import iam
from components.pricing_filters import render_filters
from components.pricing_table import create_pricing_table
from components.pricing_matrix import render_matrix_view
from utils.data_loader import load_latest_data
from components.date_selector import select_date, select_time

def render_pricing_strategy(df):
    tab1, tab2 = st.tabs(["Detailed View", "Matrix View"])
    
    with tab1:
        render_detailed_view(df)
    
    with tab2:
        render_matrix_view(df)

def render_detailed_view(df):
    # Get filter values
    rental_period, selected_car_group, selected_sources, desired_position, handle_ties = render_filters(df)
    
    # Filter data
    filtered_df = df[
        (df['rental_period'] == rental_period) &
        (df['source'].isin(selected_sources)) &
        (df['car_group'] == selected_car_group)
    ]
    
    create_pricing_table(filtered_df, desired_position - 1, handle_ties)

def main():
    st.title("Pricing Strategy")
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    # Date and time selection
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.selected_date = select_date("Select search date", max_value=True)
    with col2:
        selected_hour = select_time(restricted_times=True, key_suffix="pricing")
    
    search_datetime = f"{st.session_state.selected_date}T{selected_hour}:00:00"
    
    # Load data button
    if st.button("Load data"):
        with st.spinner("Loading market data..."):
            df = load_latest_data(search_datetime)
        
        if df.empty:
            st.error("No data available for analysis")
            return
            
        st.session_state.pricing_df = df
        st.session_state.data_loaded = True
    
    # Only show pricing strategy when data is loaded
    if 'data_loaded' in st.session_state and st.session_state.data_loaded:
        render_pricing_strategy(st.session_state.pricing_df)

if __name__ == "__main__":
    main()