import boto3
import pandas as pd
import streamlit as st
import os

aws_account_id = st.secrets["aws_credentials"]["AWS_ACCOUNT_ID"]


def run_athena_query(database, query):
    """Run an Athena query and return the results as a DataFrame or available data info."""

    client = boto3.client(
        "athena",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="eu-west-2",
        aws_session_token=os.environ["AWS_SESSION_TOKEN"],
    )

    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={
            "OutputLocation": f"s3://greenmotion-bucket-{aws_account_id}/athena-results/"
        },
    )

    query_execution_id = response["QueryExecutionId"]

    while True:
        response = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = response["QueryExecution"]["Status"]["State"]
        if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break

    if status == "SUCCEEDED":
        result = client.get_query_results(QueryExecutionId=query_execution_id)
        columns = [
            col["Label"]
            for col in result["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
        ]
        rows = [row["Data"] for row in result["ResultSet"]["Rows"][1:]]
        data = [[col.get("VarCharValue", None) for col in row] for row in rows]

        next_token = result.get("NextToken")
        while next_token:
            result = client.get_query_results(
                QueryExecutionId=query_execution_id, NextToken=next_token
            )
            rows = [row["Data"] for row in result["ResultSet"]["Rows"]]
            data.extend(
                [[col.get("VarCharValue", None) for col in row] for row in rows]
            )
            next_token = result.get("NextToken")

        try:
            df = pd.DataFrame(data, columns=columns)
            return df
        except ValueError as e:
            if "Columns must be same length as key" in str(e):
                print(
                    "Error: Mismatch in column count and data. Checking data availability."
                )
                availability = check_data_availability(database, client)
                print(f"Data availability: {availability}")
                return {
                    "error": "Data structure mismatch",
                    "data_availability": availability,
                }
            else:
                raise
    else:
        error_message = response["QueryExecution"]["Status"]["StateChangeReason"]
        raise Exception(f"Query failed with status: {status}. Error: {error_message}")


def check_data_availability(database, client):
    """Check data availability for each source and rental period."""
    sources = ["do_you_spain", "holiday_autos", "rental_cars"]
    rental_periods = [1, 3, 5, 7, 10, 14, 21, 28]
    hours = ["08", "12", "17"]
    availability = {}

    for source in sources:
        availability[source] = {}
        for period in rental_periods:
            availability[source][period] = {}
            for hour in hours:
                query = f"""
                SELECT MAX(day) as latest_day, MAX(month) as latest_month, MAX(year) as latest_year
                FROM {database}
                WHERE rental_period = {period} AND hour = '{hour}'
                """
                response = client.start_query_execution(
                    QueryString=query,
                    QueryExecutionContext={"Database": database},
                    ResultConfiguration={
                        "OutputLocation": f"s3://greenmotion-bucket-{aws_account_id}/athena-results/"
                    },
                )
                query_execution_id = response["QueryExecutionId"]

                while True:
                    response = client.get_query_execution(
                        QueryExecutionId=query_execution_id
                    )
                    status = response["QueryExecution"]["Status"]["State"]
                    if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                        break

                if status == "SUCCEEDED":
                    result = client.get_query_results(
                        QueryExecutionId=query_execution_id
                    )
                    if len(result["ResultSet"]["Rows"]) > 1:
                        latest_day = result["ResultSet"]["Rows"][1]["Data"][0][
                            "VarCharValue"
                        ]
                        latest_month = result["ResultSet"]["Rows"][1]["Data"][1][
                            "VarCharValue"
                        ]
                        latest_year = result["ResultSet"]["Rows"][1]["Data"][2][
                            "VarCharValue"
                        ]
                        availability[source][period][
                            hour
                        ] = f"{latest_year}-{latest_month}-{latest_day}"
                    else:
                        availability[source][period][hour] = "No data available"
                else:
                    availability[source][period][hour] = "Error retrieving data"

    return availability


def generate_query(database, year, month, day, hour):
    query_template = """
        SELECT * FROM "{database}"."raw"
        WHERE cast(year as integer) = {year} 
        AND cast(month as integer) = {month} 
        AND cast(day as integer) = {day} 
        AND hour = '{hour}'
        AND rental_period != 'custom';
    """
    return query_template.format(
        database=database, year=year, month=month, day=day, hour=hour
    )


def generate_custom_query(database, fetch_time):
    query_template = """
        SELECT * FROM "{database}"."raw"
        WHERE cast(year as integer) = {year} AND cast(month as integer) = {month} AND cast(day as integer) = {day} AND hour = '{hour}'AND rental_period = 'custom';
    """
    return query_template.format(
        database=database,
        year=fetch_time.year,
        month=fetch_time.month,
        day=fetch_time.day,
        hour=fetch_time.strftime("%H"),
    )
