import requests
import json
import os
from datetime import datetime

# --- Configuration ---
# Placeholder for API key. In a real application, use environment variables or a config file.
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'YOUR_API_KEY')
FROM_CURRENCY = 'USD'
TO_CURRENCY = 'KRW'

# Alpha Vantage API endpoint
ALPHA_VANTAGE_URL = 'https://www.alphavantage.co/query'

def fetch_fx_data(api_key, from_currency, to_currency, interval='10min', outputsize='compact'):
    """
    Fetches intraday FX data from Alpha Vantage.
    """
    params = {
        'function': 'FX_INTRADAY',
        'from_symbol': from_currency,
        'to_symbol': to_currency,
        'interval': interval,
        'outputsize': outputsize,
        'apikey': api_key,
    }
    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        if "Error Message" in data:
            print(f"Alpha Vantage API Error: {data['Error Message']}")
            return None
        # Example: {'Meta Data': {...}, 'Time Series FX (10min)': {'2023-10-27 13:40:00': {...}, ...}}
        # The actual key for time series data can vary based on the interval
        time_series_key = f"Time Series FX ({interval})"
        if time_series_key not in data:
            print(f"Unexpected API response format: Missing '{time_series_key}' key.")
            print(f"Full response: {data}")
            return None
        return data[time_series_key]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Alpha Vantage: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Alpha Vantage.")
        return None

def calculate_moving_average(data, window):
    """
    Calculates the moving average for a list of prices.
    """
    if len(data) < window:
        return []
    moving_averages = []
    for i in range(len(data) - window + 1):
        window_slice = data[i : i + window]
        window_average = sum(window_slice) / window
        moving_averages.append(window_average)
    return moving_averages

def get_predictions(api_key, from_currency, to_currency):
    """
    Fetches data, calculates MAs, and generates predictions.
    """
    # Fetch data with 'compact' to get 100 data points, '10min' interval for MAs
    raw_data = fetch_fx_data(api_key, from_currency, to_currency, interval='10min', outputsize='compact')

    if not raw_data:
        print("Failed to fetch data for predictions.")
        return None, None, None, None

    # Extract closing prices and timestamps. Data is usually newest first.
    # We need to reverse it for MA calculation if the MA function expects chronological order.
    timestamps = sorted(raw_data.keys()) # Sort to ensure chronological order
    
    if not timestamps:
        print("No timestamps found in the fetched data.")
        return None, None, None, None

    closing_prices = []
    for ts in timestamps:
        try:
            closing_prices.append(float(raw_data[ts]['4. close']))
        except KeyError:
            print(f"Could not find '4. close' for timestamp {ts}. Skipping this data point.")
            continue
        except ValueError:
            print(f"Could not convert closing price to float for timestamp {ts}. Skipping this data point.")
            continue
    
    if not closing_prices:
        print("No valid closing prices could be extracted.")
        return None, None, None, None

    latest_rate = closing_prices[-1] # The last price in the chronological list is the latest
    latest_timestamp = timestamps[-1]

    # Define MA periods
    short_window = 5
    medium_window = 20
    long_window = 60

    # Calculate MAs
    # The calculate_moving_average function expects data to be in chronological order,
    # and it returns MAs where the last element corresponds to the most recent period.
    
    # For a list of prices P = [p1, p2, ..., pN] (chronological)
    # MA_short = calculate_moving_average(P, short_window) -> [sma_s1, sma_s2, ..., sma_s_latest]
    # MA_medium = calculate_moving_average(P, medium_window) -> [sma_m1, sma_m2, ..., sma_m_latest]
    # MA_long = calculate_moving_average(P, long_window) -> [sma_l1, sma_l2, ..., sma_l_latest]

    ma_short_series = calculate_moving_average(closing_prices, short_window)
    ma_medium_series = calculate_moving_average(closing_prices, medium_window)
    ma_long_series = calculate_moving_average(closing_prices, long_window)

    if not ma_short_series or not ma_medium_series or not ma_long_series:
        print("Not enough data to calculate all moving averages.")
        # Still return latest rate if available, but predictions will be NEUTRAL
        return latest_rate, "NEUTRAL", "NEUTRAL", latest_timestamp

    # Get the latest MAs
    latest_ma_short = ma_short_series[-1]
    latest_ma_medium = ma_medium_series[-1]
    latest_ma_long = ma_long_series[-1]

    # Short-term prediction
    short_term_prediction = "NEUTRAL"
    if latest_ma_short > latest_ma_medium:
        short_term_prediction = "UP"
    elif latest_ma_short < latest_ma_medium:
        short_term_prediction = "DOWN"

    # Long-term prediction
    long_term_prediction = "NEUTRAL"
    if latest_ma_medium > latest_ma_long:
        long_term_prediction = "UP"
    elif latest_ma_medium < latest_ma_long:
        long_term_prediction = "DOWN"

    return latest_rate, short_term_prediction, long_term_prediction, latest_timestamp

def generate_json_output(latest_rate, short_term_prediction, long_term_prediction, from_currency, to_currency, timestamp_str):
    """
    Generates a JSON object with the FX data and predictions.
    """
    output = {
        "timestamp": timestamp_str,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": latest_rate,
        "predictions": {
            "short_term": short_term_prediction,
            "long_term": long_term_prediction
        }
    }
    return output

if __name__ == "__main__":
    # --- Configuration (using hardcoded values as per instruction, ideally use env vars) ---
    API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'YOUR_API_KEY_REPLACE_ME') # Replace with your actual key or set env var
    FROM_CURRENCY = 'USD'
    TO_CURRENCY = 'KRW'

    print(f"Attempting to fetch FX data for {FROM_CURRENCY} to {TO_CURRENCY}...")
    latest_rate, short_term_pred, long_term_pred, latest_timestamp = get_predictions(API_KEY, FROM_CURRENCY, TO_CURRENCY)

    output_data = {}
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if latest_rate is not None and latest_timestamp is not None:
        # Ensure timestamp from API is used if available, otherwise use current time for error.
        # Alpha Vantage timestamps might not have seconds, adjust format if needed.
        # Assuming latest_timestamp is in "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD HH:MM"
        try:
            # Attempt to parse and reformat if it includes seconds
            parsed_timestamp = datetime.strptime(latest_timestamp, "%Y-%m-%d %H:%M:%S")
            timestamp_str_for_json = parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            # If it's "YYYY-MM-DD HH:MM", add ":00" for seconds
            try:
                parsed_timestamp = datetime.strptime(latest_timestamp, "%Y-%m-%d %H:%M")
                timestamp_str_for_json = parsed_timestamp.strftime("%Y-%m-%d %H:%M:00")
            except ValueError:
                print(f"Warning: Could not parse API timestamp '{latest_timestamp}'. Using current time for output.")
                timestamp_str_for_json = current_time_str
        
        output_data = generate_json_output(latest_rate, short_term_pred, long_term_pred, FROM_CURRENCY, TO_CURRENCY, timestamp_str_for_json)
        print("Successfully fetched and processed FX data.")
    else:
        print("Failed to fetch or process FX data. Generating error output.")
        output_data = {
            "timestamp": current_time_str,
            "from_currency": FROM_CURRENCY,
            "to_currency": TO_CURRENCY,
            "rate": None,
            "predictions": {
                "short_term": "NEUTRAL",
                "long_term": "NEUTRAL"
            },
            "error": "Failed to retrieve or process FX data from Alpha Vantage. Check API key, network, or symbol validity."
        }

    # Print JSON to standard output
    print("\n--- FX Data JSON Output ---")
    print(json.dumps(output_data, indent=4))

    # Write JSON to file
    output_filename = 'fx_data.json'
    try:
        with open(output_filename, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"\nSuccessfully wrote FX data to {output_filename}")
    except IOError as e:
        print(f"\nError writing FX data to {output_filename}: {e}")
