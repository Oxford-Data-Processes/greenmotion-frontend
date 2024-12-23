import streamlit as st
import pandas as pd
from aws_utils import logs, iam
import os


def load_logs(logs_handler, bucket_name):
    log_messages = logs_handler.get_logs(bucket_name, "frontend")
    log_df = pd.DataFrame(log_messages).sort_values(by="timestamp", ascending=False)
    st.dataframe(log_df, use_container_width=True)


def main():
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    st.title("Custom Search Logs")
    logs_handler = logs.LogsHandler()

    load_logs(logs_handler, bucket_name)

    refresh_button = st.button("Refresh Logs")
    if refresh_button:
        load_logs(logs_handler, bucket_name)


if __name__ == "__main__":
    main()
