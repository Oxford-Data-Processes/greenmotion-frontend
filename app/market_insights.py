import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def generate_demo_price_data():
    # Generate data from July to November 1st
    dates = pd.date_range(start='2024-07-01', end='2024-11-01', freq='D')
    suppliers = ['GREEN MOTION', 'HERTZ', 'ENTERPRISE', 'AVIS', 'EUROPCAR']
    car_groups = ['1ELE', '1A', '2A', '2B', '3A']
    
    data = []
    previous_prices = {}  # Track previous day prices
    
    for date in dates:
        seasonal_factor = 1.3 if date.month in [7, 8] else 1.0
        weekend_factor = 1.2 if date.dayofweek >= 5 else 1.0
        
        for supplier in suppliers:
            for car_group in car_groups:
                base_price = {
                    '1ELE': 150,
                    '1A': 100,
                    '2A': 130,
                    '2B': 180,
                    '3A': 200
                }[car_group]
                
                # Add random price changes (5% chance per day)
                price_change_factor = 1.0
                if np.random.random() < 0.05:
                    price_change_factor = np.random.uniform(0.9, 1.1)
                
                price = (base_price * 
                        seasonal_factor * 
                        weekend_factor * 
                        price_change_factor * 
                        (1 + np.random.normal(0, 0.02)))  # 2% random variation
                
                # Track price changes
                key = (supplier, car_group)
                previous_price = previous_prices.get(key, price)
                price_changed = abs((price - previous_price) / previous_price) > 0.05  # 5% threshold
                
                data.append({
                    'date': date,
                    'supplier': supplier,
                    'car_group': car_group,
                    'price': round(price, 2),
                    'rental_period': 1,  # Fixed 1-day rental
                    'previous_price': round(previous_price, 2),
                    'price_changed': price_changed,
                    'market_share': np.random.beta(5, 15),
                    'availability': np.random.beta(8, 2) * (0.8 if date.month in [7, 8] else 1.0)
                })
                
                previous_prices[key] = price
    
    return pd.DataFrame(data)

def price_trends_chart(df):
    st.subheader("Market Price Trends")
    
    # Calculate average prices by date and supplier
    avg_prices = df.groupby(['date', 'supplier'])['price'].mean().reset_index()
    
    fig = px.line(avg_prices, x='date', y='price', color='supplier',
                  title='Average Daily Rates by Supplier',
                  labels={'price': 'Average Daily Rate (£)', 'date': 'Date'})
    
    fig.update_layout(
        height=500,
        legend_title='Supplier',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def market_share_chart(df):
    st.subheader("Market Share Analysis")
    
    market_share = df.groupby('supplier')['market_share'].mean().sort_values(ascending=True)
    
    fig = go.Figure(go.Bar(
        x=market_share.values,
        y=market_share.index,
        orientation='h'
    ))
    
    fig.update_layout(
        title='Market Share by Supplier',
        xaxis_title='Market Share (%)',
        yaxis_title='Supplier',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def car_group_analysis(df):
    st.subheader("Car Group Performance")
    
    avg_by_group = df.groupby('car_group').agg({
        'price': 'mean',
        'availability': 'mean'
    }).reset_index()
    
    fig = px.scatter(avg_by_group, x='price', y='availability',
                    size='price', color='car_group',
                    title='Price vs Availability by Car Group',
                    labels={'price': 'Average Price (£)',
                           'availability': 'Availability Rate'})
    
    st.plotly_chart(fig, use_container_width=True)

def competitive_analysis(df):
    st.subheader("Competitive Analysis")
    
    pivot_data = df.pivot_table(
        values='price',
        index='car_group',
        columns='supplier',
        aggfunc='mean'
    )
    
    fig = px.imshow(pivot_data,
                    labels=dict(x='Supplier', y='Car Group', color='Price (£)'),
                    aspect='auto',
                    color_continuous_scale='RdYlBu_r')
    
    fig.update_layout(
        title='Price Heatmap by Supplier and Car Group',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def seasonality_analysis(df):
    st.subheader("Seasonality Patterns")
    
    df['day_of_week'] = df['date'].dt.day_name()
    daily_avg = df.groupby(['day_of_week', 'car_group'])['price'].mean().reset_index()
    
    fig = px.line(daily_avg, x='day_of_week', y='price', color='car_group',
                  title='Price Patterns by Day of Week',
                  labels={'price': 'Average Price (£)',
                         'day_of_week': 'Day of Week'})
    
    st.plotly_chart(fig, use_container_width=True)

def price_alert_dashboard(df):
    st.subheader("Price Change Alerts")
    
    # Get latest price changes
    recent_changes = df[df['price_changed']].copy()
    recent_changes['price_diff'] = recent_changes['price'] - recent_changes['previous_price']
    recent_changes['price_diff_pct'] = (recent_changes['price_diff'] / recent_changes['previous_price']) * 100
    
    # Create alerts for significant price changes
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Competitors with Price Changes",
            f"{len(recent_changes['supplier'].unique())}",
            delta=f"{len(recent_changes)} changes detected"
        )
    
    with col2:
        avg_change = recent_changes['price_diff_pct'].mean()
        st.metric(
            "Average Price Change",
            f"{abs(avg_change):.1f}%",
            delta=f"{'↑' if avg_change > 0 else '↓'}"
        )
    
    # Price change table
    if not recent_changes.empty:
        st.markdown("### Recent Price Changes")
        
        for supplier in recent_changes['supplier'].unique():
            if supplier != 'GREEN MOTION':
                supplier_changes = recent_changes[recent_changes['supplier'] == supplier]
                
                expander = st.expander(f"🔔 {supplier} - {len(supplier_changes)} price changes")
                with expander:
                    for _, change in supplier_changes.iterrows():
                        color = "red" if change['price_diff'] > 0 else "green"
                        st.markdown(f"""
                        **Car Group:** {change['car_group']}  
                        **Old Price:** £{change['previous_price']:.2f}  
                        **New Price:** £{change['price']:.2f}  
                        **Change:** <span style='color:{color}'>£{abs(change['price_diff']):.2f} ({change['price_diff_pct']:.1f}%)</span>
                        """, unsafe_allow_html=True)

def competitive_position_analysis(df):
    st.subheader("Green Motion Competitive Position")
    
    # Get latest prices
    latest_data = df.groupby(['supplier', 'car_group'])['price'].last().reset_index()
    gm_prices = latest_data[latest_data['supplier'] == 'GREEN MOTION']
    
    for car_group in gm_prices['car_group'].unique():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            group_data = latest_data[latest_data['car_group'] == car_group]
            fig = px.bar(group_data, 
                        x='supplier', 
                        y='price',
                        title=f'Price Comparison - {car_group}',
                        color='supplier',
                        color_discrete_map={'GREEN MOTION': '#00FF00'})
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            gm_price = gm_prices[gm_prices['car_group'] == car_group]['price'].iloc[0]
            competitors = latest_data[
                (latest_data['car_group'] == car_group) & 
                (latest_data['supplier'] != 'GREEN MOTION')
            ]
            
            avg_competitor_price = competitors['price'].mean()
            price_difference = ((gm_price - avg_competitor_price) / avg_competitor_price) * 100
            
            st.metric(
                "Position vs Market",
                f"£{gm_price:.2f}",
                delta=f"{price_difference:.1f}% vs avg"
            )

def simple_price_alert(df):
    st.subheader("Price Change Alerts (1-Day Rentals)")
    
    # Get today's data
    latest_date = df['date'].max()
    
    recent_changes = df[
        (df['price_changed']) &
        (df['date'] == latest_date)
    ].copy()
    
    if not recent_changes.empty:
        # Create columns for the header
        st.markdown("### Recent Price Changes")
        
        # Group changes by car group
        for car_group in recent_changes['car_group'].unique():
            group_changes = recent_changes[recent_changes['car_group'] == car_group]
            
            # Create a section for each car group
            st.markdown(f"#### 🚨 {car_group}")
            
            # Create a clean table-like display for each supplier's changes
            for _, row in group_changes.iterrows():
                price_diff = row['price'] - row['previous_price']
                pct_change = (price_diff / row['previous_price']) * 100
                
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(f"**{row['supplier']}**")
                with col2:
                    st.markdown(f"£{row['previous_price']:.2f} → £{row['price']:.2f}")
                with col3:
                    color = "red" if price_diff > 0 else "green"
                    st.markdown(
                        f"<span style='color:{color}'>{'↑' if price_diff > 0 else '↓'} {abs(pct_change):.1f}%</span>",
                        unsafe_allow_html=True
                    )
            
            st.markdown("---")  # Add a separator between car groups
    else:
        st.info("No significant price changes detected today")

def main():
    st.title("Green Motion Market Insights Dashboard")
    
    # Generate demo data
    df = generate_demo_price_data()
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Price Alerts & Position", "Market Analysis", "Detailed Insights"])
    
    # Add filters in a sidebar
    with st.sidebar:
        st.header("Filters")
        selected_suppliers = st.multiselect(
            "Select Suppliers",
            options=df['supplier'].unique(),
            default=df['supplier'].unique()
        )
        
        selected_car_groups = st.multiselect(
            "Select Car Groups",
            options=df['car_group'].unique(),
            default=df['car_group'].unique()
        )
        
        date_range = st.date_input(
            "Select Date Range",
            value=(df['date'].min(), df['date'].max()),
            min_value=df['date'].min().date(),
            max_value=df['date'].max().date()
        )
    
    # Filter data based on selections
    filtered_df = df[
        (df['supplier'].isin(selected_suppliers)) &
        (df['car_group'].isin(selected_car_groups))
    ]
    
    # Tab 1: Price Alerts & Position
    with tab1:
        # Key metrics at the top
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Daily Rate", f"£{filtered_df['price'].mean():.2f}")
        with col2:
            gm_data = filtered_df[filtered_df['supplier'] == 'GREEN MOTION']
            others_data = filtered_df[filtered_df['supplier'] != 'GREEN MOTION']
            price_diff = ((gm_data['price'].mean() - others_data['price'].mean()) / 
                         others_data['price'].mean() * 100)
            st.metric("Market Position", 
                     f"£{gm_data['price'].mean():.2f}",
                     f"{price_diff:.1f}% vs market")
        with col3:
            st.metric("Active Competitors", 
                     len(selected_suppliers)-1,
                     f"{len(filtered_df[filtered_df['price_changed']])} price changes")
        
        # Price alerts in an expander
        with st.expander("🚨 Recent Price Changes", expanded=True):
            simple_price_alert(filtered_df)
        
        # Competitive position
        competitive_position_analysis(filtered_df)
    
    # Tab 2: Market Analysis
    with tab2:
        price_trends_chart(filtered_df)
        
        col1, col2 = st.columns(2)
        with col1:
            market_share_chart(filtered_df)
        with col2:
            car_group_analysis(filtered_df)
    
    # Tab 3: Detailed Insights
    with tab3:
        competitive_analysis(filtered_df)
        seasonality_analysis(filtered_df)

if __name__ == "__main__":
    main()