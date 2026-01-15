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
    /* Compact UI & Hide Scrollbar */
    .stApp {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        color: #e0e0e0;
        overflow: hidden; /* Try to fit in one screen */
    }
    
    /* Hide Main Scrollbar */
    ::-webkit-scrollbar {
        display: none;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(30, 30, 46, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Compact Metrics */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px; /* Reduced padding */
        border-radius: 8px;
        backdrop-filter: blur(10px);
    }
    
    /* Headers */
    h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.1rem !important; margin-top: 0px !important; }
    
    /* Reduce whitespace */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=5)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1rOCXlnzaxTv0-pPKHhgGuQ9MgvNCgcKq_UCrLK7B2Gs/export?format=csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip().str.replace(' :', '').str.replace(':', '')
        df['Issue date'] = pd.to_datetime(df['Issue date'], errors='coerce')
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
if st.sidebar.button("🔄 Refresh", help="Reload data"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")

df = load_data()

# --- Helpers ---
def format_currency(val):
    return f"₹{val:,.2f}"

if not df.empty:
    df['Month_Year'] = df['Issue date'].dt.strftime('%b-%Y')
    df = df.sort_values('Issue date', ascending=False)
    available_months = df['Month_Year'].unique().tolist()
    
    selected_months = st.sidebar.multiselect("Month", options=available_months, default=available_months[:1] if available_months else None)
    
    cost_centers = sorted(df['Requesting Cost Center'].astype(str).unique().tolist())
    selected_cc = st.sidebar.multiselect("Cost Center", options=cost_centers)

    items = sorted(df['Item Name'].astype(str).unique().tolist())
    selected_items = st.sidebar.multiselect("Item", options=items)
    
    # Filter
    filtered_df = df.copy()
    if selected_months: filtered_df = filtered_df[filtered_df['Month_Year'].isin(selected_months)]
    if selected_cc: filtered_df = filtered_df[filtered_df['Requesting Cost Center'].isin(selected_cc)]
    if selected_items: filtered_df = filtered_df[filtered_df['Item Name'].isin(selected_items)]

else:
    st.warning("No data.")
    st.stop()

# --- Main Dashboard ---
st.title("Supply Chain Analytics")
st.caption(f"Overview: {' | '.join(selected_months) if selected_months else 'All Time'}")

# --- KPIs ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: st.metric("Total Spend", format_currency(filtered_df['Line Item Total'].sum()))
with kpi2: st.metric("Units Issued", f"{filtered_df['Issue Quantity'].sum():,.0f}")
with kpi3: st.metric("Unique Items", filtered_df['Item Code'].nunique())
with kpi4: st.metric("Cost Centers", filtered_df['Requesting Cost Center'].nunique())

st.markdown("---")

# --- Charts (Compact) ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("💰 Spend by Cost Center")
    if not filtered_df.empty:
        cc_spend = filtered_df.groupby('Requesting Cost Center')['Line Item Total'].sum().reset_index().sort_values('Line Item Total', ascending=True).tail(8)
        fig_cc = px.bar(cc_spend, x='Line Item Total', y='Requesting Cost Center', orientation='h', text_auto='.2s', color='Line Item Total', color_continuous_scale='Viridis')
        fig_cc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', xaxis_title=None, yaxis_title=None, showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=300)
        st.plotly_chart(fig_cc, use_container_width=True)

with c2:
    st.subheader("📈 Top Items")
    if not filtered_df.empty:
        item_qty = filtered_df.groupby('Item Name')['Issue Quantity'].sum().reset_index().sort_values('Issue Quantity', ascending=False).head(8)
        fig_item = px.pie(item_qty, values='Issue Quantity', names='Item Name', hole=0.5, color_discrete_sequence=px.colors.sequential.Bluyl)
        fig_item.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', showlegend=True, legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05), margin=dict(l=0, r=0, t=0, b=0), height=300)
        st.plotly_chart(fig_item, use_container_width=True)

# --- Data Table (Collapsed) ---
with st.expander("Show Data Log", expanded=False):
    st.dataframe(
        filtered_df[['Issue date', 'Requesting Cost Center', 'Item Name', 'Issue Quantity', 'Line Item Total']].sort_values('Issue date', ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "Issue date": st.column_config.DateColumn("Date", format="DD MMM"),
            "Line Item Total": st.column_config.NumberColumn("Cost", format="₹%.0f"),
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
