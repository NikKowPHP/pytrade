
import numpy as np
import pandas as pd
from services.logger import Logger

class MathService:
    def __init__(self):
        self.logger = Logger()

    def monte_carlo_simulation(self, df, days_lookback=30, simulations=10000):
        """
        Runs a Monte Carlo simulation to predict probable High/Low range for the next day.
        """
        try:
            if df is None or len(df) < days_lookback:
                return "Insufficient Data for Simulation", {}

            # 1. Prepare Data
            data = df['Close'].iloc[-days_lookback:].copy()
            
            # Log Returns: ln(Pt / Pt-1)
            log_returns = np.log(1 + data.pct_change())
            
            # Drift and Variance
            mean = log_returns.mean()
            var = log_returns.var()
            stdev = log_returns.std()
            
            drift = mean - (0.5 * var)
            
            # 2. Run Simulation
            # We want to simulate the NEXT day's close
            # Z is a random variable from standard normal distribution
            Z = np.random.normal(0, 1, simulations)
            
            last_price = data.iloc[-1]
            
            # Simulated prices for tomorrow
            # P_t = P_0 * exp(drift + stdev * Z)
            simulated_prices = last_price * np.exp(drift + stdev * Z)
            
            # 3. Determine Confidence Intervals (Range)
            # 85% Probability (approx 1 std deviation equivalent in valid range terms)
            # Lower 7.5% and Upper 92.5% to get middle 85%
            # Or simplified: Probable Range.
            
            # Let's define the "Probable Daily Range" (PDR)
            lower_bound = np.percentile(simulated_prices, 15) # 85% chance price > this
            upper_bound = np.percentile(simulated_prices, 85) # 85% chance price < this
            
            # Extreme boundaries (99%)
            extreme_low = np.percentile(simulated_prices, 1)
            extreme_high = np.percentile(simulated_prices, 99)

            text = (
                f"MONTE CARLO SIMULATION (Next Candle):\n"
                f"- Probable Low (85%): {lower_bound:.5f}\n"
                f"- Probable High (85%): {upper_bound:.5f}\n"
                f"- Volatility (30d): {stdev*100:.2f}%\n"
                f"- Note: 70% probability price stays between bounds."
            )
            
            ranges = {
                "probable_low": lower_bound,
                "probable_high": upper_bound,
                "extreme_low": extreme_low,
                "extreme_high": extreme_high
            }
            
            return text, ranges
            
        except Exception as e:
            self.logger.error(f"Monte Carlo Error: {e}")
            return "Simulation Failed", {}
