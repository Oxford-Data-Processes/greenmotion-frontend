import pandas as pd
from datetime import datetime, timedelta
import api.utils as api_utils

def load_latest_data(search_datetime):
    """Load and prepare data for analysis"""
    site_names = ["do_you_spain", "rental_cars", "holiday_autos"]
    dataframes = []
    
    for site_name in site_names:
        # Format search datetime
        formatted_search = format_search_datetime(search_datetime)
        
        # Fetch data from API
        json_data = fetch_data(site_name, formatted_search)
        if json_data:
            df = process_data(json_data)
            if not df.empty:
                df['source'] = site_name
                dataframes.append(df)
    
    if not dataframes:
        return pd.DataFrame()
    
    # Combine all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Process dates
    combined_df['date'] = pd.to_datetime(
        dict(
            year=combined_df['year'],
            month=combined_df['month'],
            day=combined_df['day']
        )
    ).dt.date
    
    # Ensure all required columns exist
    required_columns = [
        'supplier', 'total_price', 'rental_period', 
        'car_group', 'date', 'source'
    ]
    
    for col in required_columns:
        if col not in combined_df.columns:
            print(f"Missing required column: {col}")
            return pd.DataFrame()
    
    return combined_df

def load_historical_data(start_date, end_date):
    """Load historical data between two dates"""
    site_names = ["do_you_spain", "rental_cars", "holiday_autos"]
    dataframes = []
    
    for site_name in site_names:
        api_url = (
            f"/items/?table_name={site_name}"
            f"&start_date={start_date.strftime('%Y-%m-%dT%H:%M:%S')}:00"
            f"&end_date={end_date.strftime('%Y-%m-%dT%H:%M:%S')}:00"
            f"&limit=10000"
        )
        
        json_data = api_utils.get_request(api_url)
        if json_data:
            df = process_data(json_data)
            if not df.empty:
                df['source'] = site_name
                dataframes.append(df)
    
    if not dataframes:
        return pd.DataFrame()
    
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Process dates
    combined_df['date'] = pd.to_datetime(
        dict(
            year=combined_df['year'],
            month=combined_df['month'],
            day=combined_df['day']
        )
    ).dt.date
    
    return combined_df

def format_search_datetime(search_datetime):
    """Format search datetime for API request"""
    if isinstance(search_datetime, str):
        if ' ' in search_datetime:
            return search_datetime.replace(' ', 'T')
        return search_datetime
    return search_datetime.strftime('%Y-%m-%dT%H:%M:%S')

def fetch_data(site_name, formatted_search):
    """Fetch data from API"""
    try:
        # First try the current search datetime
        api_url = f"/items/?table_name={site_name}&search_datetime={formatted_search}:00&limit=10000"
        json_data = api_utils.get_request(api_url)
        
        # If no data, try the last 7 days
        if not json_data:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            api_url = (
                f"/items/?table_name={site_name}"
                f"&start_date={start_date.strftime('%Y-%m-%dT%H:%M:%S')}:00"
                f"&end_date={end_date.strftime('%Y-%m-%dT%H:%M:%S')}:00"
                f"&limit=10000"
            )
            json_data = api_utils.get_request(api_url)
        
        return json_data
    except Exception as e:
        print(f"Error fetching data for {site_name}: {str(e)}")
        return None

def process_data(json_data):
    """Process JSON data into DataFrame"""
    if not json_data:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(json_data)
        
        # Convert date-related columns
        if 'pickup_datetime' in df.columns:
            df['pickup_date'] = pd.to_datetime(df['pickup_datetime']).dt.date
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['total_price', 'rental_period']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return pd.DataFrame()