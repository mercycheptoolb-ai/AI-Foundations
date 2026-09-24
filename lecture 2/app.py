import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Lease Noir", page_icon="🖤", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
.stApp { background: #09070b; color: #f8eef7; font-family: 'Space Grotesk', sans-serif; }
[data-testid='stMetric'] { background: #17101a; border: 1px solid #ff2b91; border-radius: 16px; padding: 14px; }
h1 { color: #ff2b91; } h2, h3 { color: #ffd6ed; }
.doll { text-align:center; font-size:100px; filter: drop-shadow(0 0 18px #ff2b91); }
.card { background:#17101a; border:1px solid #512143; border-radius:18px; padding:18px; }
</style>""", unsafe_allow_html=True)

ROOT = Path(__file__).parent
DATA = ROOT / "leases.json"
st.title("LEASE NOIR")
st.caption("A black + pink lease intelligence dashboard")
if not DATA.exists():
    st.warning("No leases.json yet. Add PORTKEY_API_KEY to ../.env and run: python extract_leases.py")
    st.markdown('<div class="card"><div class="doll">🖤🩷</div><h3 style="text-align:center">Your lease bestie is waiting</h3></div>', unsafe_allow_html=True)
    st.stop()

records = json.loads(DATA.read_text(encoding="utf-8")).get("leases", [])
df = pd.DataFrame(records)
rent = pd.to_numeric(df.get("annual_base_rent"), errors="coerce").fillna(0)
c1, c2, c3 = st.columns(3)
c1.metric("Properties", len(df)); c2.metric("Annual base rent", f"${rent.sum():,.0f}"); c3.metric("Avg. escalation", f"{pd.to_numeric(df.get('annual_escalation_pct'), errors='coerce').mean():.1f}%")
left, right = st.columns([1.45, 1])
with left:
    st.subheader("Annual cash flow")
    chart = px.bar(df.assign(annual_rent=rent), x="property_name", y="annual_rent", color_discrete_sequence=["#ff2b91"])
    chart.update_layout(paper_bgcolor="#09070b", plot_bgcolor="#09070b", font_color="#f8eef7", xaxis_title="", yaxis_title="USD")
    st.plotly_chart(chart, use_container_width=True)
with right:
    st.subheader("Property map")
    # The lease extraction may not return coordinates. Keep the map useful by
    # placing records at their extracted city until exact geocoding is added.
    city_centers = {
        "New Haven": (41.3083, -72.9279),
        "Hamden": (41.3959, -72.8968),
        "Milford": (41.2307, -73.0640),
        "Branford": (41.2795, -72.8151),
    }
    map_df = df.copy()
    map_df["lat"] = pd.to_numeric(map_df.get("latitude"), errors="coerce")
    map_df["lon"] = pd.to_numeric(map_df.get("longitude"), errors="coerce")
    map_df["city_clean"] = map_df["city"].fillna("").astype(str).str.strip()
    for city, (lat, lon) in city_centers.items():
        mask = map_df["city_clean"].str.lower().eq(city.lower()) & (map_df["lat"].isna() | map_df["lon"].isna())
        map_df.loc[mask, ["lat", "lon"]] = lat, lon
    points = map_df.dropna(subset=["lat", "lon"]).copy()
    points["lat"] = points["lat"].astype(float)
    points["lon"] = points["lon"].astype(float)
    layer = pdk.Layer(
        "ScatterplotLayer", data=points, get_position="[lon, lat]",
        get_radius=850, get_fill_color=[255, 43, 145, 220],
        get_line_color=[255, 214, 237], line_width_min_pixels=2, pickable=True,
    )
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=pdk.ViewState(latitude=41.3083, longitude=-72.9279, zoom=10.5),
        tooltip={"text": "{property_name}\n{address}"}, map_style=None,
    ), use_container_width=True)
    st.caption(f"{len(points)} lease markers shown. Map is centered on New Haven; city-level markers fill missing exact coordinates.")
    st.markdown('<div class="doll">🧸</div>', unsafe_allow_html=True)
st.subheader("Lease records")
st.dataframe(df, use_container_width=True, hide_index=True)
