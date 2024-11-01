# import streamlit as st
# import app.v2.data_viewer as data_viewer
# import app.v2.custom_search as custom_search
# import app.v2.custom_search_logs as custom_search_logs

# st.set_page_config(layout="wide")


import streamlit as st
import data_viewer
import custom_search
import custom_search_logs


st.set_page_config(layout="wide")


def main():
    st.sidebar.title("Menu")
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
