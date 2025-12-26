import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="TODCO Probe", page_icon="🕵️", layout="wide")
st.title("Verint Connection Probe")

# --- 1. SETUP ---
if 'limit' not in st.session_state: st.session_state.limit = 50
five_months_ago = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%dT%H:%M:%S')
base_url = "https://data.sfgov.org/resource/vw6y-z8j6.json"
radius_meters = 48.8 

sites = [
    {"name": "Knox SRO", "lat": 37.77947681979851, "lon": -122.40646722115551},
    {"name": "Bayanihan", "lat": 37.78092868326207, "lon": -122.40917338372577},
    {"name": "Isabel", "lat": 37.779230374811554, "lon": -122.4107826194545}
]

location_clauses = [f"within_circle(point, {s['lat']}, {s['lon']}, {radius_meters})" for s in sites]
params = {
    "$where": f"({' OR '.join(location_clauses)}) AND requested_datetime > '{five_months_ago}' AND media_url IS NOT NULL",
    "$order": "requested_datetime DESC",
    "$limit": st.session_state.limit
}

# --- 2. FETCH DATA ---
df = pd.DataFrame()
try:
    r = requests.get(base_url, params=params)
    if r.status_code == 200:
        df = pd.DataFrame(r.json())
except: pass

# --- 3. THE PROBE FUNCTION ---
def probe_url(url):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mobile311.sfgov.org/",
        }
        r = session.get(url, headers=headers, timeout=10)
        
        # KEY DIAGNOSTICS
        status = r.status_code
        final_url = r.url
        content_len = len(r.text)
        
        # CHECK FOR SECRETS IN TEXT
        has_formref = "formref" in r.text
        has_csrf = "_csrf_token" in r.text
        
        return {
            "Original URL": url,
            "Final URL": final_url,
            "Status Code": status,
            "Content Length": content_len,
            "Found 'formref'?": has_formref,
            "Found 'csrf'?": has_csrf,
            "Preview (First 500 chars)": r.text[:500]
        }
    except Exception as e:
        return {"Error": str(e)}

# --- 4. DISPLAY RESULTS ---
if not df.empty:
    st.write(f"Found {len(df)} records. Probing the first valid Verint link...")
    
    found_verint = False
    for i, row in df.iterrows():
        url = row.get('media_url', '')
        if isinstance(url, dict): url = url.get('url', '')
        
        if "caseid" in url:
            found_verint = True
            st.subheader("Probe Result")
            
            # RUN THE PROBE
            result = probe_url(url)
            
            # SHOW RAW JSON
            st.json(result)
            
            # SHOW RAW HTML (For visual inspection)
            with st.expander("View Raw HTML Response"):
                st.code(result.get("Preview (First 500 chars)", "No content"))
            
            break
            
    if not found_verint:
        st.warning("No Verint links found in current batch.")
else:
    st.error("No data found from DataSF.")
