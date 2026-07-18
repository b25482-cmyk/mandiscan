import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import gmean

# --- 1. DATA GENERATOR ENGINE (Documented & CPCB Rooted) ---
def generate_synthetic_data():
    np.random.seed(42)
    weeks = 12
    days = weeks * 7
    date_range = pd.date_range(start="2026-05-01", periods=days, freq="D")
    
    # Base CPCB Metrics for 3,000 capita at 135 Liters/day (Total ~405,000 L/day normal)
    base_flow = 3000 * 135 
    
    data = []
    for i in range(days):
        # Simulate Himalayan Weather Patterns (Monsoon arrival around day 40)
        rain = 0 if i < 40 else (np.random.exponential(15) if np.random.rand() > 0.4 else 0)
        flow_rate = base_flow + (rain * 8000) # Infiltration factor
        
        # CPCB Water Quality Standard limits
        ph = np.random.normal(7.3, 0.2)
        if i == 25: ph = 5.1 # Inject industrial/lab dump anomaly
        
        # Turbidity dilutes during heavy rain
        turbidity = max(10, np.random.normal(180, 20) - (rain * 3))
        
        # Epidemiological curves (Baseline vs Outbreak starting Day 50)
        if i < 50:
            noro_raw = np.random.normal(1.2e5, 2e4)
            sars_raw = np.random.normal(4.5e4, 8e3)
            flu_raw = np.random.normal(1.8e4, 3e3)
        else:
            # Norovirus outbreak exponential surge
            noro_raw = np.random.normal(1.2e5, 2e4) * (1.18 ** (i - 50))
            sars_raw = np.random.normal(4.5e4, 8e3)
            # Add a milder seasonal Influenza bump around Day 65
            if i >= 65:
                flu_raw = np.random.normal(1.8e4, 3e3) * (1.08 ** (i - 65))
            else:
                flu_raw = np.random.normal(1.8e4, 3e3)
            
        # Compute absolute Daily Mass Load (Neutralizes rainfall dilution)
        noro_load = noro_raw * flow_rate
        sars_load = sars_raw * flow_rate
        flu_load = flu_raw * flow_rate
        
        data.append([date_range[i], rain, flow_rate, ph, turbidity, noro_raw, sars_raw, flu_raw, noro_load, sars_load, flu_load])
        
    df = pd.DataFrame(data, columns=[
        'Date', 'Rainfall_mm', 'Flow_Rate_L', 'pH', 'Turbidity_NTU', 
        'Noro_Conc', 'SARS_Conc', 'Flu_Conc', 'Noro_Load', 'SARS_Load', 'Flu_Load'
    ])
    return df

df = generate_synthetic_data()

# --- 2. ALERT LOGIC ENGINE ---
def compute_alerts(df):
    status_list = []
    for idx in range(len(df)):
        row = df.iloc[idx]
        if idx < 3:
            status_list.append(('🟡 LEARN', 'Building Initial Baseline...', '#F1C40F'))
            continue
            
        if row['pH'] < 6.0 or row['pH'] > 8.5:
            status_list.append(('⚠️ CRITICAL', 'CPCB pH Violation: Sample Tampered/Invalid', '#95A5A6'))
            continue
            
        # 3-Sample Historical Geometric Mean
        past_loads = df.iloc[max(0, idx-3):idx]['Noro_Load'].values
        historical_geo_mean = gmean(past_loads)
        
        # Calculate velocity
        velocity = np.log10(row['Noro_Load']) - np.log10(historical_geo_mean)
        
        if velocity >= 0.7:
            status_list.append(('🔴 ALERT', f'Outbreak Trend Detected (+{10**velocity:.1f}x Load)', '#E74C3C'))
        elif velocity >= 0.3:
            status_list.append(('🟡 WATCH', f'Elevated Viral Acceleration (+{10**velocity:.1f}x Load)', '#F39C12'))
        else:
            status_list.append(('🟢 NORMAL', 'Viral Baseline Stable', '#2ECC71'))
            
    df['Status'], df['Message'], df['Color'] = zip(*status_list)
    return df

df = compute_alerts(df)

# --- 3. WASTEWATER-SCAN INSPIRED UI ---
st.set_page_config(page_title="MandiScan Portal", layout="wide")
st.title("🏔️ MandiScan: IIT Kamand Campus Epidemiological Engine")
st.caption("Prototype Wastewater-Based Surveillance Dashboard | Target Size: 3,000 Capita")

# Interactive Timeline Slider to show historical trends
current_idx = st.slider("Simulate Hackathon Timeline (Day)", 3, len(df)-1, len(df)-1)
current_row = df.iloc[current_idx]

# KPI Summary Ribbon
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Current Sample Date", current_row['Date'].strftime('%Y-%m-%d'))
with kpi2:
    st.markdown(f"### System Status\n<h2 style='color:{current_row['Color']}'>{current_row['Status']}</h2>", unsafe_allow_html=True)
with kpi3:
    st.metric("Norovirus Daily Load", f"{current_row['Noro_Load']:.2e} GC/day")
with kpi4:
    st.metric("Influenza A Daily Load", f"{current_row['Flu_Load']:.2e} GC/day")

st.info(f"**Diagnostic Message:** {current_row['Message']}")

# Interactive Trend Graph
st.subheader("Pathogen Abundance & Dilution Tracking")
fig = go.Figure()
visible_df = df.iloc[:current_idx+1]

fig.add_trace(go.Scatter(x=visible_df['Date'], y=visible_df['Noro_Load'], name='Norovirus Load (GC/day)', line=dict(color='#E74C3C', width=3)))
fig.add_trace(go.Scatter(x=visible_df['Date'], y=visible_df['SARS_Load'], name='SARS-CoV-2 Load (GC/day)', line=dict(color='#3498DB', width=2)))
fig.add_trace(go.Scatter(x=visible_df['Date'], y=visible_df['Flu_Load'], name='Influenza A Load (GC/day)', line=dict(color='#9B59B6', width=2)))
fig.add_trace(go.Scatter(x=visible_df['Date'], y=visible_df['Flow_Rate_L'], name='Flow Rate (L/day)', yaxis='y2', line=dict(color='#2ECC71', dash='dash')))

fig.update_layout(
    yaxis=dict(title="Viral Load (Genomic Copies / Day)", type="log"),
    yaxis2=dict(title="Flow Volume (Liters)", overlaying='y', side='right'),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# Environmental Parameter Overview Dashboard Section
st.subheader("Physico-Chemical Context (CPCB Quality Monitoring)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Rainfall Today", f"{current_row['Rainfall_mm']:.1f} mm")
with col2:
    st.metric("Measured pH Value", f"{current_row['pH']:.2f}")
with col3:
    st.metric("Sample Turbidity", f"{current_row['Turbidity_NTU']:.1f} NTU")
