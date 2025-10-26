"""
ML-based Fraud Detection using Isolation Forest
Place this file in app/fraud_detection.py
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Tuple
from app import models


class FraudDetector:
    """ML-based fraud detection using Isolation Forest"""
    
    def __init__(self):
        # Initialize Isolation Forest model
        # contamination = expected proportion of outliers (5%)
        self.model = IsolationForest(
            contamination=0.05,
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False
    
    def extract_features(self, amount: float, account: models.Account, db: Session) -> np.array:
        """Extract features for fraud detection"""
        
        # Get transaction history for this account
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        recent_transactions = db.query(models.Transaction).filter(
            models.Transaction.from_account_id == account.id,
            models.Transaction.timestamp >= one_month_ago
        ).all()
        
        # Feature 1: Transaction amount
        feature_amount = amount
        
        # Feature 2: Ratio to account balance
        feature_balance_ratio = amount / account.balance if account.balance > 0 else 0
        
        # Feature 3: Average transaction amount in last month
        if recent_transactions:
            avg_amount = sum(t.amount for t in recent_transactions) / len(recent_transactions)
        else:
            avg_amount = 0
        feature_avg_diff = amount - avg_amount
        
        # Feature 4: Number of transactions in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_hour_count = db.query(models.Transaction).filter(
            models.Transaction.from_account_id == account.id,
            models.Transaction.timestamp >= one_hour_ago
        ).count()
        feature_frequency = recent_hour_count
        
        # Feature 5: Time of day (0-23 hour)
        feature_time = datetime.utcnow().hour
        
        # Feature 6: Day of week (0-6)
        feature_day = datetime.utcnow().weekday()
        
        # Feature 7: Amount to daily limit ratio
        feature_limit_ratio = amount / account.daily_limit
        
        return np.array([[
            feature_amount,
            feature_balance_ratio,
            feature_avg_diff,
            feature_frequency,
            feature_time,
            feature_day,
            feature_limit_ratio
        ]])
    
    def train_on_historical_data(self, db: Session):
        """Train model on historical transaction data"""
        
        # Get all accounts
        accounts = db.query(models.Account).all()
        
        if not accounts:
            print("No accounts found for training")
            return
        
        training_data = []
        
        # Generate training data from historical transactions
        for account in accounts:
            transactions = db.query(models.Transaction).filter(
                models.Transaction.from_account_id == account.id
            ).limit(100).all()
            
            for transaction in transactions:
                # Reconstruct features as they were during transaction
                features = np.array([
                    transaction.amount,
                    transaction.amount / account.balance if account.balance > 0 else 0,
                    transaction.amount,  # Simplified
                    1,  # Simplified frequency
                    transaction.timestamp.hour,
                    transaction.timestamp.weekday(),
                    transaction.amount / account.daily_limit
                ])
                training_data.append(features)
        
        if len(training_data) < 10:
            # Not enough data, use synthetic normal data
            print("Using synthetic training data")
            training_data = self._generate_synthetic_data()
        
        # Train the model
        X_train = np.array(training_data)
        self.model.fit(X_train)
        self.is_trained = True
        print(f"Model trained on {len(training_data)} samples")
    
    def _generate_synthetic_data(self) -> list:
        """Generate synthetic normal transaction data"""
        synthetic_data = []
        
        # Generate 100 normal transactions
        for _ in range(100):
            synthetic_data.append([
                np.random.uniform(100, 10000),      # amount
                np.random.uniform(0.01, 0.3),       # balance ratio
                np.random.uniform(-1000, 1000),     # avg diff
                np.random.randint(0, 3),            # frequency
                np.random.randint(0, 24),           # time
                np.random.randint(0, 7),            # day
                np.random.uniform(0.1, 0.5)         # limit ratio
            ])
        
        return synthetic_data
    
    def predict(self, amount: float, account: models.Account, db: Session) -> Tuple[bool, str, float]:
        """
        Predict if transaction is fraudulent
        Returns: (is_fraud, reason, anomaly_score)
        """
        
        # Train model if not trained
        if not self.is_trained:
            self.train_on_historical_data(db)
        
        # Extract features
        features = self.extract_features(amount, account, db)
        
        # Predict (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(features)[0]
        
        # Get anomaly score (lower = more anomalous)
        anomaly_score = self.model.score_samples(features)[0]
        
        is_fraud = prediction == -1
        
        if is_fraud:
            # Determine specific reason
            if amount > account.daily_limit:
                reason = f"ML detected anomaly: Amount exceeds daily limit (Score: {anomaly_score:.2f})"
            elif amount > (account.balance * 0.8):
                reason = f"ML detected anomaly: Large withdrawal detected (Score: {anomaly_score:.2f})"
            else:
                reason = f"ML detected anomaly: Unusual transaction pattern (Score: {anomaly_score:.2f})"
        else:
            reason = f"Transaction appears normal (Score: {anomaly_score:.2f})"
        
        return is_fraud, reason, float(anomaly_score)


# Global fraud detector instance
fraud_detector = FraudDetector()


def check_fraud_ml(amount: float, account: models.Account, db: Session) -> Tuple[bool, str]:
    """
    Wrapper function for fraud detection
    Combines rule-based and ML-based detection
    """
    
    # Rule-based checks (fast, deterministic)
    if amount > account.daily_limit:
        return True, f"Exceeds daily limit of ₹{account.daily_limit}"
    
    # Check multiple large transactions
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_large = db.query(models.Transaction).filter(
        models.Transaction.from_account_id == account.id,
        models.Transaction.timestamp >= one_hour_ago,
        models.Transaction.amount > 10000
    ).count()
    
    if recent_large >= 3:
        return True, "Multiple large transactions in last hour"
    
    # ML-based detection
    try:
        is_fraud, reason, score = fraud_detector.predict(amount, account, db)
        if is_fraud:
            return True, reason
    except Exception as e:
        # If ML fails, fall back to rule-based only
        print(f"ML detection failed: {e}")
    
    return False, "Transaction approved"