import pandas as pd
import numpy as np

class PriceOptimizer:
    def predict_optimal_price(self, historical_df, car_group, rental_period, future_date):
        try:
            filtered_df = historical_df[
                (historical_df['car_group'] == car_group) &
                (historical_df['rental_period'] == rental_period)
            ].copy()
            
            if filtered_df.empty:
                return None, None, None
            
            filtered_df['total_price'] = pd.to_numeric(filtered_df['total_price'], errors='coerce')
            
            if rental_period == '01' or rental_period == 1:
                max_reasonable_price = {
                    '2A': 200,
                    '2B': 180,
                    '2C': 160,
                    '3A': 250,
                    '3B': 230,
                    '1ELE': 150,
                    'default': 150
                }
                price_cap = max_reasonable_price.get(car_group, max_reasonable_price['default'])
                filtered_df = filtered_df[filtered_df['total_price'] <= price_cap]
            
            if filtered_df.empty:
                return None, None, None
            
            market_avg = filtered_df['total_price'].mean()
            market_min = filtered_df['total_price'].min()
            market_max = filtered_df['total_price'].max()
            
            green_motion_prices = filtered_df[
                filtered_df['supplier'].str.contains('GREEN MOTION', case=False, na=False)
            ]
            
            if not green_motion_prices.empty:
                current_price = green_motion_prices['total_price'].mean()
                optimal_price = current_price
            else:
                if rental_period == '01' or rental_period == 1:
                    optimal_price = market_avg * 0.85
                    if car_group == '2A':
                        optimal_price = min(optimal_price, 150)
                    elif car_group in ['2B', '2C']:
                        optimal_price = min(optimal_price, 120)
                    else:
                        optimal_price = min(optimal_price, 100)
                else:
                    optimal_price = market_avg * 0.9
            
            min_price = max(market_min * 1.05, market_avg * 0.7)
            max_price = min(market_max * 0.85, market_avg * 1.15)
            optimal_price = max(min_price, min(optimal_price, max_price))
            
            data_points = len(filtered_df)
            price_spread = (market_max - market_min) / market_avg if market_avg > 0 else 1
            competitor_count = len(filtered_df['supplier'].unique())
            
            confidence_score = (
                min(data_points / 30, 1) *
                (1 - min(price_spread, 0.5)) *
                min(competitor_count / 5, 1) *
                100
            )
            
            market_context = {
                "market_min": market_min,
                "market_max": market_max,
                "market_avg": market_avg,
                "competitor_count": competitor_count,
                "data_points": data_points
            }
            
            return round(optimal_price, 2), round(confidence_score, 1), market_context
            
        except Exception as e:
            return None, None, None
