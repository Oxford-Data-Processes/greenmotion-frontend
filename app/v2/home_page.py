import streamlit as st
import pandas as pd


def read_parquet_file():
    file_path = "mocks/s3/do_you_spain/raw/year=2024/month=10/day=09/hour=09/rental_period=custom/data.parquet"
    df = pd.read_parquet(file_path)
    return df


def main():
    st.title("Home Page")
    st.write("Welcome to the Home Page!")
    st.write("Navigate to the following options:")
    st.write("Search by Date")
    st.write("Custom Date Range")

    if st.button("Load Car Groups Data"):
        data = read_parquet_file()
        st.dataframe(data)


if __name__ == "__main__":
    main()
