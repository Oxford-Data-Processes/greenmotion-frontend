# The module which can be reused to display data for all the pages
import streamlit as st
import api.utils
import pandas as pd


def main():
    table_options = ["do_you_spain", "rental_cars", "holiday_autos"]
    selected_table = st.selectbox("Select a table:", table_options)
    st.write(f"You selected: {selected_table}")

    if selected_table:
        if st.button("Get Data"):
            data = api.utils.get_request(f"/table={selected_table}/limit=5")
            df = pd.DataFrame(data)
            st.dataframe(df)


if __name__ == "__main__":
    main()
