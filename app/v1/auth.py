import streamlit as st
import boto3


def get_credentials(aws_account_id, role):
    role_arn = f"arn:aws:iam::{aws_account_id}:role/{role}"
    session_name = "MySession"

    sts_client = boto3.client(
        "sts",
        aws_access_key_id=st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY"],
    )

    # Assume the role
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    # Extract the credentials
    credentials = response["Credentials"]
    access_key_id = credentials["AccessKeyId"]
    secret_access_key = credentials["SecretAccessKey"]
    session_token = credentials["SessionToken"]

    return access_key_id, secret_access_key, session_token


def login():
    """Handle user login."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        st.success("You are already logged in!")
        return

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if (
            username == st.secrets["login_credentials"]["username"]
            and password == st.secrets["login_credentials"]["password"]
        ):
            st.session_state["logged_in"] = True
            st.session_state["just_logged_in"] = True  # Set the flag
            st.rerun()  # Force a rerun to update the UI
        else:
            st.error("Invalid username or password")


def logout():
    """Handle user logout."""
    st.session_state["logged_in"] = False
    st.success("Logged out successfully!")
