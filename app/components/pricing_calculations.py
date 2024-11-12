def calculate_suggested_price(df, desired_position, handle_ties=False):
    sorted_prices = df.sort_values('total_price')
    competitor_data = sorted_prices[['supplier', 'total_price']].copy()
    
    green_motion_entries = get_green_motion_entries(competitor_data)
    
    if desired_position == 0:
        return calculate_cheapest_price(competitor_data)
    
    if handle_ties:
        return calculate_with_ties(competitor_data, green_motion_entries, desired_position)
    
    return calculate_sequential(competitor_data, green_motion_entries, desired_position)

def get_green_motion_entries(competitor_data):
    return competitor_data[
        competitor_data['supplier'].str.contains('GREEN MOTION', case=False, na=False)
    ]

def calculate_cheapest_price(competitor_data):
    return competitor_data.iloc[0]['total_price'] * 0.95

def calculate_with_ties(competitor_data, green_motion_entries, desired_position):
    unique_prices = sorted(competitor_data['total_price'].unique())
    
    if len(unique_prices) <= desired_position + 1:
        return competitor_data['total_price'].max() * 1.05
        
    price_at_position = unique_prices[desired_position]
    price_at_next = unique_prices[desired_position + 1]
    return (price_at_position + price_at_next) / 2

def calculate_sequential(competitor_data, green_motion_entries, desired_position):
    if len(competitor_data) <= desired_position + 1:
        return competitor_data['total_price'].max() * 1.05
        
    price_at_position = competitor_data.iloc[desired_position]['total_price']
    price_at_next = competitor_data.iloc[desired_position + 1]['total_price']
    return (price_at_position + price_at_next) / 2
