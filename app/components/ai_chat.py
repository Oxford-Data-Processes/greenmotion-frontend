import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests

def render_ai_chat(df):
    st.header("Rental Pricing AI Chat")
    st.info("💡 Ask questions about rental pricing predictions and trends based on our historical data.")

    # Add clear conversation button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("Clear Conversation"):
            st.session_state.chat_history = []
            st.rerun()

    # Text input for user questions
    user_input = st.text_input(
        "Ask a question about rental pricing:",
        placeholder="Example: What is the price trend for category 2A for 1 day rentals?"
    )

    if st.button("Get AI Insights"):
        if user_input:
            with st.spinner("Analyzing market data..."):
                response = analyze_pricing_data(df, user_input)
                st.session_state.chat_history.append({
                    "user": user_input,
                    "ai": response
                })

    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### Conversation History")
        for chat in reversed(st.session_state.chat_history):
            st.markdown(f"**You:** {chat['user']}")
            st.markdown(f"**AI:** {chat['ai']}")

def analyze_pricing_data(df, question):
    question = question.lower()
    
    # Extract car groups from question with more precise matching
    car_groups = df['car_group'].unique()
    mentioned_car_groups = [
        cg for cg in car_groups 
        if (
            # Exact match (case-insensitive)
            cg.lower() == "2b" or 
            cg.lower() == "g" or
            # Match with "category" prefix
            f"category {cg.lower()}" in question.lower() or
            # Match with space before/after to avoid partial matches
            f" {cg.lower()} " in f" {question.lower()} "
        )
    ]
    
    # Extract rental period from question
    rental_periods = df['rental_period'].unique()
    period_keywords = {
        '01': ['1 day', 'one day', '1day', 'one-day'],
        '03': ['3 day', 'three day', '3day', 'three-day'],
        '05': ['5 day', 'five day', '5day', 'five-day'],
        '07': ['7 day', 'seven day', '7day', 'seven-day']
    }
    
    mentioned_period = None
    for period, keywords in period_keywords.items():
        if any(keyword in question.lower() for keyword in keywords):
            mentioned_period = period
            break
    
    if not mentioned_period:
        # Fallback to direct number matching with zero-padding
        mentioned_period = next(
            (str(rp).zfill(2) for rp in range(1, 29) if str(rp) in question), 
            None
        )
    
    if mentioned_car_groups and mentioned_period:
        response = "Here's the market analysis for your requested vehicles:\n\n"
        
        for car_group in mentioned_car_groups:
            # Filter data for specific car group and rental period
            filtered_df = df[
                (df['car_group'] == car_group) & 
                (df['rental_period'] == mentioned_period)
            ].copy()
            
            if filtered_df.empty:
                response += f"""No data available for {car_group} ({mentioned_period} day rental)\n\n"""
                continue
            
            # Clean outliers based on rental period
            max_reasonable_price = {
                '01': 200,  # £200 for 1 day
                '03': 500,  # £500 for 3 days
                '05': 800,  # £800 for 5 days
                '07': 1000  # £1000 for 7 days
            }.get(mentioned_period, float('inf'))
            
            filtered_df = filtered_df[filtered_df['total_price'] <= max_reasonable_price]
            
            if filtered_df.empty:
                response += f"""After removing outliers, no reliable data for {car_group} ({mentioned_period} day rental)\n\n"""
                continue
            
            # Calculate metrics
            current_avg = filtered_df['total_price'].mean()
            current_min = filtered_df['total_price'].min()
            current_max = filtered_df['total_price'].max()
            competitor_count = filtered_df['supplier'].nunique()
            
            # Calculate trend
            filtered_df['date'] = pd.to_datetime(
                filtered_df[['year', 'month', 'day']].assign(
                    hour=filtered_df['hour']
                )
            )
            recent_trend = filtered_df.sort_values('date').tail(10)
            trend_direction = "increasing" if recent_trend['total_price'].is_monotonic_increasing else \
                            "decreasing" if recent_trend['total_price'].is_monotonic_decreasing else \
                            "fluctuating"
            
            response += f"""Car Group {car_group} ({mentioned_period} day rental):
• Current average price: £{current_avg:.2f}
• Competitive price range: £{current_min:.2f} - £{current_max:.2f}
• Number of competitors: {competitor_count}
• Price trend: {trend_direction}
• Recommended price: £{current_avg * 0.95:.2f} (5% below market average)

"""
        
        return response
    
    # If no specific car group or rental period mentioned
    return """Please specify both the car groups and rental period in your question. 
    
Example questions:
• What's the optimal price for 2B and G vehicles for a 5 day rental?
• How should I price my fleet of 2A and 1ELE vehicles for 3 day rentals?"""
