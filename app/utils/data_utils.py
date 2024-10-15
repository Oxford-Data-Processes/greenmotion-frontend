import pandas as pd
from datetime import datetime, time
import pytz

TIMEZONE = pytz.timezone("Europe/London")


def standardize_column_names(df):
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    return df


def rename_date_columns(df):
    return df.rename(
        columns={
            "pickup_date_time": "pickup_datetime",
            "dropoff_date_time": "dropoff_datetime",
            "pickup_date": "pickup_datetime",
            "dropoff_date": "dropoff_datetime",
        }
    )


def rename_total_price(df):
    if "drive_away_price" in df.columns:
        df = df.rename(columns={"drive_away_price": "total_price"})
    elif "full_price" in df.columns:
        df = df.rename(columns={"full_price": "total_price"})
    elif "price" in df.columns:
        df = df.rename(columns={"price": "total_price"})
    return df


def get_common_columns(df1, df2, df3):
    common_cols = list(set(df1.columns) & set(df2.columns) & set(df3.columns))
    if "total_price" not in common_cols:
        common_cols.append("total_price")
    for col in ["pickup_datetime", "dropoff_datetime"]:
        if col not in common_cols:
            common_cols.append(col)
    if "supplier_full_name" not in common_cols:
        common_cols.append("supplier_full_name")
    return common_cols


def rename_supplier_column(df):
    if "supplier_full_name" in df.columns:
        df = df.rename(columns={"supplier_full_name": "supplier"})
    elif "supplier_name" in df.columns:
        df = df.rename(columns={"supplier_name": "supplier"})
    return df


def combine_dataframes(df1, df2, df3, common_columns):
    dfs = [df1, df2, df3]
    combined_df = pd.DataFrame()

    for df in dfs:
        if not df.empty:
            # Only include columns that are actually present in the dataframe
            present_columns = [col for col in common_columns if col in df.columns]
            if "source" not in df.columns:
                df["source"] = "unknown"  # Add a default source if it's not present
            df_subset = df[present_columns + ["source"]]
            combined_df = pd.concat([combined_df, df_subset], ignore_index=True)

    return combined_df


def clean_combined_data(df):
    for col in ["make", "model", "transmission", "car_group", "supplier"]:
        df[col] = df[col].str.upper()
    for col in ["pickup_datetime", "dropoff_datetime"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    numeric_columns = [
        "total_price",
        "discounted_price",
        "price_per_day",
        "seats",
        "doors",
        "rental_period",
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["price_per_day"] = (df["total_price"] / df["rental_period"]).round(2)
    return df


def reorder_columns(df):
    columns_order = [
        "make",
        "model",
        "transmission",
        "car_group",
        "supplier",
        "total_price",
        "price_per_day",
        "pickup_datetime",
        "dropoff_datetime",
        "day",
        "month",
        "year",
        "hour",
        "rental_period",
        "source",
    ]
    return df[columns_order]


def sort_dataframe(df):
    return df.sort_values(["make", "model", "price_per_day"])


def extract_available_dates(combined_df):
    """Extract available dates from the DataFrame."""
    return pd.to_datetime(
        combined_df[["year", "month", "day"]]
        .drop_duplicates()
        .astype(str)
        .agg("-".join, axis=1),
        format="%Y-%m-%d",
    ).dt.date


def get_most_recent_date(available_dates):
    """Get the most recent date available."""
    today = datetime.now().date()
    return max(available_dates) if today not in available_dates else today


def filter_data_by_date(combined_df, search_date):
    """Filter the DataFrame for available rental periods based on the selected search date."""
    filtered_df = combined_df[
        (combined_df["year"] == search_date.year)
        & (combined_df["month"] == search_date.month)
        & (combined_df["day"] == search_date.day)
    ]
    return filtered_df


def ensure_correct_data_types(df):
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    df["day"] = df["day"].astype(int)
    return df


def get_available_periods(filtered_df):
    """Get available rental periods from the filtered data."""
    return sorted(filtered_df["rental_period"].unique())


def get_top_vehicles(filtered_df, rental_period, num_vehicles):
    """Get top N cheapest vehicles for each car group."""
    return (
        filtered_df.groupby("car_group")
        .apply(lambda x: x.nsmallest(num_vehicles, "price_per_day"))
        .reset_index(drop=True)
    )


def get_closest_past_time(current_time=None, increased_search_date=None):
    if increased_search_date is None:
        increased_search_date = datetime(2024, 10, 3).date()

    today = datetime.now(TIMEZONE).date()

    if current_time is None:
        current_time = datetime.now(TIMEZONE).time()

    if today < increased_search_date:
        return "11:00"
    elif today == increased_search_date:
        if current_time < time(17, 0):
            return "11:00"
        else:
            return "17:00"
    else:  # today > increased_search_date
        available_times = [time(8, 0), time(12, 0), time(17, 0)]
        past_times = [t for t in available_times if t <= current_time]
        if not past_times:
            return "17:00"  # If it's before 08:00, return the previous day's 17:00
        closest_time = max(past_times)
        return f"{closest_time.hour:02d}:00"
