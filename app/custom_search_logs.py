import streamlit as st
import pandas as pd
from aws_utils import logs, iam
import os

iam_instance = iam.IAM(stage=st.secrets["aws_credentials"]["STAGE"])
iam.AWSCredentials.get_aws_credentials(
    aws_access_key_id=st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID_ADMIN"],
    aws_secret_access_key=st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY_ADMIN"],
    iam_instance=iam_instance,
)


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
