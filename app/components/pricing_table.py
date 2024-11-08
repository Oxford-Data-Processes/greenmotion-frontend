import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def create_pricing_table(df, desired_position, handle_ties=False):
    if len(df) < 2:
        st.warning("Insufficient data for pricing analysis. Need at least 2 competitors.")
        return
    
    competitor_data = prepare_competitor_data(df)
    green_motion_entries = get_green_motion_entries(competitor_data)
    
    # Check if Green Motion is in correct position
    is_correct_position = False
    if handle_ties:
        unique_prices = sorted(competitor_data['total_price'].unique())
        price_to_rank = {price: idx for idx, price in enumerate(unique_prices)}
        if check_green_motion_position(green_motion_entries, price_to_rank, desired_position):
            is_correct_position = True
    else:
        if check_green_motion_sequential_position(competitor_data, green_motion_entries, desired_position):
            is_correct_position = True
    
    if is_correct_position:
        st.success("✅ Green Motion is already priced in the desired market position!")
    
    suggested_price = calculate_suggested_price(competitor_data, desired_position, handle_ties)
    display_table(competitor_data, suggested_price, desired_position, handle_ties)

def prepare_competitor_data(df):
    sorted_prices = df.sort_values('total_price')
    return sorted_prices[['supplier', 'total_price']].copy()

def calculate_suggested_price(competitor_data, desired_position, handle_ties):
    green_motion_entries = get_green_motion_entries(competitor_data)
    
    if handle_ties:
        return calculate_with_ties(competitor_data, green_motion_entries, desired_position)
    else:
        return calculate_sequential(competitor_data, green_motion_entries, desired_position)

def get_green_motion_entries(competitor_data):
    return competitor_data[
        competitor_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)
    ]

def calculate_with_ties(competitor_data, green_motion_entries, desired_position):
    unique_prices = sorted(competitor_data['total_price'].unique())
    price_to_rank = {price: idx for idx, price in enumerate(unique_prices)}
    
    if check_green_motion_position(green_motion_entries, price_to_rank, desired_position):
        return green_motion_entries['total_price'].iloc[0]
    
    if desired_position == 0:
        return unique_prices[0] * 0.95
    
    if len(unique_prices) <= desired_position + 1:
        return competitor_data['total_price'].max() * 1.05
    
    price_at_position = unique_prices[desired_position]
    price_at_next = unique_prices[desired_position + 1]
    return (price_at_position + price_at_next) / 2

def calculate_sequential(competitor_data, green_motion_entries, desired_position):
    competitor_data['rank'] = range(len(competitor_data))
    
    if check_green_motion_sequential_position(competitor_data, green_motion_entries, desired_position):
        return green_motion_entries['total_price'].iloc[0]
    
    if desired_position == 0:
        return competitor_data.iloc[0]['total_price'] * 0.95
    
    if len(competitor_data) <= desired_position + 1:
        return competitor_data['total_price'].max() * 1.05
    
    price_at_position = competitor_data.iloc[desired_position]['total_price']
    price_at_next = competitor_data.iloc[desired_position + 1]['total_price']
    return (price_at_position + price_at_next) / 2

def check_green_motion_position(green_motion_entries, price_to_rank, desired_position):
    if not green_motion_entries.empty:
        green_motion_ranks = green_motion_entries['total_price'].map(price_to_rank)
        return any(rank in [desired_position, desired_position + 1] for rank in green_motion_ranks)
    return False

def check_green_motion_sequential_position(competitor_data, green_motion_entries, desired_position):
    if not green_motion_entries.empty:
        green_motion_indices = competitor_data[
            competitor_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)
        ].index
        green_motion_ranks = [competitor_data.index.get_loc(idx) for idx in green_motion_indices]
        return any(rank in [desired_position, desired_position + 1] for rank in green_motion_ranks)
    return False

def display_table(competitor_data, suggested_price, desired_position, handle_ties):
    suggested_row = pd.DataFrame({
        'supplier': ['SUGGESTED PRICE'],
        'total_price': [suggested_price],
        'rank': [desired_position + 0.5 if desired_position > 0 else 0]
    })
    
    all_data = pd.concat([competitor_data, suggested_row], ignore_index=True)
    all_data = all_data.sort_values('total_price')
    all_data['rank'] = range(len(all_data))
    
    fig = go.Figure(data=[
        go.Table(
            header=dict(
                values=['Position', 'Supplier', 'Price (£)'],
                fill_color='paleturquoise',
                align='left'
            ),
            cells=dict(
                values=[
                    (all_data['rank'] + 1).astype(int).tolist(),  # Add 1 to make positions 1-based
                    all_data['supplier'].tolist(),
                    all_data['total_price'].round(2).tolist()
                ],
                fill_color=[
                    ['lightgreen' if supplier == 'SUGGESTED PRICE'
                     else 'lightblue' if 'GREEN MOTION' in str(supplier).upper()
                     else 'white'
                     for supplier in all_data['supplier']]
                ],
                align='left'
            )
        )
    ])
    
    ranking_type = "grouped" if handle_ties else "sequential"
    fig.update_layout(
        title=f"Price Ranking ({ranking_type} positions, suggested price between positions {desired_position + 1} and {desired_position + 2})",
        height=400 + (len(all_data) * 25)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    if not competitor_data[competitor_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)].empty:
        st.subheader("Green Motion Current Positions")
        for _, row in competitor_data[competitor_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)].iterrows():
            position = all_data[all_data['supplier'] == row['supplier']]['rank'].iloc[0]
            st.info(f"{row['supplier']}: Position {int(position + 1)} at £{row['total_price']:.2f}")
