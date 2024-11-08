import streamlit as st
import pandas as pd
from datetime import datetime
from .pricing_calculations import calculate_suggested_price

def render_matrix_view(df):
    selected_sources = render_source_filter(df)
    desired_position, handle_ties = render_position_controls(df)
    
    matrix_df, cell_colors = create_matrix(df, selected_sources, desired_position - 1, handle_ties)
    display_matrix(matrix_df, cell_colors)
    add_export_button(matrix_df)

def render_source_filter(df):
    sources = sorted(df['source'].unique())
    return st.multiselect(
        "Select Data Sources",
        options=sources,
        default=sources,
        key="matrix_pricing_sources"
    )

def render_position_controls(df):
    col1, col2 = st.columns(2)
    
    with col1:
        if 'matrix_desired_position' not in st.session_state:
            st.session_state.matrix_desired_position = 3
            
        desired_position = st.number_input(
            "Desired Market Position (1 = cheapest)",
            min_value=1,
            max_value=len(df),
            value=st.session_state.matrix_desired_position,
            key="matrix_desired_position"
        )
    
    with col2:
        handle_ties = st.checkbox(
            "Group same prices together",
            value=False,
            help="When enabled, vehicles with the same price will share the same position",
            key="matrix_handle_ties"
        )
    
    return desired_position, handle_ties

def create_matrix(df, selected_sources, desired_position, handle_ties):
    filtered_df = df[df['source'].isin(selected_sources)]
    car_groups = sorted(filtered_df['car_group'].unique())
    rental_periods = sorted(filtered_df['rental_period'].unique())
    
    return build_matrix_data(filtered_df, car_groups, rental_periods, desired_position, handle_ties)

def add_export_button(matrix_df):
    if st.button("Export to CSV"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pricing_matrix_{timestamp}.csv"
        csv = matrix_df.to_csv(index=False)
        
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )

def display_matrix(matrix_df, cell_colors):
    def style_df(df):
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        for i in range(len(df)):
            for j in range(len(df.columns)):
                if cell_colors[i][j] == 'lightgreen':
                    styles.iloc[i, j] = 'background-color: lightgreen'
        return styles

    styler = matrix_df.style.set_table_attributes('style="width: 100%;"')\
                           .apply(style_df, axis=None)
    
    st.dataframe(styler, use_container_width=True)

def build_matrix_data(filtered_df, car_groups, rental_periods, desired_position, handle_ties):
    matrix_data = []
    cell_colors = []  # Track which cells should be green
    
    for car_group in car_groups:
        row_data = {'Car Group': car_group}
        row_colors = ['white'] * (len(rental_periods) + 1)  # +1 for Car Group column
        
        for i, period in enumerate(rental_periods, 1):
            period_data = filtered_df[
                (filtered_df['car_group'] == car_group) & 
                (filtered_df['rental_period'] == period)
            ]
            if not period_data.empty:
                # Get Green Motion entries
                green_motion_entries = period_data[
                    period_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)
                ]
                
                # Check if Green Motion is in correct position
                is_correct_position = False
                sorted_data = period_data.sort_values('total_price')
                
                if not green_motion_entries.empty:
                    if handle_ties:
                        unique_prices = sorted(sorted_data['total_price'].unique())
                        price_to_rank = {price: idx for idx, price in enumerate(unique_prices)}
                        green_motion_ranks = green_motion_entries['total_price'].map(price_to_rank)
                        is_correct_position = any(rank in [desired_position, desired_position + 1] for rank in green_motion_ranks)
                    else:
                        green_motion_indices = sorted_data[
                            sorted_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)
                        ].index
                        green_motion_ranks = [sorted_data.index.get_loc(idx) for idx in green_motion_indices]
                        is_correct_position = any(rank in [desired_position, desired_position + 1] for rank in green_motion_ranks)
                
                suggested_price = calculate_suggested_price(period_data, desired_position, handle_ties)
                price_text = f"£{suggested_price:.2f}"
                if is_correct_position:
                    row_colors[i] = 'lightgreen'
                    price_text = f"✅ {price_text}"
                
                row_data[f'{period} Days'] = price_text
            else:
                row_data[f'{period} Days'] = "N/A"
                
        matrix_data.append(row_data)
        cell_colors.append(row_colors)
    
    return pd.DataFrame(matrix_data), cell_colors