import pandas as pd
import api.utils as api_utils

def load_latest_data(search_datetime):
    site_names = ["do_you_spain", "rental_cars", "holiday_autos"]
    dataframes = []
    
    for site_name in site_names:
        formatted_search = format_search_datetime(search_datetime)
        json_data = fetch_data(site_name, formatted_search)
        if json_data:
            df = process_data(json_data, site_name)
            if not df.empty:
                dataframes.append(df)
    
    return pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()

def format_search_datetime(search_datetime):
    return search_datetime.replace(" ", "T") if " " in search_datetime else search_datetime

def fetch_data(site_name, formatted_search):
    api_url = f"/items/?table_name={site_name}&search_datetime={formatted_search}:00&limit=10000"
    return api_utils.get_request(api_url)

def process_data(json_data, site_name):
    df = pd.DataFrame(json_data)
    df['source'] = site_name
    return df