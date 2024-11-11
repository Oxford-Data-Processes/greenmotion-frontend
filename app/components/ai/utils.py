import streamlit as st
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
import re
from datetime import datetime, timedelta

@st.cache_resource
def load_qa_model():
    """Load and cache the question-answering model"""
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            "distilbert-base-uncased-distilled-squad",
            use_auth_token=st.secrets["hugging_face"]["token"]
        )
        model = AutoModelForQuestionAnswering.from_pretrained(
            "distilbert-base-uncased-distilled-squad",
            use_auth_token=st.secrets["hugging_face"]["token"]
        )
        return tokenizer, model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None, None

def answer_question(question, context, tokenizer, model):
    """Generate an answer for a given question using the provided context"""
    try:
        # Prepare inputs
        inputs = tokenizer.encode_plus(
            question, 
            context,
            add_special_tokens=True,
            max_length=512,
            truncation=True,
            return_tensors="pt"
        )
        
        # Get model outputs
        outputs = model(**inputs)
        
        # Find the answer span
        answer_start = torch.argmax(outputs.start_logits)
        answer_end = torch.argmax(outputs.end_logits) + 1
        
        # Convert tokens to answer string
        answer = tokenizer.convert_tokens_to_string(
            tokenizer.convert_ids_to_tokens(
                inputs["input_ids"][0][answer_start:answer_end]
            )
        )
        
        # Clean and format the answer
        answer = clean_answer(answer)
        
        return format_answer(answer, question)
        
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}"

def generate_context_from_data(df):
    """Generate a context string from the DataFrame for the QA model"""
    context = []
    
    # Add overall statistics
    context.append(f"The dataset contains information from {len(df['supplier'].unique())} suppliers.")
    
    # Add supplier-specific information
    for supplier in df['supplier'].unique():
        supplier_data = df[df['supplier'] == supplier]
        avg_price = supplier_data['total_price'].mean()
        min_price = supplier_data['total_price'].min()
        max_price = supplier_data['total_price'].max()
        
        context.append(
            f"{supplier} has an average price of £{avg_price:.2f}, "
            f"ranging from £{min_price:.2f} to £{max_price:.2f}."
        )
        
        # Add rental period specific information
        for period in supplier_data['rental_period'].unique():
            period_data = supplier_data[supplier_data['rental_period'] == period]
            avg_period_price = period_data['total_price'].mean()
            context.append(
                f"For {period}-day rentals, {supplier} charges an average of £{avg_period_price:.2f}."
            )
    
    return " ".join(context)

def is_visualization_request(query):
    """Determine if the user is requesting a visualization"""
    visualization_keywords = [
        'show me',
        'graph',
        'plot',
        'chart',
        'visualize',
        'visualization',
        'compare',
        'trend',
        'trends'
    ]
    return any(keyword in query.lower() for keyword in visualization_keywords)

def extract_query_parameters(query):
    """Extract relevant parameters from the user's query"""
    params = {
        'type': 'general',
        'supplier': None,
        'rental_period': None,
        'car_group': None,
        'date_range': None,
        'compare_suppliers': False
    }
    
    # Extract visualization type
    if any(word in query.lower() for word in ['trend', 'trends', 'over time']):
        params['type'] = 'trend'
    elif any(word in query.lower() for word in ['compare', 'comparison', 'versus', 'vs']):
        params['type'] = 'comparison'
        params['compare_suppliers'] = True
    
    # Extract date range
    date_patterns = {
        'last week': 7,
        'last month': 30,
        'last 30 days': 30,
        'last 7 days': 7,
        'past week': 7,
        'past month': 30
    }
    for pattern, days in date_patterns.items():
        if pattern in query.lower():
            params['date_range'] = days
            break
    
    # Extract rental period
    rental_period_pattern = r'(\d+)[\s-]day'
    if match := re.search(rental_period_pattern, query):
        params['rental_period'] = int(match.group(1))
    
    # Extract car group (assuming format like '2A', '1B', etc.)
    car_group_pattern = r'\b[1-9][A-Z]\b'
    if match := re.search(car_group_pattern, query):
        params['car_group'] = match.group(0)
    
    return params

def clean_answer(answer):
    """Clean and format the model's answer"""
    # Remove special tokens
    answer = re.sub(r'\[CLS\]|\[SEP\]', '', answer)
    # Remove extra whitespace
    answer = ' '.join(answer.split())
    return answer.strip()

def format_answer(answer, question):
    """Format the answer based on the question type"""
    if not answer or answer.isspace():
        return "I apologize, but I couldn't find a specific answer to your question. Could you please rephrase it?"
    
    # Format currency values
    currency_pattern = r'£?\s*\d+\.?\d*'
    if re.search(currency_pattern, answer):
        answer = re.sub(r'(\d+\.?\d*)', r'£\1', answer)
    
    # Add context based on question type
    if 'average' in question.lower() or 'mean' in question.lower():
        answer = f"The average {answer}"
    elif 'difference' in question.lower():
        answer = f"The difference is {answer}"
    elif 'compare' in question.lower():
        answer = f"Based on the comparison, {answer}"
    
    return answer
