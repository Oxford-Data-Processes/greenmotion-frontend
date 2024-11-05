import streamlit as st
import pandas as pd
from aws_utils import logs, iam
import os

iam.get_aws_credentials(st.secrets["aws_credentials"])


def main():
    project = "greenmotion"
    bucket_name = f"{project}-bucket-{os.environ['AWS_ACCOUNT_ID']}"
    st.title("Custom Search Logs")
    logs_handler = logs.LogsHandler()
    log_messages = logs_handler.get_logs(bucket_name, "frontend")
    log_df = pd.DataFrame(log_messages)
    st.dataframe(log_df, use_container_width=True)


if __name__ == "__main__":
    main()
