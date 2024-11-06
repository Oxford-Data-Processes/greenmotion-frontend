import pandas as pd

def calculate_market_stats(df):
    return df.groupby('supplier').agg({
        'total_price': ['mean', 'min', 'count']
    }).round(2)

def calculate_market_insights(df):
    insights = {}
    
    for supplier in df['supplier'].unique():
        supplier_data = df[df['supplier'] == supplier]
        prices = supplier_data.groupby('date')['total_price'].mean()
        
        if len(prices) >= 2:
            insights[supplier] = calculate_supplier_insights(
                prices, 
                df['total_price'].mean()
            )
    
    return insights

def calculate_supplier_insights(prices, market_avg):
    price_change = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] * 100
    volatility = prices.std() / prices.mean() * 100
    position = (prices.mean() - market_avg) / market_avg * 100
    
    return {
        'Price Trend': format_trend(price_change),
        'Volatility': format_volatility(volatility),
        'Market Position': format_position(position)
    }

def format_trend(change):
    return {
        'icon': '🔴' if change < 0 else '🟢',
        'text': f"{abs(change):.1f}% {'decrease' if change < 0 else 'increase'}"
    }

def format_volatility(volatility):
    return {
        'icon': '📊',
        'text': f"{volatility:.1f}%"
    }

def format_position(position):
    return {
        'icon': '📍',
        'text': f"{abs(position):.1f}% {'above' if position > 0 else 'below'} market average"
    }