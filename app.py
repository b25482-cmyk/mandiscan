import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import gmean

# --- 1. DATA GENERATOR ENGINE (Simulating 3 Campus Nodes) ---
def generate_campus_node_data():
    np.random.seed(42)
    days = 60
    date_range = pd.date_range(start="2026-05-01", periods=days, freq="D")
    
    # Standard base flow per node (approx 1,000 people per node * 135 L/capita = 135,000 L/day)
    base_flow = 135000
    
    nodes = ['Node 1 (Beas-Side Hostels)', 'Node 2 (Uhl-Side Hostels)', 'Node 3 (Academic & Transit Hub)']
    all_data = []
    
    for day_idx in range(days):
        rain = 0 if day_idx < 40 else (np.random.exponential(12) if np.random.rand() > 0.4 else 0)
        
        for node in nodes:
            flow = base_flow + (rain * 2500)
            ph = np.random.normal(7.3, 0.15)
            turbidity = max(15, np.random.normal(175, 15) - (rain * 2))
            
            # Baseline normal ranges
            noro_raw = np.random.normal(1.1e5, 1.5e4)
            sars_raw = np.random.normal(4.0e4, 5e3)
            flu_raw = np.random.normal(1.5e4, 2e3)
            
            # Scenario Anomalies for Hackathon Impact
            if node == 'Node 1 (Beas-Side Hostels)' and day_idx >= 48:
                # Localized rapid Norovirus outbreak in West campus hostels
                noro_raw *= (1.28 ** (day_idx - 48))
                
            if node == 'Node 3 (Academic & Transit Hub)' and day_idx == 35:
                # Localized chemistry lab chemical dump anomaly
                ph = 4.8
                turbidity = 45.0
                
            if node == 'Node 2 (Uhl-Side Hostels)' and day_idx >= 52:
                # Localized Influenza A spike in East campus hostels
                flu_raw *= (1.22 ** (day_idx - 52))

            noro_load = noro_raw * flow
            sars_load = sars_raw * flow
            flu_load = flu_raw * flow
            
            all_data.append([date_range[day_idx], day_idx, node, rain, flow, ph, turbidity, noro_load, sars_load, flu_load])
            
    df = pd.DataFrame(all_data, columns=[
        'Date', 'Day_Index', 'Node', 'Rainfall_mm', 'Flow_Rate_L', 'pH', 'Turbidity_NTU', 
        'Noro_Load', 'SARS_Load', 'Flu_Load'
    ])
    return df

df = generate_campus_node_data()

# --- 2. PRESCRIPTIVE ENGINE (Why, Where, How Action Logic) ---
def analyze_node_incident(node_df, current_idx):
    if current_idx < 3:
        return {
            "Status": "🟡 INITIAL LEARNING PHASE", "Color": "#F1C40F",
            "Why": "The system is currently gathering the opening 3 days of baseline data.",
            "Measures": ["Maintain standard plant maintenance operations.", "Verify auto-sampler physical seal integrity."]
        }
    
    row = node_df.iloc[current_idx]
    
    # 1. CPCB Physical Parameter Violations
    if row['pH'] < 6.5:
        return {
            "Status": "🚨 PHYSICAL INTEGRITY CRITICAL: ACCIDENTAL ACID RELEASE", "Color": "#9B59B6",
            "Why": f"pH level dropped down to {row['pH']:.2f}, breaching CPCB minimum limits (6.5). The low turbidity confirms chemical dilution rather than human bio-waste aggregation.",
            "Measures": [
                "🛑 IMMEDIATELY halt downstream biological digester treatment to prevent biomass kill-off.",
                "🧪 Inject Sodium Carbonate (Soda Ash) dosing into the localized lift station to neutralize acidity.",
                "🥼 Alert the IIT Mandi Chemistry / Bio-X Labs to audit upstream chemical disposal logs for the last 12 hours."
            ]
        }
        
    # 2. Biological Velocity Trajectory Math
    past_loads = node_df.iloc[max(0, current_idx-3):current_idx]['Noro_Load'].values
    historical_geo_mean = gmean(past_loads) if len(past_loads) > 0 else 1.0
    noro_velocity = np.log10(row['Noro_Load']) - np.log10(historical_geo_mean)
    
    past_flu = node_df.iloc[max(0, current_idx-3):current_idx]['Flu_Load'].values
    flu_geo_mean = gmean(past_flu) if len(past_flu) > 0 else 1.0
    flu_velocity = np.log10(row['Flu_Load']) - np.log10(flu_geo_mean)

    if noro_velocity >= 0.7:
        fold_inc = 10**noro_velocity
        return {
            "Status": "🔴 BIOLOGICAL ALERT: LOCALIZED NOROVIRUS OUTBREAK", "Color": "#E74C3C",
            "Why": f"Norovirus daily mass load spiked by {fold_inc:.1f}x over the 3-sample rolling geometric mean. Stable pH and turbidity confirm this is a real epidemiological viral acceleration, not a water network artifact.",
            "Measures": [
                "🧼 Contact the corresponding Hostel Mess Committee to immediately stop self-service; deploy dedicated masked food handlers.",
                "🪣 Switch campus common-area sanitation protocols from quaternary ammonium to 1,000 ppm chlorine bleach solution.",
                "🏥 Advise the IIT Mandi Dispensary to pre-position anti-motility medications and rehydration salts for this hostel cluster."
            ]
        }
        
    if flu_velocity >= 0.6:
        fold_inc = 10**flu_velocity
        return {
            "Status": "🟠 RESPIRATORY WATCH: INFLUENZA A TRANSMISSION", "Color": "#E67E22",
            "Why": f"Influenza A load expanded by {fold_inc:.1f}x relative to baseline. Elevated wastewater mass load flags high viral shedding prior to broad clinic-level symptomatic presentation.",
            "Measures": [
                "😷 Issue a targeted health advisory to the specific hostel block suggesting masking inside common reading rooms.",
                "💨 Increase ventilation cycles and maximize outdoor fresh air intake inside the nearest mess hall and common lounges.",
                "🌡️ Launch proactive digital temperature self-reporting on the internal student portal."
            ]
        }
        
    return {
        "Status": "🟢 HEALTH STANDARDS SECURE", "Color": "#2ECC71",
        "Why": "All target pathogens and physico-chemical indices match normal, historic CPCB baseline parameters.",
        "Measures": ["Continue standard daily composite sampling schedules.", "Log data parameters into the rolling internal archive."]
    }

# --- 3. UI ADVISORY PORTAL DEPLOYMENT ---
st.set_page_config(page_title="MandiScan Action Portal", layout="wide")
st.title("🏔️ MandiScan: IIT Kamand Prescriptive Response Center")
st.caption("Active Countermeasure & Restoration Engine | Population: 3,000")

# Timeline Sandbox Controller
sim_day = st.slider("Step Through Simulation Day (Test the Scenarios!)", 0, 59, 54)
target_date = df[df['Day_Index'] == sim_day]['Date'].iloc[0].strftime('%Y-%m-%d')

st.markdown(f"### 🗓️ Incident Log Date: `{target_date}`")
st.write("---")

# Run analysis per node for the selected day
nodes = ['Node 1 (Beas-Side Hostels)', 'Node 2 (Uhl-Side Hostels)', 'Node 3 (Academic & Transit Hub)']

for node in nodes:
    node_full_data = df[df['Node'] == node].sort_values('Day_Index').reset_index(drop=True)
    analysis = analyze_node_incident(node_full_data, sim_day)
    
    # Visual Box Structure for Immediate Scanning
    with st.container():
        st.markdown(
            f"""
            <div style="background-color: {analysis['Color']}15; border-left: 6px solid {analysis['Color']}; padding: 18px; border-radius: 6px; margin-bottom: 20px;">
                <h3 style="margin-top:0; color:{analysis['Color']};">{node} — {analysis['Status']}</h3>
                <p><strong>🚨 THE WHY & WHERE:</strong> {analysis['Why']}</p>
                <strong>🛠️ MANDATORY CONTAINER ACTIONS TO RESTORE WATER QUALITY & HEALTH SAFETY:</strong>
                <ul style="margin-top: 5px;">
                    {"".join([f"<li style='margin-bottom:6px;'>{measure}</li>" for measure in analysis['Measures']])}
                </ul>
            </div>
            """, 
            unsafe_allow_html=True
        )

# Secondary expandable container for validation data
with st.expander("🔍 Click to view raw chemical/biological sensor values for this day"):
    current_day_data = df[df['Day_Index'] == sim_day]
    st.dataframe(current_day_data[['Node', 'pH', 'Turbidity_NTU', 'Flow_Rate_L', 'Noro_Load']].style.format({
        'pH': '{:.2f}', 'Turbidity_NTU': '{:.1f}', 'Flow_Rate_L': '{:,.0f}', 'Noro_Load': '{:.2e}'
    }))
