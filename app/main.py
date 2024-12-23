import streamlit as st
import data_viewer
import custom_search
import custom_search_logs
import market_analysis
import pricing_strategy

st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Car Rental Data Tool",
    page_icon="🚗",
)

def login():
    st.title("Login")

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

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.title("Car Rental Data Tool")
        selection = st.sidebar.radio(
            "Select an option:", 
            ["Data Viewer", 
             "Custom Search", 
             "Pricing Strategy",  # Moved Pricing Strategy below Custom Search
             "Custom Search Logs", 
             "Market Analysis (Beta)"]
        )

        if selection == "Data Viewer":
            data_viewer.main()
        elif selection == "Custom Search":
            custom_search.main()
        elif selection == "Pricing Strategy":  # Adjusted the order of the conditions
            pricing_strategy.main()
        elif selection == "Custom Search Logs":
            custom_search_logs.main()
        elif selection == "Market Analysis (Beta)":
            market_analysis.main()

if __name__ == "__main__":
    main()
