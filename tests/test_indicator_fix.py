import pandas as pd
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.market_data import MarketDataProvider
from unittest.mock import MagicMock

def test_fix():
    provider = MarketDataProvider()
    # Mock logger to avoid actual logging if needed, or just let it run
    provider.logger = MagicMock()
    
    # 2 rows of data - should result in None indicators
    data = {
        'High': [1.1, 1.2],
        'Low': [1.0, 1.1],
        'Close': [1.05, 1.15]
    }
    df = pd.DataFrame(data)
    
    print("Testing calculate_indicators with 2 rows...")
    try:
        result_df = provider.calculate_indicators(df)
        print("Success! No exception raised.")
        
        # Check if logger info was called with "N/A"
        calls = provider.logger.info.call_args_list
        log_msg = ""
        for call in calls:
            if "LATEST TECHNICALS" in str(call):
                log_msg = str(call)
                break
        
        print(f"Log message capture: {log_msg}")
        if "N/A" in log_msg:
            print("Verified: Log output contains 'N/A' for missing indicators.")
        else:
            print("Warning: 'N/A' not found in log message.")
            
    except Exception as e:
        print(f"Failed! Caught exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_fix()
