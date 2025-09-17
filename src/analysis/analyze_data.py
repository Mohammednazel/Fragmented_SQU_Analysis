import pandas as pd
import os
from typing import List, Dict, Any
# You may need to install this library in your backend's virtual environment:
# pip install statsmodels
from statsmodels.tsa.api import SimpleExpSmoothing

# -------------------------------------------------------------------
# Data Loading and Preparation (Optimized for Fast Startup)
# -------------------------------------------------------------------
def load_master_data() -> pd.DataFrame:
    """
    Loads and prepares the master dataframe. This is the ONLY data loaded at startup.
    """
    current_dir = os.path.dirname(__file__)
    cleaned_data_path = os.path.join(current_dir, '..', '..', 'data', 'processed', 'cleaned_purchase_orders.csv')
    if not os.path.exists(cleaned_data_path):
        raise FileNotFoundError(f"Cleaned data not found at {cleaned_data_path}")
    
    df = pd.read_csv(cleaned_data_path)
    df['created_date'] = pd.to_datetime(df['created_date'])
    df['department'] = df['purchasing_group'] # Map column for dashboard compatibility
    df['month'] = df['created_date'].dt.strftime('%B') # Add month name
    return df

# -------------------------------------------------------------------
# On-Demand Calculation Functions
# -------------------------------------------------------------------

def calculate_kpis(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calculates KPIs from the raw data on demand."""
    total_spend = df['net_value'].sum()
    saving_potential_df = df.groupby('product_id')['unit_price'].min().reset_index(name='min_price')
    df_merged = pd.merge(df, saving_potential_df, on='product_id')
    saving_potential = ((df_merged['unit_price'] - df_merged['min_price']) * df_merged['quantity']).sum()
    supplier_counts = df.groupby('product_id')['supplier_id'].nunique()
    fragmented_skus = (supplier_counts > 1).sum()
    
    kpi_data = [
        {"KPI": "Total Spend", "Value": f"${total_spend:,.2f}"},
        {"KPI": "Potential Savings", "Value": f"${saving_potential:,.2f}"},
        {"KPI": "Total Purchase Orders", "Value": f"{df['purchase_order_id'].nunique():,}"},
        {"KPI": "Total Active Suppliers", "Value": f"{df['supplier_id'].nunique():,}"},
        {"KPI": "Fragmented SKUs", "Value": f"{fragmented_skus:,}"},
        {"KPI": "Fragmentation Rate (%)", "Value": f"{(fragmented_skus / df['product_id'].nunique() * 100):.2f}%"},
    ]
    return kpi_data

def calculate_sku_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Generates the detailed SKU analysis table on demand."""
    sku_analysis = df.groupby(['department', 'product_id', 'description', 'supplier_id']).agg(
        quantity_purchased=('quantity', 'sum'), 
        avg_price_paid=('unit_price', 'mean')
    ).reset_index()
    best_prices_per_sku = df.groupby('product_id')['unit_price'].min().reset_index(name='best_available_price')
    sku_analysis = pd.merge(sku_analysis, best_prices_per_sku, on='product_id')
    sku_analysis['cost_above_best_price'] = (sku_analysis['avg_price_paid'] - sku_analysis['best_available_price']) * sku_analysis['quantity_purchased']
    return sku_analysis

def filter_sku_analysis(df: pd.DataFrame, departments: List[str], suppliers: List[str], cost_threshold: float) -> pd.DataFrame:
    """Applies filters to the detailed SKU analysis dataframe."""
    if not departments and not suppliers and cost_threshold == 0:
        return df

    filtered_df = df.copy()
    if departments:
        filtered_df = filtered_df[filtered_df['department'].isin(departments)]
    if suppliers:
        filtered_df = filtered_df[filtered_df['supplier_id'].isin(suppliers)]
    
    filtered_df = filtered_df[filtered_df['cost_above_best_price'] >= cost_threshold]
    return filtered_df

# --- NEW FUNCTIONS FOR RISK & FORECASTING ---

def calculate_critical_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    """Identifies high-value, single-sourced SKUs that pose a supply chain risk."""
    sku_summary = df.groupby(['product_id', 'description']).agg(
        total_net_value=('net_value', 'sum'),
        supplier_count=('supplier_id', 'nunique')
    ).reset_index().sort_values('total_net_value', ascending=False)
    
    sku_summary['cum_spend_pct'] = (sku_summary['total_net_value'].cumsum() / sku_summary['total_net_value'].sum()) * 100
    
    top_spend_skus = sku_summary[sku_summary['cum_spend_pct'] <= 80]['product_id']
    single_sourced_mask = sku_summary['product_id'].isin(top_spend_skus) & (sku_summary['supplier_count'] == 1)
    critical_single_sourced_skus = sku_summary[single_sourced_mask]

    supplier_info = df[['product_id', 'supplier_id']].drop_duplicates()
    critical_risk_suppliers = pd.merge(critical_single_sourced_skus, supplier_info, on='product_id')
    
    return critical_risk_suppliers[['product_id', 'description', 'supplier_id', 'total_net_value']].sort_values('total_net_value', ascending=False)

def calculate_price_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates price volatility using the Coefficient of Variation (CV)."""
    price_volatility = df.groupby(['product_id', 'description'])['unit_price'].agg(['mean', 'std']).reset_index()
    price_volatility['CV_%'] = (price_volatility['std'] / price_volatility['mean']) * 100
    return price_volatility.sort_values('CV_%', ascending=False).fillna(0)

def calculate_demand_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Generates a 3-month demand forecast for the top 5 SKUs by quantity."""
    top_5_skus_by_qty = df.groupby('product_id')['quantity'].sum().nlargest(5).index.tolist()
    
    monthly_demand = df[df['product_id'].isin(top_5_skus_by_qty)].copy()
    monthly_demand_ts = monthly_demand.groupby(['product_id', pd.Grouper(key='created_date', freq='M')])['quantity'].sum().reset_index()
    
    all_forecasts = []
    for sku in top_5_skus_by_qty:
        sku_history = monthly_demand_ts[monthly_demand_ts['product_id'] == sku].set_index('created_date')['quantity']
        
        if len(sku_history) > 2:
            model = SimpleExpSmoothing(sku_history, initialization_method="estimated").fit()
            forecast = model.forecast(3).rename(f"{sku}_forecast").reset_index()
            forecast.columns = ['Forecast_Date', 'Forecast_Quantity']
            forecast['product_id'] = sku
            all_forecasts.append(forecast)
            
    if all_forecasts:
        demand_forecast_df = pd.concat(all_forecasts)
        return demand_forecast_df[['product_id', 'Forecast_Date', 'Forecast_Quantity']]
    
    return pd.DataFrame() # Return empty dataframe if no forecasts could be made
