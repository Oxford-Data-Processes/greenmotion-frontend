# app/data_processing.py
import pandas as pd
import requests
import toml
import boto3
import re
import streamlit as st
from datetime import datetime
import os


def process_doyouspain_data(df, car_groups):
    df[["make", "model"]] = df["vehicle"].str.split(" ", n=1, expand=True)
    df["make"] = df["make"].replace({"Opel": "Vauxhall", "VW": "Volkswagen"})
    df.loc[df["make"] == "MG4", ["make", "model"]] = ["MG", "4"]
    df["model"] = (
        df["model"]
        .str.split(",")
        .str[0]
        .str.replace(r"\s*(Auto|Automatic|4x4)\s*$", "", regex=True)
        .str.replace(r"\s*4 door\s*", "", regex=True)
        .str.replace(r"\s*coupe\s*", "", regex=True)
        .str.replace(r"\s*5 door\s*", "", regex=True)
        .str.replace(r"\s*\+\s*GPS\s*", "", regex=True)
        .str.replace("SW", "Estate", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["transmission"] = df.apply(
        lambda row: (
            "AUTOMATIC"
            if row["has_automatic_transmission"] == "A"
            else ("MANUAL" if row["has_manual_transmission"] == "M" else "Unknown")
        ),
        axis=1,
    )
    df["car_group"] = df.apply(
        lambda row: assign_car_group_doyouspain(row, car_groups), axis=1
    )
    df = df.drop(
        ["vehicle", "has_manual_transmission", "has_automatic_transmission"], axis=1
    )
    cols = ["make", "model", "transmission", "car_group"] + [
        col
        for col in df.columns
        if col not in ["make", "model", "transmission", "car_group"]
    ]
    return df[cols]


def assign_car_group_doyouspain(row, car_groups):
    make = row["make"].upper()
    model = row["model"].upper()
    transmission = "AUTO" if row["transmission"] == "AUTOMATIC" else "MANUAL"

    match = car_groups[
        (car_groups["MAKE"] == make)
        & (car_groups["MODEL"] == model)
        & (car_groups["TRANSMISSION"] == transmission)
    ]

    return match.iloc[0]["GROUP"] if not match.empty else "Other"


def process_holidayautos_data(df, car_groups):
    df[["make", "model"]] = df["vehicle"].str.split(" ", n=1, expand=True)
    df["model"] = (
        df["model"]
        .str.replace(" or similar", "", case=False)
        .str.replace("AUTOMATIC", "", case=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df = df.drop("vehicle", axis=1)
    df = df.rename(
        columns={"total_charge": "full_price", "vendor": "supplier_full_name"}
    )
    df["car_group"] = df.apply(
        lambda row: assign_car_group_holidayautos(row, car_groups), axis=1
    )
    df["make"] = df["make"].replace("Opel", "Vauxhall")
    cols = ["make", "model", "car_group"] + [
        col for col in df.columns if col not in ["make", "model", "car_group"]
    ]
    return df[cols]


def assign_car_group_holidayautos(row, car_groups):
    make = row["make"].upper()
    model = row["model"].upper()
    transmission = "AUTO" if row["transmission"].upper() == "AUTOMATIC" else "MANUAL"
    make = "VAUXHALL" if make == "OPEL" else make

    match = car_groups[
        (car_groups["MAKE"] == make)
        & (car_groups["MODEL"] == model)
        & (car_groups["TRANSMISSION"] == transmission)
    ]

    return match.iloc[0]["GROUP"] if not match.empty else "Other"


def process_rentalcars_data(df, car_groups):
    df[["make", "model"]] = df["make_and_model"].str.split(" ", n=1, expand=True)
    df = df.drop("make_and_model", axis=1)
    df["model"] = (
        df["model"]
        .str.replace(" or similar", "", case=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["make"] = df["make"].replace("Opel", "Vauxhall")
    df["car_group"] = df.apply(
        lambda row: assign_car_group_rentalcars(row, car_groups), axis=1
    )
    cols = ["make", "model", "car_group"] + [
        col for col in df.columns if col not in ["make", "model", "car_group"]
    ]
    return df[cols]


def assign_car_group_rentalcars(row, car_groups):
    make, model, transmission = map(
        str.upper, [row["make"], row["model"], row["transmission"]]
    )
    match = car_groups[
        (car_groups["MAKE"] == make)
        & (car_groups["MODEL"] == model)
        & (car_groups["TRANSMISSION"] == transmission)
    ]
    return match.iloc[0]["GROUP"] if not match.empty else "Other"


def trigger_lambda(site_name, pickup_datetime, dropoff_datetime):

    secrets = toml.load(".streamlit/secrets.toml")
    token = secrets["github"]["token"]
    branch_name = st.secrets["github"]["branch_name"]
    custom_config = "true"
    stage = st.secrets["aws_credentials"]["STAGE"]
    repo = "Oxford-Data-Processes/greenmotion"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/trigger_workflow_{stage}.yml/dispatches"

    payload = {
        "ref": branch_name,
        "inputs": {
            "SITE_NAME": site_name,
            "CUSTOM_CONFIG": custom_config,
            "PICKUP_DATETIME": pickup_datetime,
            "DROPOFF_DATETIME": dropoff_datetime,
        },
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.post(url, headers=headers, json=payload)

    return response


def extract_datetime_from_sns_message(message):
    # Regular expression to find the datetime in the message
    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", message)
    return match.group(0) if match else None


def get_all_sqs_messages(queue_url):
    aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
    aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    aws_session_token = os.environ["AWS_SESSION_TOKEN"]
    sqs_client = boto3.client(
        "sqs",
        region_name="eu-west-2",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )
    all_messages = []
    current_time = datetime.now()

    while True:
        # Receive messages from the SQS queue
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,  # Process up to 10 messages at a time
            WaitTimeSeconds=10,  # Long polling for 10 seconds
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        if not messages:
            print("No more messages to purge. Exiting the loop.")
            break

        for message in messages:
            # Delete the message to purge it from the queue
            sqs_client.delete_message(
                QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
            )
            print("Deleted message:", message["MessageId"])

    while True:
        # Receive messages from the SQS queue
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,  # Process one message at a time
            WaitTimeSeconds=10,  # Long polling for 10 seconds
            MessageAttributeNames=["All"],
        )

        messages = response.get("Messages", [])
        if messages:
            for message in messages:
                timestamp = extract_datetime_from_sns_message(message["Body"])
                timestamp_datetime = datetime.fromisoformat(timestamp)

                message_body = message["Body"]
                all_messages.append({"timestamp": timestamp, "message": message_body})

                # Delete the message after processing
                sqs_client.delete_message(
                    QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"]
                )

                # Check if 'rental_cars' is in the message body and timestamp is after current time
                if (
                    "rental_cars" in message_body.lower()
                    and timestamp_datetime > current_time
                ):
                    print(
                        "Found 'rental_cars' in message and timestamp is after current time. Stopping the loop."
                    )
                    return all_messages

            print(all_messages)
        else:
            print("No new messages. Waiting for new notifications...")
