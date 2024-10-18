import streamlit as st
import search_by_date
import custom_date_range
import home_page

# Set the default layout to wide
st.set_page_config(layout="wide")

def main():
    st.sidebar.title("Menu")
    selection = st.sidebar.radio(
        "Select an option:", ["Homepage", "Search by Date", "Custom Date Range"]
    )

    if selection == "Homepage":
        home_page.main()
    elif selection == "Search by Date":
        search_by_date.main()
    elif selection == "Custom Date Range":
        custom_date_range.main()


if __name__ == "__main__":
    main()
