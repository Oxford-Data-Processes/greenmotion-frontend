# app/components/ai_chat.py

import streamlit as st
import pandas as pd
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch

# Cache the model and tokenizer to avoid reloading on every interaction
@st.cache_resource
def load_qa_model():
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-distilled-squad")
    model = AutoModelForQuestionAnswering.from_pretrained("distilbert-base-uncased-distilled-squad")
    return tokenizer, model

def render_ai_chat(df):
    st.title("🚀 Rental Pricing AI Assistant")
    st.write("Ask questions about rental pricing trends, predictions, and comparisons.")

    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Text input for user questions
    user_input = st.text_input(
        "Type your question and press Enter",
        placeholder="e.g., What has Enterprise done with their pricing on a 1-day rental over the last 30 days?"
    )

    if user_input:
        tokenizer, model = load_qa_model()
        with st.spinner("Analyzing data..."):
            context = generate_context_from_data(df)
            answer = answer_question(user_input, context, tokenizer, model)
            st.session_state.chat_history.append({"user": user_input, "ai": answer})
            st.experimental_rerun()

    # Display chat history
    for chat in st.session_state.chat_history[::-1]:
        st.write(f"**You:** {chat['user']}")
        st.write(f"**AI:** {chat['ai']}")
        st.markdown("---")

    # Clear conversation button
    if st.button("Clear Conversation"):
        st.session_state.chat_history = []
        st.experimental_rerun()

def answer_question(question, context, tokenizer, model):
    inputs = tokenizer.encode_plus(question, context, add_special_tokens=True, max_length=512, truncation=True, return_tensors="pt")
    input_ids = inputs["input_ids"].tolist()[0]

    outputs = model(**inputs)

    answer_start = torch.argmax(outputs.start_logits)
    answer_end = torch.argmax(outputs.end_logits) + 1

    if answer_end <= answer_start:
        return "I'm sorry, I could not find an answer to your question."

    answer = tokenizer.convert_tokens_to_string(
        tokenizer.convert_ids_to_tokens(input_ids[answer_start:answer_end])
    )

    return answer.strip()

def generate_context_from_data(df):
    # Summarize or select key data points to create the context
    # For demonstration, we will create a context with aggregated data
    grouped = df.groupby(['supplier', 'rental_period']).agg({
        'total_price': ['mean', 'min', 'max']
    }).reset_index()

    context = ""
    for _, row in grouped.iterrows():
        supplier = row['supplier']
        rental_period = row['rental_period']
        mean_price = row[('total_price', 'mean')]
        min_price = row[('total_price', 'min')]
        max_price = row[('total_price', 'max')]
        context += f"{supplier} has average prices of £{mean_price:.2f}, ranging from £{min_price:.2f} to £{max_price:.2f} for {rental_period}-day rentals. "

    return context