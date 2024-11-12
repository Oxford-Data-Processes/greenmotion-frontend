import streamlit as st

def render_filters(df):
    # Data source filter in its own row
    sources = sorted(df['source'].unique())
    selected_sources = st.multiselect(
        "Select Data Sources",
        options=sources,
        default=sources,
        key="pricing_sources"
    )
    
    # Other filters in a row below
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rental_period = st.selectbox(
            "Select Rental Period",
            options=sorted(df['rental_period'].unique()),
            key="pricing_rental_period"
        )
    
    with col2:
        car_groups = sorted(df['car_group'].unique())
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=car_groups,
            key="pricing_car_group"
        )
    
    with col3:
        max_vehicles = len(df[df['car_group'] == selected_car_group])
        desired_position = st.number_input(
            "Desired Market Position (1 = cheapest)",
            min_value=1,
            max_value=max_vehicles,
            value=4,
            key="desired_position"
        ) - 1
        
        handle_ties = st.checkbox(
            "Group same prices together",
            value=False,
            help="When enabled, vehicles with the same price will share the same position"
        )
    
    return rental_period, selected_car_group, selected_sources, desired_position, handle_ties