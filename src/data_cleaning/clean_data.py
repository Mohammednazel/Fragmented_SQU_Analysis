# src/data_cleaning/clean_data.py

import pandas as pd
import json
import os

def clean_and_process_data():
    """
    Loads raw purchase order data, flattens the nested items,
    cleans it, and saves the result as a CSV file.
    """
    # --- 1. DEFINE FILE PATHS ---
    current_dir = os.path.dirname(__file__)
    RAW_DATA_PATH = os.path.join(current_dir, '..', '..', 'data', 'raw', 'purchase_orders.json')
    PROCESSED_DATA_PATH = os.path.join(current_dir, '..', '..', 'data', 'processed', 'cleaned_purchase_orders.csv')

    print(f"Reading raw data from {RAW_DATA_PATH}...")
    
    # --- 2. LOAD RAW DATA ---
    try:
        with open(RAW_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Raw data file not found at {RAW_DATA_PATH}")
        print("Please run the data extraction script first: python src/data_extraction/fetch_data.py")
        return

    # --- 3. FLATTEN NESTED DATA ---
    flattened_data = []

    # ▼▼▼ THIS IS THE CORRECTED LOGIC ▼▼▼
    # First, extract the list of orders. It's the first (and likely only) value in the top-level dictionary.
    list_of_orders = list(data.values())[0]

    # Now, loop through the extracted list
    for order in list_of_orders:
        # Get context from the parent purchase order
        order_context = {
            'purchase_order_id': order.get('purchase_order_id'),
            'created_date': order.get('created_date'),
            'status': order.get('status'),
            'supplier_id': order.get('supplier_id'),
            'plant': order.get('plant'),
            'purchasing_group': order.get('purchasing_group'),
        }
        
        # Iterate through each item in the nested 'items' list
        for item in order.get('items', []):
            record = order_context.copy()
            record.update({
                'product_id': item.get('product_id'),
                'description': item.get('description'),
                'quantity': item.get('quantity'),
                'unit': item.get('unit'),
                'unit_price': item.get('unit_price'),
                'net_value': item.get('net_value'),
                'material_group': item.get('material_group'),
            })
            flattened_data.append(record)

    # --- 4. CREATE AND CLEAN PANDAS DATAFRAME ---
    df = pd.DataFrame(flattened_data)
    print("Data flattened. Now cleaning and transforming...")

    # Convert date column and extract month
    df['created_date'] = pd.to_datetime(df['created_date'])
    df['month'] = df['created_date'].dt.to_period('M').astype(str)

    # Convert numeric columns
    numeric_cols = ['quantity', 'unit_price', 'net_value']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- 5. SELECT AND REORDER FINAL COLUMNS ---
    required_cols = [
        'purchasing_group', 'plant', 'material_group', 'description', 'supplier_id',
        'product_id', 'quantity', 'unit_price', 'net_value', 'month', 'unit', 
        'purchase_order_id', 'created_date', 'status'
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    final_df = df[required_cols]

    # --- 6. SAVE PROCESSED DATA ---
    os.makedirs(os.path.dirname(PROCESSED_DATA_PATH), exist_ok=True)
    final_df.to_csv(PROCESSED_DATA_PATH, index=False)
    
    print(f"Success! Cleaned data saved to: {PROCESSED_DATA_PATH}")
    print(f"Cleaned DataFrame has {final_df.shape[0]} rows and {final_df.shape[1]} columns.")

if __name__ == '__main__':
    clean_and_process_data()