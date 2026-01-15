import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="Supply Chain Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling (Glassmorphism & Premium UI) ---
st.markdown("""
<style>
    /* Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        color: #e0e0e0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(30, 30, 46, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Cards/Metrics */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.08);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    /* DataFrame Styling */
    div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1e1e2e;
    }
    ::-webkit-scrollbar-thumb {
        background: #5c5c7f;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #7a7a9f;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=5)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1rOCXlnzaxTv0-pPKHhgGuQ9MgvNCgcKq_UCrLK7B2Gs/export?format=csv"
    try:
        df = pd.read_csv(url)
        
        # Clean column names (remove extra spaces and colons)
        df.columns = df.columns.str.strip().str.replace(' :', '').str.replace(':', '')
        
        # Date conversion
        # First try converting with infer_datetime_format, if that fails or leaves object, specify format if known or coerce
        # The sample shows "15-Jan-2026", which pandas usually parses well
        df['Issue date'] = pd.to_datetime(df['Issue date'], errors='coerce')
        
        # Numeric conversion for key columns
        numeric_cols = ['Requisition Quantity', 'Issue Quantity', 'Pending Issue Quantity', 'Line Item Total', 'Item Rate']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Sidebar Filters ---
st.sidebar.title("🔍 Filters")

# Refresh Button
if st.sidebar.button("🔄 Refresh Data", help="Click to reload data from Google Sheets"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

df = load_data()

# --- Helpers ---
def format_currency(val):
    return f"₹{val:,.2f}"

if not df.empty:
    # 1. Date Filter (Monthly)
    df['Month_Year'] = df['Issue date'].dt.strftime('%b-%Y') # e.g., Jan-2026
    # Sort months chronologically
    df = df.sort_values('Issue date', ascending=False)
    available_months = df['Month_Year'].unique().tolist()
    
    selected_months = st.sidebar.multiselect(
        "Select Month(s)",
        options=available_months,
        default=available_months[:1] if available_months else None,
        help="Filter data by specific months"
    )

    # 2. Cost Center Filter
    cost_centers = sorted(df['Requesting Cost Center'].astype(str).unique().tolist())
    selected_cc = st.sidebar.multiselect(
        "Requesting Cost Center",
        options=cost_centers,
        placeholder="All Cost Centers"
    )

    # 3. Item Name Filter
    items = sorted(df['Item Name'].astype(str).unique().tolist())
    selected_items = st.sidebar.multiselect(
        "Item Name",
        options=items,
        placeholder="All Items"
    )
    
    # --- Filtering Logic ---
    filtered_df = df.copy()
    
    if selected_months:
        filtered_df = filtered_df[filtered_df['Month_Year'].isin(selected_months)]
    
    if selected_cc:
        filtered_df = filtered_df[filtered_df['Requesting Cost Center'].isin(selected_cc)]
        
    if selected_items:
        filtered_df = filtered_df[filtered_df['Item Name'].isin(selected_items)]

else:
    st.warning("No data loaded. Please check the source.")
    st.stop()

# --- Main Dashboard ---
st.title("📊 Supply Chain Analytics")
st.markdown(f"**Data Overview for:** {' | '.join(selected_months) if selected_months else 'All Time'}")

# --- KPIs ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_spend = filtered_df['Line Item Total'].sum()
total_issued_qty = filtered_df['Issue Quantity'].sum()
unique_items = filtered_df['Item Code'].nunique()
active_ccs = filtered_df['Requesting Cost Center'].nunique()

with kpi1:
    st.metric("Total Spend", format_currency(total_spend), delta_color="normal")
with kpi2:
    st.metric("Total Units Issued", f"{total_issued_qty:,.0f}")
with kpi3:
    st.metric("Unique Items", unique_items)
with kpi4:
    st.metric("Active Cost Centers", active_ccs)

st.markdown("---")

# --- Charts Section ---
c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.subheader("💰 Spend by Cost Center")
    if not filtered_df.empty:
        # Group by CC and sum Line Item Total
        cc_spend = filtered_df.groupby('Requesting Cost Center')['Line Item Total'].sum().reset_index()
        cc_spend = cc_spend.sort_values('Line Item Total', ascending=True).tail(10) # Top 10
        
        fig_cc = px.bar(
            cc_spend,
            x='Line Item Total',
            y='Requesting Cost Center',
            orientation='h',
            text_auto='.2s',
            color='Line Item Total',
            color_continuous_scale='Viridis'
        )
        fig_cc.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0',
            xaxis_title="Total Cost (₹)",
            yaxis_title=None,
            showlegend=False
        )
        st.plotly_chart(fig_cc, use_container_width=True)
    else:
        st.info("No data for charts")

with c2:
    st.subheader("📈 Top Items by Quantity")
    if not filtered_df.empty:
        item_qty = filtered_df.groupby('Item Name')['Issue Quantity'].sum().reset_index()
        item_qty = item_qty.sort_values('Issue Quantity', ascending=False).head(10)
        
        fig_item = px.pie(
            item_qty,
            values='Issue Quantity',
            names='Item Name',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Bluyl
        )
        fig_item.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#e0e0e0',
            showlegend=True,
            legend=dict(orientation="h", y=-0.1)
        )
        st.plotly_chart(fig_item, use_container_width=True)
    else:
        st.info("No data for charts")

# --- Detailed Data View ---
st.subheader("📋 Detailed Requisition Log")
with st.expander("View Full Data Table", expanded=True):
    # Select relevant columns to display
    display_cols = [
        'Issue date', 'Issue Number', 'Requesting Cost Center', 'Item Name', 
        'Category', 'UOM', 'Issue Quantity', 'Item Rate', 'Line Item Total', 'Issue Status'
    ]
    # Filter columns that actually exist in the dataframe
    valid_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[valid_cols].sort_values('Issue date', ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Issue date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            "Line Item Total": st.column_config.NumberColumn("Total Cost", format="₹%.2f"),
            "Item Rate": st.column_config.NumberColumn("Rate", format="₹%.2f"),
        }
    )

# --- Download Button ---
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download Filtered Data as CSV",
    data=csv,
    file_name='supply_chain_data.csv',
    mime='text/csv',
)
