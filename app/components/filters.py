import streamlit as st
from datetime import datetime, timedelta
from data_viewer import load_data
import pandas as pd

@st.cache_data(ttl=3600)
def load_historical_data(days=10):
    """Load historical market data"""
    dates_to_fetch = generate_dates_to_fetch(days)
    return batch_process_dates(dates_to_fetch)

def generate_dates_to_fetch(days):
    """Generate list of dates to fetch data for"""
    dates = []
    end_date = datetime.now().date()
    current_date = end_date - timedelta(days=days)
    
    while current_date <= end_date:
        for hour in [17]:
            dates.append(f"{current_date.strftime('%Y-%m-%d')}T{hour:02d}:00:00")
        current_date += timedelta(days=1)
    return dates

def batch_process_dates(dates_to_fetch, batch_size=5):
    """Process dates in batches"""
    progress_bar = st.progress(0, text="Loading historical market data...")
    all_dataframes = []
    
    for batch_idx in range(0, len(dates_to_fetch), batch_size):
        batch = dates_to_fetch[batch_idx:batch_idx + batch_size]
        process_batch(batch, all_dataframes)
        update_progress(progress_bar, batch_idx, len(dates_to_fetch))
    
    progress_bar.empty()
    return combine_dataframes(all_dataframes)

def process_batch(batch_dates, all_dataframes):
    """Process a batch of dates and append results to all_dataframes"""
    for search_datetime in batch_dates:
        try:
            df = load_data(search_datetime, None, None, False)
            if not df.empty:
                all_dataframes.append(df)
        except Exception as e:
            # Silently continue if a particular datetime fails
            continue

def update_progress(progress_bar, current_idx, total_items):
    """Update the progress bar"""
    progress = min((current_idx + 1) / total_items, 1.0)
    progress_bar.progress(progress, text="Loading historical market data...")

def combine_dataframes(dataframes):
    """Combine all dataframes and return the result"""
    if not dataframes:
        return pd.DataFrame()
    
    return pd.concat(dataframes, ignore_index=True)

def select_car_group(df, key=""):
    """Filter dropdown for car groups"""
    return st.selectbox(
        "Select Car Group",
        options=['All'] + sorted(df['car_group'].unique().tolist()),
        key=f"car_group_{key}"
    )

def select_rental_period(df, key=""):
    """Filter dropdown for rental periods"""
    return st.selectbox(
        "Select Rental Period (Days)",
        options=sorted(df['rental_period'].unique().tolist()),
        key=f"rental_period_{key}"
    )