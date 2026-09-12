import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import json
import os

class InventoryPredictor:
    """Predict future reagent usage using machine learning."""
    
    def __init__(self, reagent_id=None):
        self.reagent_id = reagent_id
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_data(self, usage_history):
        """Prepare data for training from usage history."""
        if len(usage_history) < 10:
            return None, None
        
        # Create features from usage history
        df = pd.DataFrame(list(usage_history))
        df['date_used'] = pd.to_datetime(df['date_used'])
        df['day_of_week'] = df['date_used'].dt.dayofweek
        df['day_of_month'] = df['date_used'].dt.day
        df['month'] = df['date_used'].dt.month
        df['quarter'] = df['date_used'].dt.quarter
        
        # Additional features
        df['cumulative_usage'] = df['quantity_used'].cumsum()
        df['days_since_first'] = (df['date_used'] - df['date_used'].min()).dt.days
        
        # Lag features
        df['usage_lag_1'] = df['quantity_used'].shift(1)
        df['usage_lag_2'] = df['quantity_used'].shift(2)
        df['usage_lag_3'] = df['quantity_used'].shift(3)
        df['rolling_mean_7'] = df['quantity_used'].rolling(window=7, min_periods=1).mean()
        df['rolling_std_7'] = df['quantity_used'].rolling(window=7, min_periods=1).std()
        
        # Drop rows with NaN
        df = df.dropna()
        
        if len(df) < 5:
            return None, None
        
        # Select features
        feature_cols = ['day_of_week', 'day_of_month', 'month', 'quarter', 
                       'usage_lag_1', 'usage_lag_2', 'usage_lag_3',
                       'rolling_mean_7', 'rolling_std_7']
        
        X = df[feature_cols]
        y = df['quantity_used']
        
        return X, y
    
    def train(self, usage_history):
        """Train the model on usage history."""
        X, y = self.prepare_data(usage_history)
        if X is None or y is None:
            self.is_trained = False
            return False
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        return True
    
    def predict(self, days=30):
        """Predict usage for the next n days."""
        if not self.is_trained:
            return None
        
        # Generate future dates
        future_dates = [datetime.now() + timedelta(days=i) for i in range(1, days+1)]
        predictions = []
        
        for date in future_dates:
            features = {
                'day_of_week': date.weekday(),
                'day_of_month': date.day,
                'month': date.month,
                'quarter': (date.month - 1) // 3 + 1,
                'usage_lag_1': predictions[-1] if predictions else 0,
                'usage_lag_2': predictions[-2] if len(predictions) > 1 else 0,
                'usage_lag_3': predictions[-3] if len(predictions) > 2 else 0,
                'rolling_mean_7': np.mean(predictions[-7:]) if predictions else 0,
                'rolling_std_7': np.std(predictions[-7:]) if len(predictions) > 1 else 0,
            }
            X_pred = pd.DataFrame([features])
            X_pred_scaled = self.scaler.transform(X_pred)
            pred = self.model.predict(X_pred_scaled)[0]
            predictions.append(max(0, pred))  # Ensure non-negative
        
        total_predicted = sum(predictions)
        avg_daily = total_predicted / days
        weekly = total_predicted / (days / 7)
        
        return {
            'total_predicted': total_predicted,
            'avg_daily': avg_daily,
            'weekly_avg': weekly,
            'predictions': predictions,
            'confidence': min(0.95, 0.6 + 0.01 * len(predictions)) if self.is_trained else 0,
            'confidence_pct': (min(0.95, 0.6 + 0.01 * len(predictions)) if self.is_trained else 0) * 100,
        }

def generate_synthetic_usage(reagent, months=3):
    """Generate synthetic usage data for a reagent."""
    from faker import Faker
    import random
    from decimal import Decimal
    
    fake = Faker()
    usage_data = []
    start_date = datetime.now() - timedelta(days=months*30)
    
    # Base usage patterns
    base_usage = float(reagent.minimum_quantity * 0.3)
    variability = base_usage * 0.4
    
    # Weekly pattern - higher usage on weekdays
    for i in range(months * 30):
        date = start_date + timedelta(days=i)
        day = date.weekday()
        if day < 5:  # Weekday
            multiplier = 1.0 + random.uniform(-0.3, 0.3)
        else:  # Weekend
            multiplier = 0.5 + random.uniform(-0.2, 0.2)
        
        quantity = base_usage * multiplier + random.uniform(-variability, variability)
        quantity = max(0.1, quantity)
        
        usage_data.append({
            'date_used': date,
            'quantity_used': round(quantity, 2),
            'user': fake.name(),
            'notes': fake.sentence(),
        })
    
    return usage_data
