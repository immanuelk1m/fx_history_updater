import unittest
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import functions from the script to be tested
# Assuming fx_updater.py is in the same directory or accessible via PYTHONPATH
from fx_updater import (
    calculate_moving_average,
    get_predictions,
    generate_json_output,
    fetch_fx_data # We will mock this one heavily, or calls within it
)

class TestFxUpdater(unittest.TestCase):

    # --- Tests for calculate_moving_average ---
    def test_sma_valid_data(self):
        self.assertEqual(calculate_moving_average([1, 2, 3, 4, 5], 3), [2.0, 3.0, 4.0])
        self.assertEqual(calculate_moving_average([10, 12, 11, 13, 15, 14, 16], 4), [11.5, 12.75, 13.25, 14.5])

    def test_sma_empty_data(self):
        self.assertEqual(calculate_moving_average([], 3), [])

    def test_sma_data_shorter_than_window(self):
        self.assertEqual(calculate_moving_average([1, 2], 3), [])

    def test_sma_window_one(self):
        # Window of 1 should return the original numbers as averages
        self.assertEqual(calculate_moving_average([1, 2, 3, 4, 5], 1), [1.0, 2.0, 3.0, 4.0, 5.0])

    def test_sma_window_zero_or_negative(self):
        # The current implementation of calculate_moving_average doesn't explicitly prevent window <= 0.
        # A robust implementation might raise ValueError or handle it.
        # Based on `range(len(data) - window + 1)`, a window of 0 would process more than intended.
        # A window < 0 would also lead to unexpected behavior.
        # For now, let's test the behavior. If the function is improved, this test might need adjustment.
        # Based on the current code, window=0 would lead to `len(data)+1` iterations.
        # And division by zero.
        with self.assertRaises(ZeroDivisionError): # Or whatever error it should raise
            calculate_moving_average([1, 2, 3], 0)
        # Negative window will likely result in a larger loop than data size, or empty if data is small.
        # If len(data) - window + 1 is negative, range is empty.
        self.assertEqual(calculate_moving_average([1, 2, 3], -1), [])

    # --- Utility to create mock Alpha Vantage API data ---
    def _create_mock_fx_data(self, num_points, start_price=1300, price_increment_short=1, price_increment_long=0.1, interval_minutes=10):
        """
        Generates mock time series data for Alpha Vantage API.
        Prices are generated to control MA crossovers.
        - For UP trend: recent prices increase faster.
        - For DOWN trend: recent prices decrease faster.
        - For NEUTRAL: prices are relatively stable or fluctuate minimally.
        """
        fx_data = {}
        current_time = datetime.now()
        for i in range(num_points):
            # Timestamps should be in reverse chronological order as typically returned by API
            timestamp = (current_time - datetime.timedelta(minutes=i * interval_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Simplified price generation for basic trend control
            # This is a simplistic model; real MA behavior depends on the entire series.
            # For UP: Make more recent prices higher
            # For DOWN: Make more recent prices lower
            # This needs to be carefully crafted. Let's assume for UP, short MA > medium MA > long MA.
            # This means the most recent prices (which are at the 'end' of the chronological list fed to SMA)
            # need to be higher than older prices.
            # price = start_price + (num_points - 1 - i) * price_increment_short + (num_points - 1 - i) * price_increment_long
            
            # Let's try a simpler approach: define a list of prices and then assign to timestamps.
            # Prices list should be in chronological order for this logic
            prices_chronological = []
            base = start_price
            for j in range(num_points):
                # This is a placeholder. Specific tests will override this with more controlled data.
                base += price_increment_short if j > num_points / 2 else price_increment_long
                prices_chronological.append(base)

            # API returns newest first, so we map prices in reverse from our chronological list
            price = prices_chronological[num_points - 1 - i]

            fx_data[timestamp] = {
                "1. open": str(price - 0.5),
                "2. high": str(price + 0.5),
                "3. low": str(price - 1.0),
                "4. close": str(price)
            }
        return {"Time Series FX (10min)": fx_data}

    # --- Tests for get_predictions ---
    @patch('fx_updater.fetch_fx_data')
    def test_get_predictions_short_up_long_up(self, mock_fetch):
        # We need at least 60 data points for long MA.
        # For short UP (5MA > 20MA) and long UP (20MA > 60MA):
        # Recent prices should be significantly higher than older prices.
        prices = [100 + i * 0.5 for i in range(50)] + [100 + 50*0.5 + i*2 for i in range(10)] # last 10 prices rise fast
        
        mock_data_points = {}
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        for i, price in enumerate(prices): # prices are chronological
            # API data is reverse chronological for timestamps
            ts = (start_time + datetime.timedelta(minutes=(len(prices)-1-i)*10)).strftime("%Y-%m-%d %H:%M:%S")
            mock_data_points[ts] = {"1. open": str(price), "2. high": str(price), "3. low": str(price), "4. close": str(price)}
        
        mock_fetch.return_value = {"Time Series FX (10min)": mock_data_points}

        latest_rate, short_pred, long_pred, ts = get_predictions("fake_api_key", "USD", "KRW")
        
        self.assertIsNotNone(latest_rate)
        self.assertEqual(short_pred, "UP")
        self.assertEqual(long_pred, "UP")
        self.assertEqual(latest_rate, prices[-1]) # Latest rate is the last in chronological list

    @patch('fx_updater.fetch_fx_data')
    def test_get_predictions_short_down_long_down(self, mock_fetch):
        # For short DOWN (5MA < 20MA) and long DOWN (20MA < 60MA):
        # Recent prices should be significantly lower than older prices.
        prices = [200 - i * 0.5 for i in range(50)] + [200 - 50*0.5 - i*2 for i in range(10)] # last 10 prices drop fast
        
        mock_data_points = {}
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        for i, price in enumerate(prices): # prices are chronological
            ts = (start_time + datetime.timedelta(minutes=(len(prices)-1-i)*10)).strftime("%Y-%m-%d %H:%M:%S")
            mock_data_points[ts] = {"1. open": str(price), "2. high": str(price), "3. low": str(price), "4. close": str(price)}

        mock_fetch.return_value = {"Time Series FX (10min)": mock_data_points}
        latest_rate, short_pred, long_pred, ts = get_predictions("fake_api_key", "USD", "KRW")

        self.assertIsNotNone(latest_rate)
        self.assertEqual(short_pred, "DOWN")
        self.assertEqual(long_pred, "DOWN")
        self.assertEqual(latest_rate, prices[-1])

    @patch('fx_updater.fetch_fx_data')
    def test_get_predictions_neutral(self, mock_fetch):
        # For NEUTRAL: MAs are close or equal. E.g., prices are very stable.
        prices = [150.0] * 60 # All prices are the same
        
        mock_data_points = {}
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        for i, price in enumerate(prices):
            ts = (start_time + datetime.timedelta(minutes=(len(prices)-1-i)*10)).strftime("%Y-%m-%d %H:%M:%S")
            mock_data_points[ts] = {"1. open": str(price), "2. high": str(price), "3. low": str(price), "4. close": str(price)}

        mock_fetch.return_value = {"Time Series FX (10min)": mock_data_points}
        latest_rate, short_pred, long_pred, ts = get_predictions("fake_api_key", "USD", "KRW")

        self.assertIsNotNone(latest_rate)
        self.assertEqual(short_pred, "NEUTRAL")
        self.assertEqual(long_pred, "NEUTRAL")
        self.assertEqual(latest_rate, prices[-1])

    @patch('fx_updater.fetch_fx_data')
    def test_get_predictions_api_failure(self, mock_fetch):
        mock_fetch.return_value = None # Simulate fetch_fx_data returning None on API error
        
        latest_rate, short_pred, long_pred, ts = get_predictions("fake_api_key", "USD", "KRW")
        
        self.assertIsNone(latest_rate)
        self.assertIsNone(short_pred) # As per current get_predictions logic for this case
        self.assertIsNone(long_pred)
        self.assertIsNone(ts)

    @patch('fx_updater.fetch_fx_data')
    def test_get_predictions_insufficient_data_for_ma(self, mock_fetch):
        # Return fewer than 60 data points (long_window)
        num_points = 50 # Less than long_window=60
        prices = [100 + i for i in range(num_points)]
        
        mock_data_points = {}
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        for i, price in enumerate(prices):
            ts = (start_time + datetime.timedelta(minutes=(len(prices)-1-i)*10)).strftime("%Y-%m-%d %H:%M:%S")
            mock_data_points[ts] = {"1. open": str(price), "2. high": str(price), "3. low": str(price), "4. close": str(price)}

        mock_fetch.return_value = {"Time Series FX (10min)": mock_data_points}
        latest_rate, short_pred, long_pred, ts = get_predictions("fake_api_key", "USD", "KRW")

        # latest_rate should still be available
        self.assertEqual(latest_rate, prices[-1])
        # Predictions should be NEUTRAL as not all MAs can be calculated
        self.assertEqual(short_pred, "NEUTRAL") # Short MA might be calculable, but long MA won't be
        self.assertEqual(long_pred, "NEUTRAL")
        self.assertIsNotNone(ts)

    # --- Tests for generate_json_output ---
    def test_generate_json_valid_input(self):
        timestamp_str = "2023-10-27 10:00:00"
        from_currency = "USD"
        to_currency = "JPY"
        latest_rate = 150.25
        short_term_prediction = "UP"
        long_term_prediction = "DOWN"

        expected_json = {
            "timestamp": timestamp_str,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": latest_rate,
            "predictions": {
                "short_term": short_term_prediction,
                "long_term": long_term_prediction
            }
        }
        # The function returns a dict, not a JSON string.
        # The main script does json.dumps()
        result_dict = generate_json_output(latest_rate, short_term_prediction, long_term_prediction, from_currency, to_currency, timestamp_str)
        self.assertEqual(result_dict, expected_json)

    def test_generate_json_with_none_values(self):
        timestamp_str = "2023-10-27 10:05:00"
        from_currency = "EUR"
        to_currency = "GBP"
        latest_rate = None # Simulate failure to get rate
        short_term_prediction = "NEUTRAL" # Default on some failures
        long_term_prediction = "NEUTRAL"

        expected_json = {
            "timestamp": timestamp_str,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": None,
            "predictions": {
                "short_term": "NEUTRAL",
                "long_term": "NEUTRAL"
            }
        }
        result_dict = generate_json_output(latest_rate, short_term_prediction, long_term_prediction, from_currency, to_currency, timestamp_str)
        self.assertEqual(result_dict, expected_json)


if __name__ == '__main__':
    unittest.main()
