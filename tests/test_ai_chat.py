import pytest
import pandas as pd
from datetime import datetime, timedelta
from app.components.ai.utils import (
    extract_query_parameters,
    is_visualization_request,
    clean_answer,
    format_answer
)

@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    data = []
    
    for date in dates:
        for supplier in ['GREEN MOTION', 'ENTERPRISE', 'HERTZ']:
            for rental_period in [1, 3, 7]:
                data.append({
                    'date': date,
                    'supplier': supplier,
                    'rental_period': rental_period,
                    'car_group': '2A',
                    'total_price': 100 + rental_period * 10
                })
    
    return pd.DataFrame(data)

def test_visualization_request_detection():
    """Test the visualization request detection"""
    assert is_visualization_request("Show me a graph of prices")
    assert is_visualization_request("Can you plot the trends?")
    assert not is_visualization_request("What is the average price?")

def test_parameter_extraction():
    """Test query parameter extraction"""
    query = "Show me Enterprise's pricing trends for 3-day rentals over the last week"
    params = extract_query_parameters(query)
    
    assert params['type'] == 'trend'
    assert params['rental_period'] == 3
    assert params['date_range'] == 7

def test_answer_formatting():
    """Test answer cleaning and formatting"""
    raw_answer = "[CLS] The price is 100 [SEP]"
    clean = clean_answer(raw_answer)
    assert clean == "The price is 100"
    
    formatted = format_answer("100", "What is the average price?")
    assert formatted.startswith("The average")

def test_error_handling(sample_df):
    """Test error handling in various scenarios"""
    # Test empty DataFrame
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError):
        extract_query_parameters("")
    
    # Test invalid date range
    query = "Show me prices from 1900"
    params = extract_query_parameters(query)
    assert params['date_range'] is None

if __name__ == "__main__":
    pytest.main([__file__])
