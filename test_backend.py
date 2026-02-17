from backend import ForexAnalyzer

def test_backend():
    analyzer = ForexAnalyzer()
    
    # Test Data Fetching
    print("Fetching data for EURUSD...")
    df, error = analyzer.fetch_data("EURUSD", "1mo", "1d")
    
    if error:
        print(f"Error fetching data: {error}")
        return

    print("Data fetched successfully.")
    print(df.tail(5))

    # Test Indicators
    print("\nCalculating indicators...")
    df = analyzer.calculate_indicators(df)
    print(df[['Close', 'EMA_50', 'EMA_200', 'RSI', 'ATR']].tail(5))
    
    # Test Prompt Generation
    print("\nGenerating prompt...")
    prompt = analyzer.generate_prompt(df, "Fed rates staying high", "EURUSD")
    print(prompt)

if __name__ == "__main__":
    test_backend()
