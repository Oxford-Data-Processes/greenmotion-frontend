import streamlit as st
import data_viewer
import custom_search
import custom_search_logs

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Car Rental Data Tool",
    page_icon="🚗",
)


def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if (
            username == st.secrets["login_credentials"]["username"]
            and password == st.secrets["login_credentials"]["password"]
        ):
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.experimental_rerun()  # Move to the next page after successful login
        else:
            st.error("Invalid username or password")


def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.title("Car Rental Data Tool")
        selection = st.sidebar.radio(
            "Select an option:", ["Data Viewer", "Custom Search", "Custom Search Logs"]
        )

        if selection == "Data Viewer":
            data_viewer.main()
        elif selection == "Custom Search":
            custom_search.main()
        elif selection == "Custom Search Logs":
            custom_search_logs.main()


if __name__ == "__main__":
    main()
