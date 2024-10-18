import os
import streamlit as st
from auth import get_credentials

def setup_aws_credentials():
    if st.secrets["aws_credentials"]["STAGE"] == "prod":
        role = "ProdAdminRole"
    else:
        role = "DevAdminRole"

    access_key_id, secret_access_key, session_token = get_credentials(
        st.secrets["aws_credentials"]["AWS_ACCOUNT_ID"], role
    )

    os.environ["AWS_ACCESS_KEY_ID"] = access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = secret_access_key
    os.environ["AWS_SESSION_TOKEN"] = session_token

    return st.secrets["aws_credentials"]["AWS_ACCOUNT_ID"]
