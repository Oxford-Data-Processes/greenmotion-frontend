"""Pre-defined prompts and templates for the AI chat interface"""

SYSTEM_PROMPT = """You are an AI assistant specialized in car rental market analysis. 
You help users understand pricing trends, competitor behavior, and market opportunities. 
Your responses should be clear, concise, and data-driven."""

EXAMPLE_QUESTIONS = [
    "What's the average price for 3-day rentals in the compact car category?",
    "How does Green Motion's pricing compare to Enterprise for 7-day rentals?",
    "Show me the pricing trends for SUVs over the last month",
    "Which competitor has the most aggressive pricing in the luxury segment?",
    "What's the best day of the week to offer promotional rates?"
]

ERROR_MESSAGES = {
    "no_data": "I apologize, but I don't have enough data to answer that question.",
    "invalid_query": "I'm not sure I understood that. Could you rephrase your question?",
    "visualization_error": "I couldn't create the visualization. Please try being more specific.",
    "model_error": "I encountered an error while processing your request. Please try again."
}

def get_context_template(supplier, period, price_data):
    return f"""
    Analysis for {supplier} over {period} days:
    - Average Price: £{price_data['mean']:.2f}
    - Minimum Price: £{price_data['min']:.2f}
    - Maximum Price: £{price_data['max']:.2f}
    - Price Volatility: {price_data['volatility']:.1f}%
    """

def get_comparison_template(supplier1, supplier2, metric, value):
    return f"""
    Comparing {supplier1} vs {supplier2}:
    - {metric}: {value}
    """
