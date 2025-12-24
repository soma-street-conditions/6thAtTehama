import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. Page Config
st.set_page_config(page_title="Radius Watch", page_icon="📍", layout="wide")

# --- NO CRAWL & STYLING ---
st.markdown("""
    <style>
        div[data-testid="stVerticalBlock"] > div { gap: 0.2rem; }
        .stMarkdown p { font-size: 0.9rem; margin-bottom: 0px; }
        div.stButton > button { width: 100%; }
    </style>
    <meta name="robots" content="noindex, nofollow">
""", unsafe_allow_html=True)

# 2. Session State for "Load More"
if 'limit' not in st.session_state:
    st.session_state.limit = 800

# Header
st.header("My Block: 160ft Radius")
st.write("Daily feed of ALL 311 reports within ~160 feet of the target location.")
st.markdown("Download the Solve SF App to report your concerns to the City of San Francisco. ([iOS](https://apps.apple.com/us/app/solve-sf/id6737751237) | [Android](https://play.google.com/store/apps/details?id=com.woahfinally.solvesf))")
st.markdown("---")

# 3. Date & API Setup
ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%S')
base_url = "https://data.sfgov.org/resource/vw6y-z8j6.json"

# TARGET COORDINATES
target_lat = 37.77935708464253
target_lon = -122.4064893420712
radius_meters = 48.8  # 160 feet approx

# 4. Query
# using Socrata's within_circle(location_column, lat, long, radius_in_meters)
params = {
    "$where": f"within_circle(point, {target_lat}, {target_lon}, {radius_meters}) AND requested_datetime > '{ninety_days_ago}' AND media_url IS NOT NULL",
    "$order": "requested_datetime DESC",
    "$limit": st.session_state.limit
}

# 5. Fetch Data
@st.cache_data(ttl=300)
def get_data(query_limit):
    try:
        r = requests.get(base_url, params=params)
        if r.status_code == 200:
            return pd.DataFrame(r.json())
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

df = get_data(st.session_state.limit)

# 6. Helper: Identify Image vs Portal Link
def get_image_info(media_item):
    if not media_item: return None, False
    url = media_item.get('url') if isinstance(media_item, dict) else media_item
    if not url: return None, False
    clean_url = url.split('?')[0].lower()
    
    # Case A: Standard Image (Public Cloud)
    if clean_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
        return url, True
        
    # Case B: Verint Portal or other Web Links
    return url, False

# 7. Display Feed
if not df.empty:
    cols = st.columns(4)
    display_count = 0
    
    for index, row in df.iterrows():
        notes = str(row.get('status_notes', '')).lower()
        if 'duplicate' in notes:
            continue

        full_url, is_viewable = get_image_info(row.get('media_url'))
        
        # STRICT FILTER: Only show records with viewable images
        if full_url and is_viewable:
            col_index = display_count % 4
            
            with cols[col_index]:
                with st.container(border=True):
                    
                    # --- STANDARD IMAGE COMPONENT ---
                    st.image(full_url, use_container_width=True)

                    # Metadata
                    if 'requested_datetime' in row:
                        date_str = pd.to_datetime(row['requested_datetime']).strftime('%b %d, %I:%M %p')
                    else:
                        date_str = "?"
                    
                    # Display Service Name (Category) since we now show all types
                    category = row.get('service_name', 'Unknown Issue')
                    address = row.get('address', 'Location N/A')
                    
                    # Clean up Google Maps Link
                    map_url = f"https://www.google.com/maps?q={address.replace(' ', '+')}"
                    
                    st.markdown(f"**{category}**")
                    st.markdown(f"{date_str} | [{address}]({map_url})")
            
            display_count += 1
            
    if display_count == 0:
        st.info("No viewable images found in this radius (Web Portal links hidden).")
    
    # Load More Button
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(f"Load More Records (Current: {st.session_state.limit})"):
            st.session_state.limit += 300
            st.rerun()

else:
    st.info(f"No records found within 160ft of {target_lat}, {target_lon} in the last 90 days.")

# Footer & Methodology
st.markdown("---")
st.caption("Data source: [DataSF | Open Data Portal](https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6/about_data)")

with st.expander("Methodology & Notes"):
    st.markdown(f"""
    **Filters Applied:**
    * **Location:** Within 160 feet ({radius_meters} meters) of {target_lat}, {target_lon}.
    * **Categories:** ALL (No category filter applied).
    * **Timeframe:** Rolling 90-day window.
    
    **Data Limitations:**
    This feed exclusively visualizes reports containing publicly accessible images. Reports submitted via the internal web portal are excluded as their images are password-protected.
    """)
