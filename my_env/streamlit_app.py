"""
E-commerce Platform Manager — Streamlit UI

A rich interactive dashboard that communicates with the FastAPI environment server.

Run with:
    streamlit run streamlit_app.py
"""

import json

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

# ──────────────────── Page Config ────────────────────
st.set_page_config(
    page_title="E-commerce Platform Manager",
    page_icon="🛒",
    layout="wide",
)

# ──────────────────── Custom CSS ─────────────────────
st.markdown(
    """
<style>
    /* Global font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border: 1px solid #3a3a5c;
        border-radius: 12px;
        padding: 16px;
    }
    div[data-testid="stMetric"] label { color: #a0a0c0 !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #e0e0ff !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────── Session State ──────────────────
if "env_state" not in st.session_state:
    st.session_state.env_state = None
if "reward" not in st.session_state:
    st.session_state.reward = 0.0
if "history" not in st.session_state:
    st.session_state.history = []

# ──────────────────── Header ─────────────────────────
st.title("🛒 E-commerce Platform Manager")
st.caption("Maximize profit & customer satisfaction through strategic decisions.")

# ──────────────────── Sidebar: Controls ──────────────
with st.sidebar:
    st.header("⚙️ Controls")

    col_r, col_s = st.columns(2)
    with col_r:
        reset_btn = st.button("🔄 Reset", use_container_width=True)
    with col_s:
        state_btn = st.button("📊 Get State", use_container_width=True)

    if reset_btn:
        try:
            resp = requests.post(f"{API_BASE}/reset", timeout=10)
            data = resp.json()
            obs = data.get("observation", data)
            st.session_state.env_state = obs
            st.session_state.reward = data.get("reward", 0.0)
            st.session_state.history = []
            st.success("Environment reset!")
        except Exception as exc:
            st.error(f"Reset failed: {exc}")

    if state_btn:
        try:
            resp = requests.get(f"{API_BASE}/state", timeout=10)
            st.session_state.env_state_raw = resp.json()
            st.info("State fetched — see panel below.")
        except Exception as exc:
            st.error(f"Get state failed: {exc}")

    st.divider()
    st.header("📈 Session Stats")
    if st.session_state.history:
        rewards = [h["reward"] for h in st.session_state.history]
        profits = [h["profit"] for h in st.session_state.history]
        st.metric("Total Reward", f"{sum(rewards):.2f}")
        st.metric("Total Profit", f"${sum(profits):,.2f}")
        st.metric("Steps", len(st.session_state.history))

# ──────────────────── Main Area ──────────────────────
if st.session_state.env_state is None:
    st.info("👆 Press **Reset** in the sidebar to start the simulation.")
    st.stop()

obs = st.session_state.env_state

# ── KPI Row ──────────────────────────────────────────
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("📅 Day", obs.get("day", 0))
kpi2.metric("😊 Satisfaction", f"{obs.get('customer_satisfaction', 0):.2%}")
kpi3.metric("💰 Budget", f"${obs.get('budget', 0):,.2f}")
kpi4.metric("📦 Profit (last)", f"${obs.get('profit', 0):,.2f}")
kpi5.metric("🏆 Reward", f"{st.session_state.reward:.2f}")

st.divider()

# ── Product Table ────────────────────────────────────
products = obs.get("products", {})
product_names = list(products.keys())

st.subheader("📦 Product Catalog")

header_cols = st.columns([2, 1, 1, 1, 1, 1])
header_cols[0].markdown("**Product**")
header_cols[1].markdown("**Price**")
header_cols[2].markdown("**Cost**")
header_cols[3].markdown("**Stock**")
header_cols[4].markdown("**Demand**")
header_cols[5].markdown("**Competitor $**")

for name in product_names:
    p = products[name]
    cols = st.columns([2, 1, 1, 1, 1, 1])
    cols[0].write(name)
    cols[1].write(f"${p['price']:,.2f}")
    cols[2].write(f"${p['cost']:,.2f}")

    # Color stock based on level
    stock_val = p["stock"]
    if stock_val == 0:
        cols[3].markdown(f"🔴 **{stock_val}**")
    elif stock_val < 20:
        cols[3].markdown(f"🟡 {stock_val}")
    else:
        cols[3].markdown(f"🟢 {stock_val}")

    cols[4].write(p["demand"])
    cols[5].write(f"${p['competitor_price']:,.2f}")

st.divider()

# ── Action Form ──────────────────────────────────────
st.subheader("🎮 Take Action")

pricing_decisions = {}
inventory_decisions = {}

# Pricing & Inventory per product
for name in product_names:
    col_name, col_pricing, col_restock = st.columns([2, 2, 1])
    with col_name:
        st.markdown(f"**{name}**")
    with col_pricing:
        pricing_decisions[name] = st.selectbox(
            f"Pricing — {name}",
            options=["keep", "increase", "decrease"],
            key=f"pricing_{name}",
            label_visibility="collapsed",
        )
    with col_restock:
        inventory_decisions[name] = st.checkbox(
            "Restock",
            key=f"restock_{name}",
        )

st.markdown("---")

# Marketing
marketing_choice = st.selectbox(
    "📣 Marketing Campaign",
    options=["no_campaign", "run_ads", "influencer"],
    index=0,
)

# Step button
step_btn = st.button("▶️  Step", type="primary", use_container_width=True)

if step_btn:
    action_payload = {
        "pricing": pricing_decisions,
        "inventory": {k: v for k, v in inventory_decisions.items()},
        "marketing": marketing_choice,
    }

    try:
        resp = requests.post(
            f"{API_BASE}/step",
            json=action_payload,
            timeout=10,
        )
        data = resp.json()
        new_obs = data.get("observation", data)
        reward = data.get("reward", 0.0)

        st.session_state.env_state = new_obs
        st.session_state.reward = reward
        st.session_state.history.append(
            {
                "day": new_obs.get("day", 0),
                "reward": reward,
                "profit": new_obs.get("profit", 0.0),
                "satisfaction": new_obs.get("customer_satisfaction", 0.0),
                "budget": new_obs.get("budget", 0.0),
            }
        )

        if data.get("done", False):
            st.warning("🏁 Simulation complete (30 days)! Press Reset to start again.")

        st.rerun()
    except Exception as exc:
        st.error(f"Step failed: {exc}")

# ── History Chart ────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.subheader("📊 Performance Over Time")

    import pandas as pd

    df = pd.DataFrame(st.session_state.history)

    chart_tab1, chart_tab2, chart_tab3 = st.tabs(["Reward", "Profit", "Satisfaction"])
    with chart_tab1:
        st.line_chart(df, x="day", y="reward")
    with chart_tab2:
        st.line_chart(df, x="day", y="profit")
    with chart_tab3:
        st.line_chart(df, x="day", y="satisfaction")

# ── Raw State Panel ──────────────────────────────────
with st.expander("🔍 Raw Environment State"):
    if hasattr(st.session_state, "env_state_raw"):
        st.json(st.session_state.env_state_raw)
    st.json(obs)
