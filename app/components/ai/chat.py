import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from .utils import (
    load_qa_model,
    answer_question,
    generate_context_from_data,
    is_visualization_request,
    extract_query_parameters
)

def render_ai_chat(df):
    """Main function to render the AI chat interface"""
    
    # Load the QA model at the start
    tokenizer, model = load_qa_model()
    if tokenizer is None or model is None:
        st.error("Failed to load AI model. Please try again later.")
        return
    
    # Setup the chat interface
    st.title("🤖 AI Rental Market Analyst")
    
    # Add an engaging introduction
    st.markdown("""
    Welcome to your AI Rental Market Analyst! I can help you:
    - 📊 Analyze pricing trends
    - 📈 Generate visualizations
    - 🔍 Compare competitors
    - 🎯 Identify market opportunities
    
    Try asking questions like:
    - "What has Enterprise done with their pricing on 1-day rentals over the last 30 days?"
    - "Show me a graph comparing Green Motion to Enterprise for 3-day rentals"
    - "What's the average price difference between us and Hertz for category 2A?"
    """)

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Create a container for the chat history
    chat_container = st.container()

    # Add the input field at the bottom
    with st.container():
        col1, col2 = st.columns([6, 1])
        with col1:
            user_input = st.text_input(
                "Ask me anything about the rental market...",
                key="user_input",
                placeholder="e.g., Show me Enterprise's pricing trends for the last week"
            )
        with col2:
            clear_button = st.button("Clear Chat")
            if clear_button:
                st.session_state.chat_history = []
                st.rerun()

    # Process user input
    if user_input:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        try:
            # Check if it's a visualization request
            if is_visualization_request(user_input):
                params = extract_query_parameters(user_input)
                fig = create_visualization(df, params)
                response = "Here's the visualization you requested:"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response,
                    "visualization": fig
                })
            else:
                # Generate context and get AI response
                context = generate_context_from_data(df, user_input)
                response = answer_question(user_input, context, tokenizer, model)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response
                })
        except Exception as e:
            error_message = f"I apologize, but I encountered an error: {str(e)}"
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": error_message
            })

    # Display chat history
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**AI:** {message['content']}")
                if "visualization" in message:
                    st.plotly_chart(message["visualization"], use_container_width=True)

def create_visualization(df, params):
    """Create visualization based on user request and parameters"""
    if params.get('type') == 'trend':
        return create_trend_visualization(df, params)
    elif params.get('type') == 'comparison':
        return create_comparison_visualization(df, params)
    else:
        return create_general_visualization(df, params)

def create_trend_visualization(df, params):
    """Create a trend visualization"""
    fig = px.line(
        df,
        x='date',
        y='total_price',
        color='supplier' if params.get('compare_suppliers') else None,
        title=f"Price Trends for {params.get('supplier', 'All Suppliers')}",
        labels={'total_price': 'Total Price (£)', 'date': 'Date'}
    )
    
    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        legend_title_text='Supplier'
    )
    
    return fig

def create_comparison_visualization(df, params):
    """Create a comparison visualization"""
    fig = px.box(
        df,
        x='supplier',
        y='total_price',
        color='supplier',
        title=f"Price Comparison for {params.get('car_group', 'All Car Groups')}",
        labels={'total_price': 'Total Price (£)', 'supplier': 'Supplier'}
    )
    
    fig.update_layout(
        template='plotly_white',
        showlegend=False
    )
    
    return fig

def create_general_visualization(df, params):
    """Create a general visualization"""
    fig = px.scatter(
        df,
        x='date',
        y='total_price',
        color='supplier',
        size='rental_period',
        title="Market Overview",
        labels={
            'total_price': 'Total Price (£)',
            'date': 'Date',
            'rental_period': 'Rental Period (Days)'
        }
    )
    
    fig.update_layout(
        template='plotly_white',
        hovermode='closest'
    )
    
    return fig
