# src/data_extraction/fetch_data.py

import requests
import json
import os

def fetch_and_save_data():
    """
    Fetches purchase order data from the API and saves it as a raw JSON file.
    """
    URL = "https://procurement-sku-analysis-mock.onrender.com/purchase-orders"

    # This creates a robust path to the target file
    # It goes up two directories from fetch_data.py (to src/ then to root) and then down to data/raw/
    current_dir = os.path.dirname(__file__)
    RAW_DATA_PATH = os.path.join(current_dir, '..', '..', 'data', 'raw', 'purchase_orders.json')

    print(f"Fetching data from {URL}...")

    try:
        response = requests.get(URL)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        data = response.json()

        # Ensure the target directory exists
        os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)

        # Save the raw data to a JSON file
        with open(RAW_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print(f"Success! Raw data saved to: {RAW_DATA_PATH}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

if __name__ == '__main__':
    fetch_and_save_data()