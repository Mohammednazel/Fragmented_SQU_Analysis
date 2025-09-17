from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import pandas as pd
import numpy as np
from src.analysis.analyze_data import (
    load_master_data, 
    calculate_kpis,
    calculate_sku_analysis,
    filter_sku_analysis,
    # --- Import the new functions ---
    calculate_critical_suppliers,
    calculate_price_volatility,
    calculate_demand_forecast
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Procurement Dashboard API"]
)

# --- Load only the master data into memory at startup ---
try:
    MASTER_DF = load_master_data()
except FileNotFoundError as e:
    raise RuntimeError(f"Could not start API: {e}")

# --- Helper Function ---
def to_json_safe_dict(df: pd.DataFrame):
    """Converts dataframe to dict, replacing NaN/NaT with None for JSON compatibility."""
    return df.replace({np.nan: None, pd.NaT: None}).to_dict(orient='records')

# --- API Endpoints ---

@router.get("/kpis")
async def get_kpis():
    """Endpoint for Section A: Calculates KPIs on request."""
    kpi_data = calculate_kpis(MASTER_DF)
    return kpi_data

@router.get("/charts/spend-trend")
async def get_spend_trend():
    """Endpoint for Section B: Calculates Monthly Spend Trend chart."""
    spend_trend = MASTER_DF.groupby(MASTER_DF['created_date'].dt.to_period('M')).agg(net_value=('net_value', 'sum')).reset_index()
    spend_trend['month'] = spend_trend['created_date'].dt.strftime('%Y-%m')
    return to_json_safe_dict(spend_trend)

@router.get("/charts/department-spend")
async def get_department_spend():
    """Endpoint for Section B: Calculates Spend by Department chart."""
    dept_spend = MASTER_DF.groupby('department')['net_value'].sum().reset_index()
    return to_json_safe_dict(dept_spend)

@router.get("/charts/plant-spend")
async def get_plant_spend():
    """Endpoint for Section B: Calculates Spend by Plant chart."""
    plant_spend = MASTER_DF.groupby('plant')['net_value'].sum().reset_index()
    return to_json_safe_dict(plant_spend)

@router.get("/charts/material-spend")
async def get_material_spend():
    """Endpoint for Section B: Calculates Spend by Material Group chart."""
    material_spend = MASTER_DF.groupby('material_group')['net_value'].sum().reset_index()
    return to_json_safe_dict(material_spend)

@router.get("/tables/top-skus")
async def get_top_skus():
    """Endpoint for Section B: Calculates Top 10 SKUs table."""
    top_skus = MASTER_DF.groupby(['product_id', 'description'])['net_value'].sum().nlargest(10).reset_index()
    return to_json_safe_dict(top_skus)

@router.get("/recommendations")
async def get_recommendations():
    """Endpoint for Section C: Calculates Savings Recommendations table."""
    best_suppliers = MASTER_DF.loc[MASTER_DF.groupby('product_id')['unit_price'].idxmin()][['product_id', 'supplier_id', 'unit_price']].rename(columns={'supplier_id': 'Recommended Supplier', 'unit_price': 'Best Price'})
    avg_prices = MASTER_DF.groupby('product_id').agg(avg_unit_price=('unit_price', 'mean'), total_quantity=('quantity', 'sum')).reset_index()
    recommendations = pd.merge(best_suppliers, avg_prices, on='product_id')
    recommendations['Estimated Saving'] = (recommendations['avg_unit_price'] - recommendations['Best Price']) * recommendations['total_quantity']
    return to_json_safe_dict(recommendations.sort_values('Estimated Saving', ascending=False).head(10))

@router.get("/tables/contract-candidates")
async def get_contract_candidates():
    """Endpoint for Section C: Contract Candidates table (Placeholder)."""
    # This logic can be implemented based on the analysis script if needed
    return [] 

@router.get("/tables/sku-analysis")
async def get_sku_analysis_table(
    departments: Optional[List[str]] = Query(None, alias="departments"),
    suppliers: Optional[List[str]] = Query(None, alias="suppliers"),
    cost_threshold: int = Query(0)
):
    """Endpoint for Section D: Calculates and filters SKU Analysis table."""
    sku_analysis_df = calculate_sku_analysis(MASTER_DF)
    filtered_df = filter_sku_analysis(sku_analysis_df, departments, suppliers, cost_threshold)
    return to_json_safe_dict(filtered_df)

# --- UPDATED RISK & FORECAST ENDPOINTS ---

@router.get("/risk/critical-suppliers")
async def get_critical_suppliers():
    """Endpoint for Section E: Calculates critical single-source supplier risk."""
    critical_suppliers_df = calculate_critical_suppliers(MASTER_DF)
    return to_json_safe_dict(critical_suppliers_df)

@router.get("/risk/price-volatility")
async def get_price_volatility():
    """Endpoint for Section E: Calculates product price volatility."""
    price_volatility_df = calculate_price_volatility(MASTER_DF)
    return to_json_safe_dict(price_volatility_df)
    
@router.get("/forecasts/demand")
async def get_demand_forecast():
    """Endpoint for Section F: Generates a 3-month demand forecast."""
    forecast_df = calculate_demand_forecast(MASTER_DF)
    return to_json_safe_dict(forecast_df)

@router.get("/raw-data")
async def get_raw_data():
    """Endpoint to provide raw data for historical forecast charts."""
    return to_json_safe_dict(MASTER_DF[['product_id', 'created_date', 'quantity']])

# --- Filter Option Endpoints ---
@router.get("/filters/departments")
async def get_department_filters():
    """Provides unique department names for filter dropdowns."""
    return MASTER_DF['department'].unique().tolist()

@router.get("/filters/suppliers")
async def get_supplier_filters():
    """Provides unique supplier IDs for filter dropdowns."""
    return MASTER_DF['supplier_id'].unique().tolist()
