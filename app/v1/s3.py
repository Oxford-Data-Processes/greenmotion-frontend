import boto3
import pandas as pd
import streamlit as st
import os


def read_car_groups_from_s3():
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="eu-west-2",
        aws_session_token=os.environ["AWS_SESSION_TOKEN"],
    )
    aws_account_id = st.secrets["aws_credentials"]["AWS_ACCOUNT_ID"]
    bucket_name = f"greenmotion-bucket-{aws_account_id}"
    key = "car_groups/car_groups.csv"

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    return pd.read_csv(response["Body"])
