import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

def prepare_forecast_data(df):
    """Prepare data for Prophet forecasting"""
    # Convert date components to datetime
    df['date'] = pd.to_datetime(
        dict(year=df['year'], month=df['month'], day=df['day'])
    ).dt.date
    
    # Calculate daily average price
    forecast_df = df.groupby('date')['total_price'].mean().reset_index()
    
    # Rename columns to Prophet requirements
    forecast_df.columns = ['ds', 'y']
    
    # Drop any NaN values
    forecast_df = forecast_df.dropna()
    
    return forecast_df

def create_forecast_chart(df):
    """Create forecast chart using Prophet"""
    try:
        from prophet import Prophet
    except ImportError:
        return None
    
    # Prepare data for Prophet
    forecast_df = prepare_forecast_data(df)
    
    # Check for sufficient data points
    if len(forecast_df) < 3:
        raise ValueError("Need at least 3 days of historical data for forecasting")
    
    # Create and fit model
    model = Prophet(
        changepoint_prior_scale=0.5,
        daily_seasonality=False,
        weekly_seasonality=False,
        seasonality_mode='additive'
    )
    
    model.fit(forecast_df)
    
    # Make forecast
    future = model.make_future_dataframe(periods=14, freq='D')
    forecast = model.predict(future)
    
    # Create visualization
    fig = go.Figure()
    
    # Add historical data
    fig.add_trace(go.Scatter(
        x=forecast_df['ds'],
        y=forecast_df['y'],
        name='Historical',
        mode='markers+lines'
    ))
    
    # Add forecast
    fig.add_trace(go.Scatter(
        x=forecast['ds'].tail(14),
        y=forecast['yhat'].tail(14),
        name='Forecast',
        mode='lines',
        line=dict(dash='dot')
    ))
    
    # Add confidence interval
    fig.add_trace(go.Scatter(
        x=forecast['ds'].tail(14),
        y=forecast['yhat_upper'].tail(14),
        fill=None,
        mode='lines',
        line_color='rgba(0,100,80,0.2)',
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter(
        x=forecast['ds'].tail(14),
        y=forecast['yhat_lower'].tail(14),
        fill='tonexty',
        mode='lines',
        line_color='rgba(0,100,80,0.2)',
        name='95% Confidence'
    ))
    
    fig.update_layout(
        title='14-Day Price Forecast',
        xaxis_title='Date',
        yaxis_title='Price (£)',
        height=500,
        showlegend=True
    )
    
    return fig

def create_competitor_chart(df):
    """Create competitor analysis chart comparing prices and market share"""
    # Calculate average prices per supplier
    avg_prices = df.groupby(['supplier', 'car_group'])['total_price'].agg([
        'mean', 'count'
    ]).reset_index()
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Add price bars
    fig.add_trace(
        go.Bar(
            x=avg_prices['supplier'],
            y=avg_prices['mean'],
            name='Average Price',
            yaxis='y',
            text=avg_prices['mean'].round(2),
            textposition='auto',
        )
    )
    
    # Add market share line
    total_vehicles = avg_prices['count'].sum()
    market_share = (avg_prices['count'] / total_vehicles * 100).round(1)
    
    fig.add_trace(
        go.Scatter(
            x=avg_prices['supplier'],
            y=market_share,
            name='Market Share %',
            yaxis='y2',
            line=dict(color='red'),
            mode='lines+markers+text',
            text=market_share.apply(lambda x: f'{x}%'),
            textposition='top center'
        )
    )
    
    fig.update_layout(
        title='Competitor Price Comparison and Market Share',
        yaxis=dict(title='Average Price (£)'),
        yaxis2=dict(
            title='Market Share (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        height=500,
        showlegend=True,
        barmode='group'
    )
    
    return fig

def create_price_distribution_plot(df):
    """Create price distribution plot"""
    fig = go.Figure()
    
    for supplier in df['supplier'].unique():
        supplier_data = df[df['supplier'] == supplier]
        fig.add_trace(go.Box(
            y=supplier_data['total_price'],
            name=supplier,
            boxpoints='outliers'
        ))
    
    fig.update_layout(
        title='Price Distribution by Supplier',
        yaxis_title='Price (£)',
        height=500
    )
    
    return fig

def create_daily_price_chart(df):
    """Create daily price trend chart"""
    df['date'] = pd.to_datetime(
        dict(year=df['year'], month=df['month'], day=df['day'])
    ).dt.date
    
    daily_avg = df.groupby(['date', 'supplier'])['total_price'].mean().reset_index()
    
    fig = go.Figure()
    
    for supplier in daily_avg['supplier'].unique():
        supplier_data = daily_avg[daily_avg['supplier'] == supplier]
        fig.add_trace(go.Scatter(
            x=supplier_data['date'],
            y=supplier_data['total_price'],
            name=supplier,
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title='Daily Price Trends',
        xaxis_title='Date',
        yaxis_title='Average Price (£)',
        height=500
    )
    
    return fig

def create_pace_chart(df):
    """Create pace view chart showing inventory changes"""
    df['date'] = pd.to_datetime(
        dict(year=df['year'], month=df['month'], day=df['day'])
    ).dt.date
    
    daily_counts = df.groupby(['date', 'supplier']).size().reset_index(name='count')
    
    fig = go.Figure()
    
    for supplier in daily_counts['supplier'].unique():
        supplier_data = daily_counts[daily_counts['supplier'] == supplier]
        fig.add_trace(go.Scatter(
            x=supplier_data['date'],
            y=supplier_data['count'],
            name=supplier,
            mode='lines+markers'
        ))
    
    fig.update_layout(
        title='Inventory Pace Trend',
        xaxis_title='Date',
        yaxis_title='Number of Vehicles',
        height=500
    )
    
    return fig