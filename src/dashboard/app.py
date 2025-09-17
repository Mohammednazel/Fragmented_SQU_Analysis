import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# -------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Procurement Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------------
# API Configuration
# -------------------------------------------------------------------
# This should point to your running FastAPI server
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# -------------------------------------------------------------------
# Custom Styling (CSS)
# -------------------------------------------------------------------
st.markdown("""
<style>
    /* Main app background */
    .main {
        background-color: #F0F2F6;
    }
    /* KPI Metric styling */
    div[data-testid="stMetric"],
    div[data-testid="stMetric"] > div[data-testid="stMetricValue"],
    div[data-testid="stMetric"] > div[data-testid="stMetricLabel"] {
        width: 100%;
    }
    div.metric-container { /* Applied a class for better targeting */
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        padding: 2% 5% 2% 5%;
        border-radius: 10px;
        color: rgb(30, 103, 119);
        overflow-wrap: break-word;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    }
    /* Center align metric values */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {
        text-align: center;
    }
    /* Styling for headers */
    h1, h2, h3 {
        color: #0A2E36;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------------
# Data Fetching from API (Replaces Excel Loading)
# -------------------------------------------------------------------
@st.cache_data(ttl=300) # Cache API responses for 5 minutes
def fetch_api_data(endpoint: str, params: dict = None):
    """Fetches data from a specific API endpoint and handles errors."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error at endpoint '{endpoint}': {e}. Is the FastAPI server running?")
        return None

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
def format_kpi_value(value_str):
    """Removes formatting for calculations and returns clean string."""
    if isinstance(value_str, str):
        return value_str.replace('$', '').replace(',', '').replace('%', '').strip()
    return value_str

@st.cache_data
def convert_df_to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')


# -------------------------------------------------------------------
# UI Rendering Functions (Modular Structure)
# -------------------------------------------------------------------

def display_kpi_overview():
    """Displays the main KPIs by fetching and transforming data from the /kpis endpoint."""
    st.header("Executive Performance Overview")
    kpi_list = fetch_api_data("kpis")

    if kpi_list:
        # --- THIS IS THE CORRECTED LOGIC ---
        # The API returns a list of dicts. We convert it into a single dict for easy access.
        # From: [{"KPI": "Total Spend", "Value": "..."}]
        # To:   {"Total Spend": "..."}
        kpi_dict = {item['KPI']: item['Value'] for item in kpi_list}

        # Now we can safely use .get() on our new kpi_dict
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            value = float(format_kpi_value(kpi_dict.get("Total Spend", 0)))
            st.metric(label="Total Spend", value=f"${value:,.2f}")
        with col2:
            value = float(format_kpi_value(kpi_dict.get("Potential Savings", 0)))
            st.metric(label="Potential Savings", value=f"${value:,.2f}")
        with col3:
            value = int(float(format_kpi_value(kpi_dict.get("Total Purchase Orders", 0))))
            st.metric(label="Total POs", value=f"{value:,}")
        with col4:
            value = int(float(format_kpi_value(kpi_dict.get("Total Active Suppliers", 0))))
            st.metric(label="Active Suppliers", value=f"{value:,}")
        with col5:
            value = int(float(format_kpi_value(kpi_dict.get("Fragmented SKUs", 0))))
            st.metric(label="Fragmented SKUs", value=f"{value:,}")
        with col6:
            value = float(format_kpi_value(kpi_dict.get("Fragmentation Rate (%)", "0")))
            st.metric(label="Fragmentation Rate", value=f"{value:.2f}%")


def display_spend_analysis():
    """Displays charts from Section B by fetching data from multiple chart endpoints."""
    st.header("Deep Dive: Spend Analysis")

    # Fetch data for each chart from the API
    trend_data = fetch_api_data("charts/spend-trend")
    dept_data = fetch_api_data("charts/department-spend")
    plant_data = fetch_api_data("charts/plant-spend")
    material_data = fetch_api_data("charts/material-spend")
    top_skus_data = fetch_api_data("tables/top-skus")

    # Spend Trend Chart
    if trend_data:
        df_trend = pd.DataFrame(trend_data)
        st.subheader("Monthly Spend Trend")
        fig_trend = px.line(df_trend, x='month', y='net_value', markers=True, labels={'month': 'Month', 'net_value': 'Total Spend'}, title="Total Procurement Spend Over Time")
        st.plotly_chart(fig_trend, use_container_width=True)

    # Bar charts for spend breakdown
    col1, col2 = st.columns(2)
    with col1:
        if dept_data:
            df_dept = pd.DataFrame(dept_data)
            st.subheader("Spend by Department")
            fig_dept = px.bar(df_dept, x='department', y='net_value', title="Total Spend per Department", labels={'department': 'Department', 'net_value': 'Total Spend'}, color='department')
            st.plotly_chart(fig_dept, use_container_width=True)
        if material_data:
            df_material = pd.DataFrame(material_data)
            st.subheader("Spend by Material Group")
            fig_material = px.bar(df_material, x='material_group', y='net_value', title="Total Spend per Material Group", labels={'material_group': 'Material Group', 'net_value': 'Total Spend'}, color='material_group')
            st.plotly_chart(fig_material, use_container_width=True)
    with col2:
        if plant_data:
            df_plant = pd.DataFrame(plant_data)
            st.subheader("Spend by Plant")
            fig_plant = px.bar(df_plant, x='plant', y='net_value', title="Total Spend per Plant", labels={'plant': 'Plant', 'net_value': 'Total Spend'}, color='plant')
            st.plotly_chart(fig_plant, use_container_width=True)
        if top_skus_data:
            df_top_skus = pd.DataFrame(top_skus_data)
            st.subheader("Top 10 SKUs by Spend")
            st.dataframe(df_top_skus.style.format({'net_value': "${:,.2f}"}))


def display_recommendations():
    """Displays recommendations from Section C by fetching from API endpoints."""
    st.header("Actionable Insights: Savings & Recommendations")

    rec_data = fetch_api_data("recommendations")
    contract_data = fetch_api_data("tables/contract-candidates")

    if rec_data:
        df_rec = pd.DataFrame(rec_data)
        st.subheader("Top Supplier Consolidation Recommendations")
        st.info("These SKUs offer the highest potential savings if consolidated to the recommended supplier who offers the best price.")
        st.download_button(label="📥 Download Recommendations as CSV", data=convert_df_to_csv(df_rec), file_name='procurement_recommendations.csv', mime='text/csv')
        st.dataframe(df_rec.style.format({'Best Price': "${:,.2f}", 'avg_unit_price': "${:,.2f}", 'Estimated Saving': "${:,.2f}"}))

    if contract_data:
        df_contract = pd.DataFrame(contract_data)
        with st.expander("View Contract Candidates"):
            st.write("These are high-value, frequently purchased items that are ideal candidates for long-term contracts.")
            st.dataframe(df_contract.style.format({'total_net_value': "${:,.2f}"}))


def display_sku_analysis():
    """Displays the detailed, filterable SKU analysis table from Section D."""
    st.header("Granular Analysis: SKU Details")
    st.sidebar.header("Filter SKU Details")

    departments_options = fetch_api_data("filters/departments") or []
    suppliers_options = fetch_api_data("filters/suppliers") or []

    selected_depts = st.sidebar.multiselect("Select Department(s)", departments_options, default=[])
    selected_suppliers = st.sidebar.multiselect("Select Supplier(s)", suppliers_options, default=[])
    cost_threshold = st.sidebar.slider("Minimum 'Cost Above Best Price'", min_value=0, max_value=50000, value=0, step=1000)

    params = {
        "departments": selected_depts,
        "suppliers": selected_suppliers,
        "cost_threshold": cost_threshold
    }

    sku_analysis_data = fetch_api_data("tables/sku-analysis", params=params)

    if sku_analysis_data is not None:
        df_filtered = pd.DataFrame(sku_analysis_data)
        st.write(f"Displaying {len(df_filtered)} records based on your filters.")
        st.dataframe(df_filtered.style.format({
            'avg_price_paid': "${:,.2f}", 'best_available_price': "${:,.2f}",
            'cost_above_best_price': "${:,.2f}"
        }).background_gradient(cmap='Reds', subset=['cost_above_best_price']))


def display_risk_and_forecast():
    """Displays risk and forecast data from Sections E & F."""
    st.header("Forward-Looking: Risk & Forecasting")

    risk_data = fetch_api_data("risk/critical-suppliers")
    volatility_data = fetch_api_data("risk/price-volatility")
    forecast_data = fetch_api_data("forecasts/demand")
    raw_data_for_history = fetch_api_data("raw-data")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Supplier Concentration Risk")
        st.warning("These high-value SKUs are single-sourced, posing a potential supply chain risk.")
        if risk_data is not None:
            df_risk = pd.DataFrame(risk_data)
            if df_risk.empty:
                st.success("No critical single-source supplier risks found.")
            else:
                st.dataframe(df_risk.style.format({'total_net_value': "${:,.2f}"}))
    with col2:
        st.subheader("Product Price Volatility")
        st.info("Products with a high 'CV %' have unstable pricing.")
        if volatility_data is not None:
            df_volatility = pd.DataFrame(volatility_data)
            if df_volatility.empty:
                st.info("Price volatility data is not yet available.")
            else:
                st.dataframe(df_volatility.style.format({'CV_%': "{:.2f}%"}))

    st.divider()
    st.subheader("3-Month Demand Forecast (Placeholder)")

    if forecast_data is not None and not pd.DataFrame(forecast_data).empty:
        df_forecast = pd.DataFrame(forecast_data)
        df_raw = pd.DataFrame(raw_data_for_history)
        df_raw['created_date'] = pd.to_datetime(df_raw['created_date'])

        forecasted_skus = df_forecast['product_id'].unique()
        selected_sku = st.selectbox("Select a Product to Visualize Forecast", forecasted_skus)

        if selected_sku:
            history = df_raw[df_raw['product_id'] == selected_sku].groupby(pd.Grouper(key='created_date', freq='M'))['quantity'].sum().reset_index()
            forecast = df_forecast[df_forecast['product_id'] == selected_sku]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history['created_date'], y=history['quantity'], mode='lines+markers', name='Historical Demand'))
            fig.add_trace(go.Scatter(x=forecast['Forecast_Date'], y=forecast['Forecast_Quantity'], mode='lines+markers', name='Forecasted Demand', line=dict(dash='dash')))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Demand forecast data is not yet available.")


# -------------------------------------------------------------------
# Main Application Flow
# -------------------------------------------------------------------
def main():
    """Main function to run the Streamlit app."""
    st.title("📊 AI-Driven Procurement Analysis Dashboard")
    st.markdown("An interactive dashboard for analyzing procurement data, identifying savings, and managing supplier risk.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Executive Summary", "🔍 Spend Analysis", "💡 Recommendations", "🔬 SKU Analysis", "🔮 Risk & Forecast"
    ])

    with tab1:
        display_kpi_overview()
    with tab2:
        display_spend_analysis()
    with tab3:
        display_recommendations()
    with tab4:
        display_sku_analysis()
    with tab5:
        display_risk_and_forecast()


if __name__ == "__main__":
    main()
