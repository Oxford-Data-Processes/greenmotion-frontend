import streamlit as st
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
import pandas as pd
import re

@st.cache_resource
def load_qa_model():
    """Load and cache the question-answering model"""
    try:
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-distilled-squad")
        model = AutoModelForQuestionAnswering.from_pretrained("distilbert-base-uncased-distilled-squad")
        return tokenizer, model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None, None

def generate_context_from_data(df, question):
    """Generate relevant context from the DataFrame based on the question"""
    try:
        filtered_df = df.copy()
        
        # Extract car group if mentioned (e.g., "2A", "1B", etc.)
        car_group_match = re.search(r'\b[1-9][A-Z]\b', question)
        if car_group_match and 'car_group' in filtered_df.columns:
            car_group = car_group_match.group()
            filtered_df = filtered_df[filtered_df['car_group'] == car_group]
        
        # Handle comparison between Green Motion ("us") and other suppliers
        if 'us' in question.lower() and 'supplier' in filtered_df.columns:
            green_motion_data = filtered_df[filtered_df['supplier'].str.contains('GREEN MOTION', case=False)]
            other_supplier = None
            
            # Check for specific supplier mentions
            suppliers = ['HERTZ', 'ENTERPRISE', 'EUROPCAR', 'SIXT']
            for supplier in suppliers:
                if supplier.lower() in question.lower():
                    other_supplier = supplier
                    break
            
            if other_supplier:
                other_supplier_data = filtered_df[filtered_df['supplier'].str.contains(other_supplier, case=False)]
                
                if not green_motion_data.empty and not other_supplier_data.empty:
                    gm_avg = green_motion_data['total_price'].mean()
                    other_avg = other_supplier_data['total_price'].mean()
                    diff = gm_avg - other_avg
                    
                    context = f"""
                    For {car_group_match.group() if car_group_match else 'all categories'}:
                    Green Motion average price: £{gm_avg:.2f}
                    {other_supplier} average price: £{other_avg:.2f}
                    Price difference: £{abs(diff):.2f} {'higher' if diff > 0 else 'lower'} than {other_supplier}
                    Number of Green Motion vehicles: {len(green_motion_data)}
                    Number of {other_supplier} vehicles: {len(other_supplier_data)}
                    """
                    return context
        
        # If no specific comparison or filtering worked, return general stats
        context = f"""
        Based on the available data:
        Average price: £{filtered_df['total_price'].mean():.2f}
        Minimum price: £{filtered_df['total_price'].min():.2f}
        Maximum price: £{filtered_df['total_price'].max():.2f}
        Number of vehicles: {len(filtered_df)}
        """
        
        if 'supplier' in filtered_df.columns:
            supplier_stats = filtered_df.groupby('supplier')['total_price'].agg(['mean', 'count'])
            context += "\nBreakdown by supplier:\n"
            for supplier, stats in supplier_stats.iterrows():
                context += f"{supplier}: £{stats['mean']:.2f} (based on {stats['count']} vehicles)\n"
        
        return context

    except Exception as e:
        return f"Error generating context: {str(e)}"

def answer_question(question, context, tokenizer, model):
    """Generate an answer for a given question using the provided context"""
    try:
        # For comparison questions, format a more natural response
        if ("difference" in question.lower() or "compare" in question.lower()) and "Price difference:" in context:
            # Extract relevant information from context
            lines = context.split('\n')
            gm_line = next(line for line in lines if "Green Motion average price:" in line)
            hertz_line = next(line for line in lines if "HERTZ average price:" in line)
            diff_line = next(line for line in lines if "Price difference:" in line)
            gm_count = next(line for line in lines if "Number of Green Motion vehicles:" in line)
            hertz_count = next(line for line in lines if "Number of HERTZ vehicles:" in line)
            
            # Extract the category if present
            category = "this category"
            category_match = re.search(r'\b[1-9][A-Z]\b', question)
            if category_match:
                category = f"category {category_match.group()}"
            
            # Format a natural response
            response = f"""Based on our current data for {category}:
- {gm_line.strip()}
- {hertz_line.strip()}
- {diff_line.strip()}

This comparison is based on {gm_count.strip()} and {hertz_count.strip()}."""
            
            return response

        # For other questions, use the QA model
        inputs = tokenizer(
            question,
            context,
            add_special_tokens=True,
            return_tensors="pt",
            max_length=512,
            truncation=True
        )

        with torch.no_grad():
            outputs = model(**inputs)

        answer_start = torch.argmax(outputs.start_logits)
        answer_end = torch.argmax(outputs.end_logits) + 1

        answer = tokenizer.convert_tokens_to_string(
            tokenizer.convert_ids_to_tokens(inputs["input_ids"][0][answer_start:answer_end])
        )

        answer = clean_answer(answer)
        if not answer or answer.isspace():
            return "Based on the data, " + context.split('\n')[1].strip()

        return answer

    except Exception as e:
        return f"I encountered an error while processing your question: {str(e)}"

def clean_answer(answer):
    """Clean and format the model's answer"""
    # Remove special tokens and extra whitespace
    answer = re.sub(r'\[CLS\]|\[SEP\]', '', answer)
    answer = ' '.join(answer.split())
    return answer.strip()

def is_visualization_request(question):
    """Check if the question is requesting a visualization"""
    viz_keywords = ['show', 'plot', 'graph', 'chart', 'visualize', 'display']
    return any(keyword in question.lower() for keyword in viz_keywords)

def extract_query_parameters(question):
    """Extract parameters from the question for visualization"""
    params = {
        'type': 'general',
        'supplier': None,
        'rental_period': None,
        'car_group': None
    }
    
    # Add parameter extraction logic here
    
    return params
