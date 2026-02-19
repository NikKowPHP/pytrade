import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.seasonality_service import SeasonalityService

def test_seasonality():
    service = SeasonalityService()
    
    print("--- TEST 1: AUDUSD in September (Bearish) ---")
    # Mock date: September 15th, 2026 (Tuesday)
    mock_date = datetime(2026, 9, 15) 
    report = service.get_seasonality_report("AUDUSD", date=mock_date)
    print(report['report_text'])
    print(f"Modifier: {report['modifier']}")
    print(f"Instruction: {report['instruction']}")
    
    assert "Bearish" in report['report_text']
    assert report['modifier'] == -10
    assert "Turnaround Tuesday" in report['report_text']
    print("PASS\n")

    print("--- TEST 2: SPY in October (Bullish) ---")
    mock_date = datetime(2026, 10, 10)
    report = service.get_seasonality_report("SPY", date=mock_date)
    print(report['report_text'])
    print(f"Modifier: {report['modifier']}")
    
    assert "Bullish" in report['report_text']
    assert report['modifier'] == -10 # Note: code sets -10 for Bullish too (Reduce SELL confidence)
    print("PASS\n")

    print("--- TEST 3: Neutral Month ---")
    mock_date = datetime(2026, 3, 15)
    report = service.get_seasonality_report("EURUSD", date=mock_date)
    print(report['report_text'])
    
    assert "Neutral" in report['report_text']
    print("PASS\n")
    
    print("--- TEST 4: Friday Logic ---")
    mock_date = datetime(2026, 2, 20) # A Friday
    report = service.get_seasonality_report("GBPUSD", date=mock_date)
    print(report['report_text'])
    
    assert "Friday" in report['report_text']
    assert "Gap Risk" in report['report_text']
    assert report['modifier'] == -5
    print("PASS\n")

if __name__ == "__main__":
    test_seasonality()
