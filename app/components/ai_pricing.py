import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from ml.price_optimizer import PriceOptimizer
import plotly.graph_objects as go
import plotly.express as px

def render_ai_pricing(df):
    st.header("AI-Powered Price Optimization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        valid_combinations = df.groupby(['car_group', 'rental_period']).size().reset_index()
        valid_car_groups = valid_combinations['car_group'].unique()
        
        selected_car_group = st.selectbox(
            "Select Car Group",
            options=sorted(valid_car_groups),
            key="ai_pricing_car_group"
        )
        
        valid_periods = valid_combinations[
            valid_combinations['car_group'] == selected_car_group
        ]['rental_period'].unique()
        
        selected_period = st.selectbox(
            "Select Rental Period (Days)",
            options=sorted(valid_periods),
            key="ai_pricing_period"
        )
        
        filtered_count = len(df[
            (df['car_group'] == selected_car_group) & 
            (df['rental_period'] == selected_period)
        ])
        
        if filtered_count > 0:
            st.success(f"✅ {filtered_count} data points available")
        else:
            st.error("❌ No data available for this combination")
    
    with col2:
        future_date = st.date_input(
            "Select Future Date",
            value=datetime.now().date() + timedelta(days=7),
            min_value=datetime.now().date(),
            max_value=datetime.now().date() + timedelta(days=90)
        )
    
    if filtered_count > 0:
        if st.button("Calculate Price", type="primary"):
            optimizer = PriceOptimizer()
            optimal_price, confidence, market_context = optimizer.predict_optimal_price(
                df, selected_car_group, selected_period, future_date
            )
            
            if optimal_price is not None:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Recommended Price", f"£{optimal_price:.2f}")
                
                with col2:
                    st.metric("Confidence Score", f"{confidence}%")
                
                with col3:
                    st.metric("Market Average", f"£{market_context['market_avg']:.2f}")
                    
                st.markdown("### Market Context")
                st.write(f"• Number of competitors: {market_context['competitor_count']}")
                st.write(f"• Price range: £{market_context['market_min']:.2f} - £{market_context['market_max']:.2f}")
                st.write(f"• Most common supplier: {df[df['car_group'] == selected_car_group]['supplier'].mode().iloc[0]}")
                
                st.markdown("### Market Analysis")
                tab1, tab2 = st.tabs(["Price Distribution", "Competitor Analysis"])
                
                filtered_df = df[
                    (df['car_group'] == selected_car_group) &
                    (df['rental_period'] == selected_period)
                ].copy()
                
                dist_fig, comp_fig = create_price_analysis_charts(
                    filtered_df, 
                    optimal_price, 
                    selected_car_group, 
                    selected_period
                )
                
                tab1.plotly_chart(dist_fig, use_container_width=True)
                tab2.plotly_chart(comp_fig, use_container_width=True)

# Add this function to create the visualization
def create_price_analysis_charts(filtered_df, optimal_price, car_group, rental_period):
    # Create price distribution plot
    fig1 = go.Figure()
    
    # Add price distribution
    fig1.add_trace(go.Histogram(
        x=filtered_df['total_price'],
        name='Market Prices',
        nbinsx=30,
        opacity=0.7
    ))
    
    # Add vertical lines for key metrics
    fig1.add_vline(
        x=optimal_price,
        line_dash="dash",
        line_color="red",
        annotation_text="Recommended Price",
        annotation_position="top"
    )
    
    fig1.add_vline(
        x=filtered_df['total_price'].mean(),
        line_dash="dash",
        line_color="green",
        annotation_text="Market Average",
        annotation_position="bottom"
    )
    
    fig1.update_layout(
        title=f"Price Distribution for {car_group} ({rental_period} day rental)",
        xaxis_title="Price (£)",
        yaxis_title="Number of Listings",
        showlegend=True,
        height=400
    )
    
    # Create competitor comparison plot
    competitor_avg = filtered_df.groupby('supplier')['total_price'].agg(['mean', 'count']).reset_index()
    competitor_avg = competitor_avg.sort_values('mean')
    
    fig2 = go.Figure()
    
    # Add competitor bars
    fig2.add_trace(go.Bar(
        x=competitor_avg['supplier'],
        y=competitor_avg['mean'],
        text=competitor_avg['count'].apply(lambda x: f'{x} listings'),
        textposition='auto',
        name='Competitor Prices'
    ))
    
    # Add horizontal line for recommended price
    fig2.add_hline(
        y=optimal_price,
        line_dash="dash",
        line_color="red",
        annotation_text="Recommended Price",
        annotation_position="right"
    )
    
    fig2.update_layout(
        title="Average Price by Competitor",
        xaxis_title="Supplier",
        yaxis_title="Average Price (£)",
        showlegend=True,
        height=500,
        xaxis_tickangle=-45
    )
    
    return fig1, fig2
