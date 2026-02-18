import pandas as pd
import pandas_ta as ta

def reproduce():
    # Only 2 rows of data
    data = {
        'High': [1.1, 1.2],
        'Low': [1.0, 1.1],
        'Close': [1.05, 1.15]
    }
    df = pd.DataFrame(data)

    print("Calculating EMA 200 with 2 rows...")
    ema = ta.ema(df['Close'], length=200)
    print(f"Type of result: {type(ema)}")
    print(f"Result: {ema}")

    if ema is None:
        print("Confirmed: pandas_ta returns None for insufficient data in some cases.")
        try:
            print(f"Trying to format None: {ema:.2f}")
        except Exception as e:
            print(f"Caught expected error: {e}")
    else:
        # Check if any element is None/NaN
        val = ema.iloc[-1]
        print(f"Latest value type: {type(val)}")
        print(f"Latest value: {val}")
        try:
             print(f"Formatting latest value: {val:.2f}")
        except Exception as e:
            print(f"Caught error while formatting value: {e}")

if __name__ == "__main__":
    reproduce()
