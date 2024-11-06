import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from aws_utils import logs, iam
import api.utils as api_utils
import os
from data_viewer import load_data
import display_data

# Cache the data loading function
@st.cache_data(ttl=3600)
def load_historical_data(days=14):
    """Load last 30 days of data using data_viewer pattern"""
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().date()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Generate all date-time combinations we want to fetch
    dates_to_fetch = []
    current_date = start_date
    while current_date <= end_date:
        for hour in [17]:  # Only fetch data for available times
            dates_to_fetch.append(
                f"{current_date.strftime('%Y-%m-%d')}T{hour:02d}:00:00"
            )
        current_date += timedelta(days=1)
    
    # Create progress bar
    progress_text = "Loading historical market data..."
    progress_bar = st.progress(0, text=progress_text)
    
    # Batch process dates
    batch_size = 5  # Number of dates to process in parallel
    all_dataframes = []
    total_batches = len(dates_to_fetch) // batch_size + (1 if len(dates_to_fetch) % batch_size else 0)
    
    for batch_idx in range(0, len(dates_to_fetch), batch_size):
        batch_dates = dates_to_fetch[batch_idx:batch_idx + batch_size]
        batch_dfs = []
        
        # Process each date in the batch
        for search_datetime in batch_dates:
            try:
                df = load_data(search_datetime, None, None, False)
                if not df.empty:
                    batch_dfs.append(df)
            except Exception:
                # Silently continue if a particular datetime fails
                continue
        
        if batch_dfs:
            all_dataframes.extend(batch_dfs)
        
        # Update progress
        progress = (batch_idx + batch_size) / len(dates_to_fetch)
        progress_bar.progress(min(progress, 1.0), text=progress_text)
    
    # Clean up progress bar
    progress_bar.empty()
    
    if all_dataframes:
        final_df = pd.concat(all_dataframes, ignore_index=True)
        st.success(f"Successfully loaded data from {len(all_dataframes)} time points")
        return final_df
    
    st.warning("Limited data available in development environment")
    return pd.DataFrame()

def calculate_market_stats(df, car_group=None):
    """Calculate market statistics for each vehicle category"""
    if car_group:
        df = df[df['car_group'] == car_group]
    
    stats = df.groupby(['car_group', 'supplier']).agg({
        'total_price': ['mean', 'min', 'max', 'count']
    }).reset_index()
    
    stats.columns = ['car_group', 'supplier', 'mean_price', 'min_price', 'max_price', 'count']
    return stats

def create_price_distribution_plot(df, car_group):
    """Create price distribution plot with GreenMotion highlighted"""
    fig = go.Figure()
    
    # Add box plots for each supplier
    for supplier in df['supplier'].unique():
        supplier_data = df[df['supplier'] == supplier]
        color = '#1f77b4' if supplier != 'GREEN MOTION' else '#ff7f0e'
        
        fig.add_trace(go.Box(
            y=supplier_data['total_price'],
            name=supplier,
            boxpoints='all',
            marker_color=color,
            marker_size=4
        ))
    
    fig.update_layout(
        title=f'Price Distribution for {car_group}',
        yaxis_title='Total Price',
        showlegend=True,
        height=400
    )
    
    return fig

def market_overview_page(df):
    st.header("Market Overview (30-day Historical View)")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=['All'] + sorted(df['car_group'].unique().tolist())
        )
    
    with col2:
        rental_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(df['rental_period'].unique().tolist())
        )
    
    # Filter data
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Calculate and display statistics
    stats = calculate_market_stats(filtered_df)
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Market Price", 
                 f"£{stats['mean_price'].mean():.2f}")
    with col2:
        st.metric("Lowest Price Available", 
                 f"£{stats['min_price'].min():.2f}")
    with col3:
        st.metric("Total Vehicles", 
                 str(stats['count'].sum()))
    
    # Price distribution plot
    st.plotly_chart(
        create_price_distribution_plot(filtered_df, selected_car_group),
        use_container_width=True
    )
    
    # Display detailed statistics table
    st.subheader("Detailed Market Statistics")
    st.dataframe(stats.style.format({
        'mean_price': '£{:.2f}',
        'min_price': '£{:.2f}',
        'max_price': '£{:.2f}'
    }))

def daily_snapshot_page(df):
    st.header("Daily Snapshot")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=['All'] + sorted(df['car_group'].unique().tolist()),
            key="daily_snapshot_car_group"
        )
    
    with col2:
        rental_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(df['rental_period'].unique().tolist()),
            key="daily_snapshot_rental_period"
        )
    
    # Filter data
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Create daily price trend plot
    fig = go.Figure()
    
    for supplier in filtered_df['supplier'].unique():
        supplier_data = filtered_df[filtered_df['supplier'] == supplier]
        # Create search_date from when the search was conducted
        supplier_data['search_date'] = pd.to_datetime(
            dict(
                year=supplier_data['year'],
                month=supplier_data['month'],
                day=supplier_data['day'],
                hour=supplier_data['hour']
            )
        ).dt.date
        
        # Average price for each search date
        daily_avg = supplier_data.groupby('search_date')['total_price'].mean().reset_index()
        
        fig.add_trace(go.Scatter(
            x=daily_avg['search_date'],
            y=daily_avg['total_price'],
            name=supplier,
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title=f'Price Changes Over Time for {selected_car_group} (Rental Period: {rental_period} days)',
        xaxis_title='Search Date',
        yaxis_title='Average Price (£)',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

def pace_view_page(df):
    st.header("Pace View (30-day Trend)")
    
    # Create search_date from when the search was conducted
    df['search_date'] = pd.to_datetime(
        dict(
            year=df['year'],
            month=df['month'],
            day=df['day'],
            hour=df['hour']
        )
    ).dt.date
    
    # Calculate daily statistics
    daily_stats = df.groupby(['search_date', 'supplier']).agg({
        'total_price': ['mean', 'count']
    }).reset_index()
    
    daily_stats.columns = ['search_date', 'supplier', 'avg_price', 'vehicle_count']
    
    # Create two plots
    col1, col2 = st.columns(2)
    
    with col1:
        # Price Pace
        fig1 = go.Figure()
        for supplier in daily_stats['supplier'].unique():
            supplier_data = daily_stats[daily_stats['supplier'] == supplier]
            fig1.add_trace(go.Scatter(
                x=supplier_data['search_date'],
                y=supplier_data['avg_price'],
                name=supplier,
                mode='lines+markers'
            ))
        
        fig1.update_layout(
            title='Price Pace Trend',
            xaxis_title='Search Date',
            yaxis_title='Average Price (£)',
            height=400
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Inventory Pace
        fig2 = go.Figure()
        for supplier in daily_stats['supplier'].unique():
            supplier_data = daily_stats[daily_stats['supplier'] == supplier]
            fig2.add_trace(go.Scatter(
                x=supplier_data['search_date'],
                y=supplier_data['vehicle_count'],
                name=supplier,
                mode='lines+markers'
            ))
        
        fig2.update_layout(
            title='Inventory Pace Trend',
            xaxis_title='Search Date',
            yaxis_title='Number of Vehicles',
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)

def future_trends_page(df):
    st.header("Future Trends (14-day Forecast) - BETA")
    st.warning("⚠️ This is a beta feature. Predictions are experimental and should be used as rough guidance only.")
    
    try:
        import prophet
    except ImportError:
        st.error("Please install Prophet: `pip install prophet`")
        return
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=['All'] + sorted(df['car_group'].unique().tolist()),
            key="forecast_car_group"
        )
    
    with col2:
        rental_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(df['rental_period'].unique().tolist()),
            key="forecast_rental_period"
        )
    
    # Filter data
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Prepare data for forecasting
    filtered_df['search_date'] = pd.to_datetime(
        dict(
            year=filtered_df['year'],
            month=filtered_df['month'],
            day=filtered_df['day'],
            hour=filtered_df['hour']
        )
    )
    
    # Create forecasts for each supplier
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Price Forecast")
        
        for supplier in filtered_df['supplier'].unique():
            supplier_data = filtered_df[filtered_df['supplier'] == supplier]
            
            # Prepare data for Prophet
            forecast_df = supplier_data.groupby('search_date')['total_price'].mean().reset_index()
            forecast_df.columns = ['ds', 'y']
            
            # Check if we have enough data points
            if len(forecast_df) < 2:
                st.warning(f"Not enough historical data for {supplier} to make predictions. Need at least 2 data points.")
                continue
                
            try:
                # Create and fit the model
                m = prophet.Prophet(
                    changepoint_prior_scale=0.5,
                    daily_seasonality=False,  # Changed to False as we don't have enough data
                    weekly_seasonality=False,  # Changed to False as we don't have enough data
                    seasonality_mode='additive'  # Changed to additive for more conservative estimates
                )
                m.fit(forecast_df)
                
                # Make future predictions
                future = m.make_future_dataframe(periods=14, freq='D')
                forecast = m.predict(future)
                
                # Create plot
                fig = go.Figure()
                
                # Historical data
                fig.add_trace(go.Scatter(
                    x=forecast_df['ds'],
                    y=forecast_df['y'],
                    name=f'{supplier} (Historical)',
                    mode='markers'
                ))
                
                # Forecast
                fig.add_trace(go.Scatter(
                    x=forecast['ds'].tail(14),
                    y=forecast['yhat'].tail(14),
                    name=f'{supplier} (Forecast)',
                    mode='lines',
                    line=dict(dash='dash')
                ))
                
                # Confidence interval
                fig.add_trace(go.Scatter(
                    x=forecast['ds'].tail(14),
                    y=forecast['yhat_upper'].tail(14),
                    fill=None,
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=forecast['ds'].tail(14),
                    y=forecast['yhat_lower'].tail(14),
                    fill='tonexty',
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    name=f'{supplier} (Confidence Interval)'
                ))
                
                fig.update_layout(
                    title=f'Price Forecast for {supplier}',
                    xaxis_title='Date',
                    yaxis_title='Price (£)',
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error creating forecast for {supplier}: {str(e)}")
    
    with col2:
        st.subheader("Market Insights")
        
        # Calculate trend strength
        for supplier in filtered_df['supplier'].unique():
            supplier_data = filtered_df[filtered_df['supplier'] == supplier]
            prices = supplier_data.groupby('search_date')['total_price'].mean()
            
            if len(prices) < 2:
                st.warning(f"Not enough data points for {supplier} to calculate trends.")
                continue
            
            # Simple trend analysis
            price_change = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100
            
            # Market movement indicators
            st.write(f"**{supplier}**")
            
            # Price trend
            trend_color = "🔴" if price_change < 0 else "🟢"
            st.write(f"{trend_color} Price Trend: {abs(price_change):.1f}% {'decrease' if price_change < 0 else 'increase'}")
            
            # Volatility (using standard deviation)
            volatility = prices.std() / prices.mean() * 100
            st.write(f"📊 Price Volatility: {volatility:.1f}%")
            
            # Market position
            avg_market_price = filtered_df.groupby('search_date')['total_price'].mean().mean()
            supplier_avg_price = prices.mean()
            position = (supplier_avg_price - avg_market_price) / avg_market_price * 100
            
            position_text = "Above" if position > 0 else "Below"
            st.write(f"📍 Market Position: {abs(position):.1f}% {position_text} market average")
            
            st.write("---")
        
        # Add confidence disclaimer
        st.info("""
        **Forecast Confidence Levels:**
        - Short-term (1-3 days): High
        - Medium-term (4-7 days): Medium
        - Long-term (8-14 days): Low
        
        Factors affecting accuracy:
        - Market volatility
        - Seasonal changes
        - Limited historical data
        """)

def competitor_analysis_page(df):
    st.header("Competitor Analysis")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=['All'] + sorted(df['car_group'].unique().tolist()),
            key="competitor_car_group"
        )
    
    with col2:
        rental_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(df['rental_period'].unique().tolist()),
            key="competitor_rental_period"
        )
    
    # Filter data
    filtered_df = df[df['rental_period'] == rental_period]
    if selected_car_group != 'All':
        filtered_df = filtered_df[filtered_df['car_group'] == selected_car_group]
    
    # Calculate market share
    market_share = filtered_df.groupby('supplier')['car_group'].count()
    market_share = (market_share / market_share.sum() * 100).round(2)
    
    # Create market share pie chart
    fig1 = go.Figure(data=[go.Pie(
        labels=market_share.index,
        values=market_share.values,
        hole=.3
    )])
    fig1.update_layout(title='Market Share by Supplier (%)')
    
    # Price positioning
    price_positioning = filtered_df.groupby('supplier')['total_price'].agg(['mean', 'min', 'max']).round(2)
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.subheader("Price Positioning")
        st.dataframe(price_positioning.style.format({
            'mean': '£{:.2f}',
            'min': '£{:.2f}',
            'max': '£{:.2f}'
        }))

def main():
    st.title("Market Analysis Dashboard")
    
    # Initialize AWS credentials
    iam.get_aws_credentials(st.secrets["aws_credentials"])
    
    # Load data
    with st.spinner("Loading market data..."):
        df = load_historical_data()
    
    if df.empty:
        st.error("No data available for analysis")
        return
        
    # Display data availability
    display_data.display_data_availability(
        df,
        "Scheduled",
        {"date": "2024-10-29", "time": "17:00:00"}
    )
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Market Overview", 
        "Daily Snapshot", 
        "Pace View", 
        "Future Trends (Alpha Testing)",
        "Competitor Analysis"
    ])
    
    with tab1:
        market_overview_page(df)
    
    with tab2:
        daily_snapshot_page(df)
    
    with tab3:
        pace_view_page(df)
    
    with tab4:
        future_trends_page(df)
    
    with tab5:
        competitor_analysis_page(df)

if __name__ == "__main__":
    main()
