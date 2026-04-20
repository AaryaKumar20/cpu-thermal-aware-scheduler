"""
ML-based Thermal Predictor using Random Forest.
Predicts core temperature N ticks ahead to enable proactive frequency scaling.
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from constants import FREQ_LEVELS, VOLTAGE_MAP, IDLE_POWER, AMBIENT_TEMP


class ThermalPredictor:
    def __init__(self, lookahead=3):
        self.lookahead = lookahead
        self.model = None

    def _generate_training_data(self, n_samples=2000):
        """
        Generate synthetic training data by simulating thermal dynamics.
        Features: [current_temp, freq, power, utilization]
        Target: temperature after `lookahead` ticks
        """
        np.random.seed(42)
        X = []
        y = []

        for _ in range(n_samples):
            # Random starting conditions
            temp = np.random.uniform(35.0, 75.0)
            freq = np.random.choice(FREQ_LEVELS)
            utilization = np.random.uniform(0.3, 1.0)

            # Calculate power for this configuration
            voltage = VOLTAGE_MAP[freq]
            is_active = np.random.random() > 0.2  # 80% chance active
            if is_active:
                power = (voltage ** 2) * freq + IDLE_POWER
            else:
                power = IDLE_POWER

            features = [temp, freq, power, utilization]

            # Simulate thermal dynamics for `lookahead` ticks
            future_temp = temp
            for _ in range(self.lookahead):
                heat = power * 0.8
                cool = 0.03 * (future_temp - AMBIENT_TEMP)
                future_temp += heat - cool
                future_temp = max(35.0, future_temp)

            X.append(features)
            y.append(future_temp)

        return np.array(X), np.array(y)

    def train(self):
        """Train the Random Forest model on synthetic thermal data."""
        X, y = self._generate_training_data()
        self.model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X, y)

    def predict(self, current_temp, freq, power, utilization):
        """
        Predict temperature `lookahead` ticks into the future.

        Args:
            current_temp: Current core temperature
            freq: Current frequency level
            power: Current power consumption
            utilization: Task utilization

        Returns:
            Predicted future temperature (float)
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        features = np.array([[current_temp, freq, power, utilization]])
        return float(self.model.predict(features)[0])

    def get_feature_importance(self):
        """Return feature importance from the trained model."""
        if self.model is None:
            return {}
        names = ["Temperature", "Frequency", "Power", "Utilization"]
        importances = self.model.feature_importances_
        return dict(zip(names, importances))
