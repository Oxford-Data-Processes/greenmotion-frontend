import streamlit as st
import pandas as pd
from aws_utils import s3


def read_parquet_file():
    s3_handler = s3.S3Handler()
    bucket_name = "mock-bucket"
    file_path = "do_you_spain/raw/year=2024/month=10/day=09/hour=09/rental_period=custom/data.parquet"
    parquet_data = s3_handler.load_parquet_from_s3(bucket_name, file_path)
    df = pd.read_parquet(pd.io.common.BytesIO(parquet_data))
    return df


def main():
    st.title("Home Page")
    st.write("Welcome to the Home Page!")

    if st.button("Load Parquet Data from S3"):
        data = read_parquet_file()
        st.dataframe(data)


if __name__ == "__main__":
    main()
