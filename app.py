import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- 1. IMD LIVE API FALLBACK WRAPPER ---
def fetch_imd_rainfall():
    """
    Simulates a live connection to the IMD API Gateway (api.imd.gov.in)
    with a robust operational fallback for the Mandi district grid.
    """
    try:
        response = requests.get("https://imd.gov.in", timeout=2)
        if response.status_code == 200:
            return float(response.json().get("rainfall_24h", 0.0))
    except:
        pass
    # Production fallback matching dynamic simulation controls
    return float(st.session_state.get("sandbox_rain", 0.0))

# --- 2. MULTI-BRANCH DECISION ENGINE ---
def execute_decision_pipeline(noro, sars, flu, ph, turb, rain, flow, baseline_noro=1e5, baseline_flu=2e4, baseline_sars=4e4):
    # Context / Correction branch:
    # Compute relative dilution coefficients based on IMD precipitation metrics
    dilution_factor = 1.0 if rain < 5 else (1.0 + (rain * 0.05))
    
    # Normalise active pathogen counts to completely counter rainfall dilution
    noro_norm = noro * dilution_factor
    flu_norm = flu * dilution_factor
    sars_norm = sars * dilution_factor
    
    # Disease-Warning branch:
    noro_ratio = noro_norm / baseline_noro
    flu_ratio = flu_norm / baseline_flu
    sars_ratio = sars_norm / baseline_sars
    
    pathogen_spike = max(noro_ratio, flu_ratio, sars_ratio)
    
    # Rule engine to decide confidence levels based on weather interference
    if pathogen_spike > 4.0:
        if rain < 15 and flow < 150000:
            disease_alert = "🔴 HIGH-CONFIDENCE OUTBREAK"
        else:
            disease_alert = "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)"
    elif pathogen_spike > 1.8:
        disease_alert = "🟡 ELEVATED TRANSMISSION WATCH"
    else:
        disease_alert = "🟢 PATHOGEN LEVELS STABLE"
        
    # Water/Sanitation branch:
    # Factor out rain to see if high turbidity is mud vs true sewage overflow
    expected_rain_turbidity = rain * 4.5
    unexplained_turbidity = max(0, turb - expected_rain_turbidity)
    
    if ph < 6.5 or ph > 8.5 or unexplained_turbidity > 220:
        if rain >= 25:
            sanitation_alert = "🟡 MONSOON RUNOFF ANOMALY"
        else:
            sanitation_alert = "🔴 UNEXPLAINED SANITATION VIOLATION"
    else:
        sanitation_alert = "🟢 WATER QUALITY NORMAL"
        
    return {
        "disease_status": disease_alert,
        "sanitation_status": sanitation_alert,
        "noro_stat": "HIGH" if noro_ratio > 3 else ("MED" if noro_ratio > 1.5 else "LOW"),
        "flu_stat": "HIGH" if flu_ratio > 3 else ("MED" if flu_ratio > 1.5 else "LOW"),
        "sars_stat": "HIGH" if sars_ratio > 3 else ("MED" if sars_ratio > 1.5 else "LOW"),
        "ph_stat": "HIGH" if (ph < 6.5 or ph > 8.5) else "LOW",
        "turb_stat": "HIGH" if unexplained_turbidity > 200 else ("MED" if unexplained_turbidity > 100 else "LOW"),
        "noro_ratio": noro_ratio,
        "flu_ratio": flu_ratio,
        "sars_ratio": sars_ratio
    }

# --- 3. STREAMLIT FRONTEND DEPLOYMENT ---
st.set_page_config(page_title="MandiScan Portal", layout="wide")
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🏔️ Campus Wastewater Health Alert Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D;'>IIT Mandi Kamand Infrastructure Monitoring Framework</p>", unsafe_allow_html=True)
st.write("---")

# Intercepting interactive states via Sidebar Control Panel
st.sidebar.header("🕹️ Simulation Sandbox Matrix")
st.sidebar.write("Manually alter indices to stress-test pipeline logic rules:")

st.session_state["sandbox_rain"] = st.sidebar.slider("IMD Weather Station Rain (mm)", 0, 50, 0)

sim_scenario = st.sidebar.selectbox("Choose Localised Campus Event Profile", [
    "Healthy Normal Operations Baseline", 
    "Norovirus Spike in Beas Block (Dry Weather)", 
    "Influenza Outbreak in Uhl Block during Heavy Rain",
    "Chemical Dump / Broken Pipe Event in Academic Zone"
])

# Fetch rainfall from the IMD API wrapper
live_rain = fetch_imd_rainfall()

# Map simulated metrics across individual campus hostel groups
hostel_zones = {
    "Beas-Side Hostel Cluster (B16-B23)": {"noro": 1.1e5, "flu": 1.8e4, "sars": 3.8e4, "ph": 7.3, "turb": 120, "flow": 135000},
    "Uhl-Side Hostel Cluster (B8-B12)": {"noro": 1.0e5, "flu": 1.9e4, "sars": 3.9e4, "ph": 7.2, "turb": 115, "flow": 130000},
    "Academic, Labs & Sports Complex Hub": {"noro": 0.8e5, "flu": 1.2e4, "sars": 2.5e4, "ph": 7.4, "turb": 90, "flow": 110000}
}

if sim_scenario == "Norovirus Spike in Beas Block (Dry Weather)":
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["noro"] = 6.5e5
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["turb"] = 280
elif sim_scenario == "Influenza Outbreak in Uhl Block during Heavy Rain":
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flu"] = 1.2e5
    st.session_state["sandbox_rain"] = 45 
    live_rain = 45
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flow"] = 195000
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["turb"] = 240 
elif sim_scenario == "Chemical Dump / Broken Pipe Event in Academic Zone":
    hostel_zones["Academic, Labs & Sports Complex Hub"]["ph"] = 5.2
    hostel_zones["Academic, Labs & Sports Complex Hub"]["turb"] = 350

# --- SECTION 1: MACRO PARAMETER STATUS RIBBON ---
st.markdown("### 📊 Live Parameter Multi-Indicator Status")
m_cols = st.columns(5)
metrics_labels = ["🦠 Norovirus", "🫁 Influenza A", "🦠 SARS-CoV-2", "🧪 pH Level", "🔬 Turbidity"]
metrics_keys = ["noro_stat", "flu_stat", "sars_stat", "ph_stat", "turb_stat"]

for idx, label in enumerate(metrics_labels):
    highest_status = "LOW"
    for zone, z_data in hostel_zones.items():
        res = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
        curr_stat = res[metrics_keys[idx]]
        if curr_stat == "HIGH": highest_status = "HIGH"
        elif curr_stat == "MED" and highest_status != "HIGH": highest_status = "MED"
        
    color_map = {"LOW": "#2ECC71", "MED": "#F1C40F", "HIGH": "#E74C3C"}
    with m_cols[idx]:
        st.markdown(
            f"""
            <div style="background-color:{color_map[highest_status]}20; border:1px solid {color_map[highest_status]}; padding:15px; border-radius:8px; text-align:center;">
                <h4 style="margin:0; color:#34495E;">{label}</h4>
                <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold; color:{color_map[highest_status]};">{highest_status}</p>
            </div>
            """, unsafe_allow_html=True
        )

st.write("---")

# --- SECTION 2: SCROLL-DOWN ZONE INTERVENTIONS ---
st.markdown("### 🗺️ Localised Hostel Block Assessment & Prescriptive Actions")

# Map colors to specific status terms for border rendering
color_mapping = {
    "🔴 HIGH-CONFIDENCE OUTBREAK": "#E74C3C",
    "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)": "#F39C12",
    "🟡 ELEVATED TRANSMISSION WATCH": "#F1C40F",
    "🟢 PATHOGEN LEVELS STABLE": "#2ECC71",
    "🟡 MONSOON RUNOFF ANOMALY": "#F1C40F",
    "🔴 UNEXPLAINED SANITATION VIOLATION": "#9B59B6",
    "🟢 WATER QUALITY NORMAL": "#2ECC71"
}

for zone, z_data in hostel_zones.items():
    analysis = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
    d_color = color_mapping.get(analysis['disease_status'], "#BDC3C7")
    s_color = color_mapping.get(analysis['sanitation_status'], "#BDC3C7")
    
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:#FAFAFA; border:1px solid #E0E0E0; padding:20px; border-radius:8px; margin-bottom:25px;">
                <h2 style="color:#2C3E50; margin-top:0;">📍 {zone}</h2>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:15px;">
                    <div style="padding:10px; border-left:4px solid {d_color}; background-color:{d_color}10;">
                        <strong>🦠 DISEASE BRANCH STATUS:</strong><br><span style="color:{d_color}; font-weight:bold;">{analysis['disease_status']}</span>
                    </div>
                    <div style="padding:10px; border-left:4px solid {s_color}; background-color:{s_color}10;">
                        <strong>💧 SANITATION BRANCH STATUS:</strong><br><span style="color:{s_color}; font-weight:bold;">{analysis['sanitation_status']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True
        )
        
        st.markdown("**🔬 Metric Anomalies Identified:**")
        anomaly_found = False
        
        if analysis["noro_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Norovirus concentration expanded significantly ({analysis['noro_ratio']:.1f}x baseline). This points to rising gastrointestinal activity inside this hostel group.")
            anomaly_found = True
        if analysis["flu_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Influenza A load spiked ({analysis['flu_ratio']:.1f}x baseline). This points to an active respiratory cluster transmission within common reading rooms.")
            anomaly_found = True
        if analysis["ph_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Localized pH dropped to {z_data['ph']:.2f}. This is an asset violation indicating unauthorized upstream chemical disposal.")
            anomaly_found = True
        if not anomaly_found:
            st.markdown("✅ No unexpected parameter variances identified. Water matrices are stable within CPCB parameters.")
            
        st.markdown("<p style='margin-top:15px; margin-bottom:5px;'><strong>🛠️ Recommended Corrective Protocols:</strong></p>", unsafe_allow_html=True)
        
        # --- FIXED & INDENTED MULTI-BRANCH RESPONSE MATRIX ---
        actions = []
import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- 1. IMD LIVE API FALLBACK WRAPPER ---
def fetch_imd_rainfall():
    """
    Simulates a live connection to the IMD API Gateway (api.imd.gov.in)
    with a robust operational fallback for the Mandi district grid.
    """
    try:
        response = requests.get("https://imd.gov.in", timeout=2)
        if response.status_code == 200:
            return float(response.json().get("rainfall_24h", 0.0))
    except:
        pass
    # Production fallback matching dynamic simulation controls
    return float(st.session_state.get("sandbox_rain", 0.0))

# --- 2. MULTI-BRANCH DECISION ENGINE ---
def execute_decision_pipeline(noro, sars, flu, ph, turb, rain, flow, baseline_noro=1e5, baseline_flu=2e4, baseline_sars=4e4):
    # Context / Correction branch:
    # Compute relative dilution coefficients based on IMD precipitation metrics
    dilution_factor = 1.0 if rain < 5 else (1.0 + (rain * 0.05))
    
    # Normalise active pathogen counts to completely counter rainfall dilution
    noro_norm = noro * dilution_factor
    flu_norm = flu * dilution_factor
    sars_norm = sars * dilution_factor
    
    # Disease-Warning branch:
    noro_ratio = noro_norm / baseline_noro
    flu_ratio = flu_norm / baseline_flu
    sars_ratio = sars_norm / baseline_sars
    
    pathogen_spike = max(noro_ratio, flu_ratio, sars_ratio)
    
    # Rule engine to decide confidence levels based on weather interference
    if pathogen_spike > 4.0:
        if rain < 15 and flow < 150000:
            disease_alert = "🔴 HIGH-CONFIDENCE OUTBREAK"
        else:
            disease_alert = "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)"
    elif pathogen_spike > 1.8:
        disease_alert = "🟡 ELEVATED TRANSMISSION WATCH"
    else:
        disease_alert = "🟢 PATHOGEN LEVELS STABLE"
        
    # Water/Sanitation branch:
    # Factor out rain to see if high turbidity is mud vs true sewage overflow
    expected_rain_turbidity = rain * 4.5
    unexplained_turbidity = max(0, turb - expected_rain_turbidity)
    
    if ph < 6.5 or ph > 8.5 or unexplained_turbidity > 220:
        if rain >= 25:
            sanitation_alert = "🟡 MONSOON RUNOFF ANOMALY"
        else:
            sanitation_alert = "🔴 UNEXPLAINED SANITATION VIOLATION"
    else:
        sanitation_alert = "🟢 WATER QUALITY NORMAL"
        
    return {
        "disease_status": disease_alert,
        "sanitation_status": sanitation_alert,
        "noro_stat": "HIGH" if noro_ratio > 3 else ("MED" if noro_ratio > 1.5 else "LOW"),
        "flu_stat": "HIGH" if flu_ratio > 3 else ("MED" if flu_ratio > 1.5 else "LOW"),
        "sars_stat": "HIGH" if sars_ratio > 3 else ("MED" if sars_ratio > 1.5 else "LOW"),
        "ph_stat": "HIGH" if (ph < 6.5 or ph > 8.5) else "LOW",
        "turb_stat": "HIGH" if unexplained_turbidity > 200 else ("MED" if unexplained_turbidity > 100 else "LOW"),
        "noro_ratio": noro_ratio,
        "flu_ratio": flu_ratio,
        "sars_ratio": sars_ratio
    }

# --- 3. STREAMLIT FRONTEND DEPLOYMENT ---
st.set_page_config(page_title="MandiScan Portal", layout="wide")
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🏔️ Campus Wastewater Health Alert Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D;'>IIT Mandi Kamand Infrastructure Monitoring Framework</p>", unsafe_allow_html=True)
st.write("---")

# Intercepting interactive states via Sidebar Control Panel
st.sidebar.header("🕹️ Simulation Sandbox Matrix")
st.sidebar.write("Manually alter indices to stress-test pipeline logic rules:")

st.session_state["sandbox_rain"] = st.sidebar.slider("IMD Weather Station Rain (mm)", 0, 50, 0)

sim_scenario = st.sidebar.selectbox("Choose Localised Campus Event Profile", [
    "Healthy Normal Operations Baseline", 
    "Norovirus Spike in Beas Block (Dry Weather)", 
    "Influenza Outbreak in Uhl Block during Heavy Rain",
    "Chemical Dump / Broken Pipe Event in Academic Zone"
])

# Fetch rainfall from the IMD API wrapper
live_rain = fetch_imd_rainfall()

# Map simulated metrics across individual campus hostel groups
hostel_zones = {
    "Beas-Side Hostel Cluster (B16-B23)": {"noro": 1.1e5, "flu": 1.8e4, "sars": 3.8e4, "ph": 7.3, "turb": 120, "flow": 135000},
    "Uhl-Side Hostel Cluster (B8-B12)": {"noro": 1.0e5, "flu": 1.9e4, "sars": 3.9e4, "ph": 7.2, "turb": 115, "flow": 130000},
    "Academic, Labs & Sports Complex Hub": {"noro": 0.8e5, "flu": 1.2e4, "sars": 2.5e4, "ph": 7.4, "turb": 90, "flow": 110000}
}

if sim_scenario == "Norovirus Spike in Beas Block (Dry Weather)":
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["noro"] = 6.5e5
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["turb"] = 280
elif sim_scenario == "Influenza Outbreak in Uhl Block during Heavy Rain":
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flu"] = 1.2e5
    st.session_state["sandbox_rain"] = 45 
    live_rain = 45
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flow"] = 195000
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["turb"] = 240 
elif sim_scenario == "Chemical Dump / Broken Pipe Event in Academic Zone":
    hostel_zones["Academic, Labs & Sports Complex Hub"]["ph"] = 5.2
    hostel_zones["Academic, Labs & Sports Complex Hub"]["turb"] = 350

# --- SECTION 1: MACRO PARAMETER STATUS RIBBON ---
st.markdown("### 📊 Live Parameter Multi-Indicator Status")
m_cols = st.columns(5)
metrics_labels = ["🦠 Norovirus", "🫁 Influenza A", "🦠 SARS-CoV-2", "🧪 pH Level", "🔬 Turbidity"]
metrics_keys = ["noro_stat", "flu_stat", "sars_stat", "ph_stat", "turb_stat"]

for idx, label in enumerate(metrics_labels):
    highest_status = "LOW"
    for zone, z_data in hostel_zones.items():
        res = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
        curr_stat = res[metrics_keys[idx]]
        if curr_stat == "HIGH": highest_status = "HIGH"
        elif curr_stat == "MED" and highest_status != "HIGH": highest_status = "MED"
        
    color_map = {"LOW": "#2ECC71", "MED": "#F1C40F", "HIGH": "#E74C3C"}
    with m_cols[idx]:
        st.markdown(
            f"""
            <div style="background-color:{color_map[highest_status]}20; border:1px solid {color_map[highest_status]}; padding:15px; border-radius:8px; text-align:center;">
                <h4 style="margin:0; color:#34495E;">{label}</h4>
                <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold; color:{color_map[highest_status]};">{highest_status}</p>
            </div>
            """, unsafe_allow_html=True
        )

st.write("---")

# --- SECTION 2: SCROLL-DOWN ZONE INTERVENTIONS ---
st.markdown("### 🗺️ Localised Hostel Block Assessment & Prescriptive Actions")

# Map colors to specific status terms for border rendering
color_mapping = {
    "🔴 HIGH-CONFIDENCE OUTBREAK": "#E74C3C",
    "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)": "#F39C12",
    "🟡 ELEVATED TRANSMISSION WATCH": "#F1C40F",
    "🟢 PATHOGEN LEVELS STABLE": "#2ECC71",
    "🟡 MONSOON RUNOFF ANOMALY": "#F1C40F",
    "🔴 UNEXPLAINED SANITATION VIOLATION": "#9B59B6",
    "🟢 WATER QUALITY NORMAL": "#2ECC71"
}

for zone, z_data in hostel_zones.items():
    analysis = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
    d_color = color_mapping.get(analysis['disease_status'], "#BDC3C7")
    s_color = color_mapping.get(analysis['sanitation_status'], "#BDC3C7")
    
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:#FAFAFA; border:1px solid #E0E0E0; padding:20px; border-radius:8px; margin-bottom:25px;">
                <h2 style="color:#2C3E50; margin-top:0;">📍 {zone}</h2>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:15px;">
                    <div style="padding:10px; border-left:4px solid {d_color}; background-color:{d_color}10;">
                        <strong>🦠 DISEASE BRANCH STATUS:</strong><br><span style="color:{d_color}; font-weight:bold;">{analysis['disease_status']}</span>
                    </div>
                    <div style="padding:10px; border-left:4px solid {s_color}; background-color:{s_color}10;">
                        <strong>💧 SANITATION BRANCH STATUS:</strong><br><span style="color:{s_color}; font-weight:bold;">{analysis['sanitation_status']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True
        )
        
        st.markdown("**🔬 Metric Anomalies Identified:**")
        anomaly_found = False
        
        if analysis["noro_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Norovirus concentration expanded significantly ({analysis['noro_ratio']:.1f}x baseline). This points to rising gastrointestinal activity inside this hostel group.")
            anomaly_found = True
        if analysis["flu_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Influenza A load spiked ({analysis['flu_ratio']:.1f}x baseline). This points to an active respiratory cluster transmission within common reading rooms.")
            anomaly_found = True
        if analysis["ph_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Localized pH dropped to {z_data['ph']:.2f}. This is an asset violation indicating unauthorized upstream chemical disposal.")
            anomaly_found = True
        if not anomaly_found:
            st.markdown("✅ No unexpected parameter variances identified. Water matrices are stable within CPCB parameters.")
            
        st.markdown("<p style='margin-top:15px; margin-bottom:5px;'><strong>🛠️ Recommended Corrective Protocols:</strong></p>", unsafe_allow_html=True)
        
        # --- FIXED & INDENTED MULTI-BRANCH RESPONSE MATRIX ---
        actions = []
import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- 1. IMD LIVE API FALLBACK WRAPPER ---
def fetch_imd_rainfall():
    """
    Simulates a live connection to the IMD API Gateway (api.imd.gov.in)
    with a robust operational fallback for the Mandi district grid.
    """
    try:
        response = requests.get("https://imd.gov.in", timeout=2)
        if response.status_code == 200:
            return float(response.json().get("rainfall_24h", 0.0))
    except:
        pass
    # Production fallback matching dynamic simulation controls
    return float(st.session_state.get("sandbox_rain", 0.0))

# --- 2. MULTI-BRANCH DECISION ENGINE ---
def execute_decision_pipeline(noro, sars, flu, ph, turb, rain, flow, baseline_noro=1e5, baseline_flu=2e4, baseline_sars=4e4):
    # Context / Correction branch:
    # Compute relative dilution coefficients based on IMD precipitation metrics
    dilution_factor = 1.0 if rain < 5 else (1.0 + (rain * 0.05))
    
    # Normalise active pathogen counts to completely counter rainfall dilution
    noro_norm = noro * dilution_factor
    flu_norm = flu * dilution_factor
    sars_norm = sars * dilution_factor
    
    # Disease-Warning branch:
    noro_ratio = noro_norm / baseline_noro
    flu_ratio = flu_norm / baseline_flu
    sars_ratio = sars_norm / baseline_sars
    
    pathogen_spike = max(noro_ratio, flu_ratio, sars_ratio)
    
    # Rule engine to decide confidence levels based on weather interference
    if pathogen_spike > 4.0:
        if rain < 15 and flow < 150000:
            disease_alert = "🔴 HIGH-CONFIDENCE OUTBREAK"
        else:
            disease_alert = "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)"
    elif pathogen_spike > 1.8:
        disease_alert = "🟡 ELEVATED TRANSMISSION WATCH"
    else:
        disease_alert = "🟢 PATHOGEN LEVELS STABLE"
        
    # Water/Sanitation branch:
    # Factor out rain to see if high turbidity is mud vs true sewage overflow
    expected_rain_turbidity = rain * 4.5
    unexplained_turbidity = max(0, turb - expected_rain_turbidity)
    
    if ph < 6.5 or ph > 8.5 or unexplained_turbidity > 220:
        if rain >= 25:
            sanitation_alert = "🟡 MONSOON RUNOFF ANOMALY"
        else:
            sanitation_alert = "🔴 UNEXPLAINED SANITATION VIOLATION"
    else:
        sanitation_alert = "🟢 WATER QUALITY NORMAL"
        
    return {
        "disease_status": disease_alert,
        "sanitation_status": sanitation_alert,
        "noro_stat": "HIGH" if noro_ratio > 3 else ("MED" if noro_ratio > 1.5 else "LOW"),
        "flu_stat": "HIGH" if flu_ratio > 3 else ("MED" if flu_ratio > 1.5 else "LOW"),
        "sars_stat": "HIGH" if sars_ratio > 3 else ("MED" if sars_ratio > 1.5 else "LOW"),
        "ph_stat": "HIGH" if (ph < 6.5 or ph > 8.5) else "LOW",
        "turb_stat": "HIGH" if unexplained_turbidity > 200 else ("MED" if unexplained_turbidity > 100 else "LOW"),
        "noro_ratio": noro_ratio,
        "flu_ratio": flu_ratio,
        "sars_ratio": sars_ratio
    }

# --- 3. STREAMLIT FRONTEND DEPLOYMENT ---
st.set_page_config(page_title="MandiScan Portal", layout="wide")
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🏔️ Campus Wastewater Health Alert Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D;'>IIT Mandi Kamand Infrastructure Monitoring Framework</p>", unsafe_allow_html=True)
st.write("---")

# Intercepting interactive states via Sidebar Control Panel
st.sidebar.header("🕹️ Simulation Sandbox Matrix")
st.sidebar.write("Manually alter indices to stress-test pipeline logic rules:")

st.session_state["sandbox_rain"] = st.sidebar.slider("IMD Weather Station Rain (mm)", 0, 50, 0)

sim_scenario = st.sidebar.selectbox("Choose Localised Campus Event Profile", [
    "Healthy Normal Operations Baseline", 
    "Norovirus Spike in Beas Block (Dry Weather)", 
    "Influenza Outbreak in Uhl Block during Heavy Rain",
    "Chemical Dump / Broken Pipe Event in Academic Zone"
])

# Fetch rainfall from the IMD API wrapper
live_rain = fetch_imd_rainfall()

# Map simulated metrics across individual campus hostel groups
hostel_zones = {
    "Beas-Side Hostel Cluster (B16-B23)": {"noro": 1.1e5, "flu": 1.8e4, "sars": 3.8e4, "ph": 7.3, "turb": 120, "flow": 135000},
    "Uhl-Side Hostel Cluster (B8-B12)": {"noro": 1.0e5, "flu": 1.9e4, "sars": 3.9e4, "ph": 7.2, "turb": 115, "flow": 130000},
    "Academic, Labs & Sports Complex Hub": {"noro": 0.8e5, "flu": 1.2e4, "sars": 2.5e4, "ph": 7.4, "turb": 90, "flow": 110000}
}

if sim_scenario == "Norovirus Spike in Beas Block (Dry Weather)":
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["noro"] = 6.5e5
    hostel_zones["Beas-Side Hostel Cluster (B16-B23)"]["turb"] = 280
elif sim_scenario == "Influenza Outbreak in Uhl Block during Heavy Rain":
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flu"] = 1.2e5
    st.session_state["sandbox_rain"] = 45 
    live_rain = 45
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["flow"] = 195000
    hostel_zones["Uhl-Side Hostel Cluster (B8-B12)"]["turb"] = 240 
elif sim_scenario == "Chemical Dump / Broken Pipe Event in Academic Zone":
    hostel_zones["Academic, Labs & Sports Complex Hub"]["ph"] = 5.2
    hostel_zones["Academic, Labs & Sports Complex Hub"]["turb"] = 350

# --- SECTION 1: MACRO PARAMETER STATUS RIBBON ---
st.markdown("### 📊 Live Parameter Multi-Indicator Status")
m_cols = st.columns(5)
metrics_labels = ["🦠 Norovirus", "🫁 Influenza A", "🦠 SARS-CoV-2", "🧪 pH Level", "🔬 Turbidity"]
metrics_keys = ["noro_stat", "flu_stat", "sars_stat", "ph_stat", "turb_stat"]

for idx, label in enumerate(metrics_labels):
    highest_status = "LOW"
    for zone, z_data in hostel_zones.items():
        res = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
        curr_stat = res[metrics_keys[idx]]
        if curr_stat == "HIGH": highest_status = "HIGH"
        elif curr_stat == "MED" and highest_status != "HIGH": highest_status = "MED"
        
    color_map = {"LOW": "#2ECC71", "MED": "#F1C40F", "HIGH": "#E74C3C"}
    with m_cols[idx]:
        st.markdown(
            f"""
            <div style="background-color:{color_map[highest_status]}20; border:1px solid {color_map[highest_status]}; padding:15px; border-radius:8px; text-align:center;">
                <h4 style="margin:0; color:#34495E;">{label}</h4>
                <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold; color:{color_map[highest_status]};">{highest_status}</p>
            </div>
            """, unsafe_allow_html=True
        )

st.write("---")

# --- SECTION 2: SCROLL-DOWN ZONE INTERVENTIONS ---
st.markdown("### 🗺️ Localised Hostel Block Assessment & Prescriptive Actions")

# Map colors to specific status terms for border rendering
color_mapping = {
    "🔴 HIGH-CONFIDENCE OUTBREAK": "#E74C3C",
    "🟡 UNCERTAIN SIGNAL (WEATHER INTERFERENCE)": "#F39C12",
    "🟡 ELEVATED TRANSMISSION WATCH": "#F1C40F",
    "🟢 PATHOGEN LEVELS STABLE": "#2ECC71",
    "🟡 MONSOON RUNOFF ANOMALY": "#F1C40F",
    "🔴 UNEXPLAINED SANITATION VIOLATION": "#9B59B6",
    "🟢 WATER QUALITY NORMAL": "#2ECC71"
}

for zone, z_data in hostel_zones.items():
    analysis = execute_decision_pipeline(z_data["noro"], z_data["flu"], z_data["sars"], z_data["ph"], z_data["turb"], live_rain, z_data["flow"])
    d_color = color_mapping.get(analysis['disease_status'], "#BDC3C7")
    s_color = color_mapping.get(analysis['sanitation_status'], "#BDC3C7")
    
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:#FAFAFA; border:1px solid #E0E0E0; padding:20px; border-radius:8px; margin-bottom:25px;">
                <h2 style="color:#2C3E50; margin-top:0;">📍 {zone}</h2>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:15px;">
                    <div style="padding:10px; border-left:4px solid {d_color}; background-color:{d_color}10;">
                        <strong>🦠 DISEASE BRANCH STATUS:</strong><br><span style="color:{d_color}; font-weight:bold;">{analysis['disease_status']}</span>
                    </div>
                    <div style="padding:10px; border-left:4px solid {s_color}; background-color:{s_color}10;">
                        <strong>💧 SANITATION BRANCH STATUS:</strong><br><span style="color:{s_color}; font-weight:bold;">{analysis['sanitation_status']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True
        )
        
        st.markdown("**🔬 Metric Anomalies Identified:**")
        anomaly_found = False
        
        if analysis["noro_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Norovirus concentration expanded significantly ({analysis['noro_ratio']:.1f}x baseline). This points to rising gastrointestinal activity inside this hostel group.")
            anomaly_found = True
        if analysis["flu_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Influenza A load spiked ({analysis['flu_ratio']:.1f}x baseline). This points to an active respiratory cluster transmission within common reading rooms.")
            anomaly_found = True
        if analysis["ph_stat"] == "HIGH":
            st.markdown(f"⚠️ *Unexpected change:* Localized pH dropped to {z_data['ph']:.2f}. This is an asset violation indicating unauthorized upstream chemical disposal.")
            anomaly_found = True
        if not anomaly_found:
            st.markdown("✅ No unexpected parameter variances identified. Water matrices are stable within CPCB parameters.")
            
        st.markdown("<p style='margin-top:15px; margin-bottom:5px;'><strong>🛠️ Recommended Corrective Protocols:</strong></p>", unsafe_allow_html=True)
        
        # --- FIXED & INDENTED MULTI-BRANCH RESPONSE MATRIX ---
        actions = []
        if "🔴 HIGH-CONFIDENCE" in analysis["disease_status"]:
            if analysis["noro_stat"] == "HIGH":actions = ["Halt mess self-service operations immediately; mandate dedicated plate handlers.", "Switch cleaning crews to 1,000 ppm sodium hypochlorite bleach for all common bathrooms."]
            elif analysis["flu_stat"] == "HIGH":actions = ["Issue targeted masking directives for shared reading lounges inside this block.", "Increase HVAC exhaust cycles to max air exchanges within hostel common spaces."]
        elif "🟡 UNCERTAIN SIGNAL" in analysis["disease_status"]:actions = ["Postpone major public health restrictions.", "Trigger automated re-sampling within a 12-hour window to account for heavy stormwater runoff."]
        elif "🔴 UNEXPLAINED SANITATION" in analysis["sanitation_status"]:actions = ["Halt flow routing to the main biological aeration basin to prevent biomass kill-off.", "Dispatch maintenance to check upstream lab neutralization tanks for leaks."]
        else:
            actions = ["Maintain baseline tracking schedules.", "Log active physical attributes to the historical campus baseline file."]
        st.markdown("".join([f"• {act}" for act in actions]), unsafe_allow_html=True)
        st.markdown("", unsafe_allow_html=True)
