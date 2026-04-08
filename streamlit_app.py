"""
E-commerce Platform Manager — Streamlit UI

A rich interactive dashboard that communicates with the FastAPI environment server.

Run with:
    streamlit run streamlit_app.py
"""

import json
import requests
import streamlit as st
import pandas as pd

API_BASE = "http://localhost:7860"

# ──────────────────── Page Config ────────────────────
st.set_page_config(
    page_title="E-commerce Platform Manager",
    page_icon="🛒",
    layout="wide",
)

# ──────────────────── Session State ──────────────────
if "env_state" not in st.session_state:
    st.session_state.env_state = None
if "reward" not in st.session_state:
    st.session_state.reward = 0.0
if "history" not in st.session_state:
    st.session_state.history = []
if "has_reset" not in st.session_state:
    st.session_state.has_reset = False

# ──────────────────── Section 1: Welcome / Instructions ─────────────────────────
expander_open = not st.session_state.has_reset
with st.expander("📖 How to Play (Instructions)", expanded=expander_open):
    st.markdown("""
🎯 **Goal:** Maximize your total reward over 30 days by making smart daily decisions.

📦 **Each day you decide for each product:**
  • Price: Increase (+$20, less demand) | Keep | Decrease (-$20, more demand)
  • Restock: Buy 30 more units (costs money upfront)

📣 **And one marketing campaign:**
  • Run Ads ($200) — boosts demand this day only
  • Influencer ($350) — boosts customer satisfaction
  • No Campaign — save money

💡 **Tips:**
  • Watch competitor prices — if you're 15%+ above them, satisfaction drops
  • Stockouts (0 inventory when demand exists) hurt satisfaction
  • Holding unsold inventory costs $0.50/unit/day
  • Budget is finite — don't overspend on restocking!

🏆 **Reward formula:**
  Reward = (profit / max_possible × 100) + (satisfaction × 20) − (stockout_rate × 30) + (budget_health × 10)
    """)

# ──────────────────── Sidebar controls ──────────────
with st.sidebar:
    st.header("⚙️ Game Controls")
    
    if st.button("🔄 Reset / Start New Game", use_container_width=True, type="primary"):
        try:
            resp = requests.post(f"{API_BASE}/reset", timeout=10)
            data = resp.json()
            obs = data.get("observation", data)
            st.session_state.env_state = obs
            st.session_state.reward = data.get("reward", 0.0)
            st.session_state.history = []
            st.session_state.has_reset = True
            st.rerun()
        except Exception as exc:
            st.error(f"Reset failed: {exc}")

if not st.session_state.has_reset or st.session_state.env_state is None:
    st.info("👆 Press **Reset / Start New Game** in the sidebar to start the simulation.")
    st.stop()

obs = st.session_state.env_state
products = obs.get("products", {})
product_names = list(products.keys())

done = obs.get("done", False)

# ── Episode End Screen ──────────────────────────────────
if done:
    total_reward = sum(h["reward"] for h in st.session_state.history) + st.session_state.reward
    total_profit = sum(h["profit"] for h in st.session_state.history) + obs.get('profit', 0)
    total_revenue = sum(h["revenue"] for h in st.session_state.history) + obs.get('revenue', 0)
    avg_satisfaction = sum(h["satisfaction"] for h in st.session_state.history) / max(1, len(st.session_state.history))

    if total_reward > 2000:
        tier, color, bg = "Elite Manager 👑", "green", "st.success"
    elif total_reward > 1000:
        tier, color, bg = "Good Manager 🌟", "blue", "st.info"
    elif total_reward > 0:
        tier, color, bg = "Average Manager 😐", "orange", "st.warning"
    else:
        tier, color, bg = "Poor Manager 📉", "red", "st.error"
        
    st.markdown("---")
    st.markdown(f"### 🏁 Simulation Complete (Day 30)")
    
    if bg == "st.success":
        st.success(f"**Final Tier:** {tier}")
    elif bg == "st.info":
        st.info(f"**Final Tier:** {tier}")
    elif bg == "st.warning":
        st.warning(f"**Final Tier:** {tier}")
    else:
        st.error(f"**Final Tier:** {tier}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Reward", f"{total_reward:.2f}")
    col2.metric("Total Profit", f"${total_profit:,.2f}")
    col3.metric("Total Revenue", f"${total_revenue:,.2f}")
    col4.metric("Avg Satisfaction", f"{avg_satisfaction:.2%}")
    
    if st.button("🔄 Play Again", use_container_width=True, type="primary", key="replay_bottom"):
        try:
            resp = requests.post(f"{API_BASE}/reset", timeout=10)
            data = resp.json()
            st.session_state.env_state = data.get("observation", data)
            st.session_state.reward = data.get("reward", 0.0)
            st.session_state.history = []
            st.session_state.has_reset = True
            st.rerun()
        except Exception as exc:
            st.error(f"Reset failed: {exc}")

    st.markdown("---")

# ──────────────────── Section 2: KPI Row ─────────────────────────
last_profit = obs.get('profit', 0)
prev_profit = 0
if st.session_state.history:
    prev_profit = st.session_state.history[-1]['profit']
profit_delta = last_profit - prev_profit

cumulative_reward = sum(h["reward"] for h in st.session_state.history) + st.session_state.reward

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("📅 Day", obs.get("day", 0))
kpi2.metric("💰 Budget", f"${obs.get('budget', 0):,.2f}")
kpi3.metric("😊 Satisfaction", f"{obs.get('customer_satisfaction', 0):.2%}")
kpi4.metric("📦 Last Profit", f"${last_profit:,.2f}", delta=f"${profit_delta:,.2f}")
kpi5.metric("📈 Last Revenue", f"${obs.get('revenue', 0):,.2f}")
kpi6.metric("🏆 Cumulative Reward", f"{cumulative_reward:.2f}")

st.divider()

if not done:
    main_col1, main_col2 = st.columns([1.5, 1])

    # ──────────────────── Section 3: Product Dashboard ─────────────────────────
    with main_col1:
        st.subheader("📦 Product Dashboard")
        
        grid_cols = st.columns(2)
        
        for idx, (name, p) in enumerate(products.items()):
            col = grid_cols[idx % 2]
            with col:
                with st.container(border=True):
                    st.markdown(f"### {name}")
                    
                    gap = (p['price'] - p['competitor_price']) / max(0.01, p['competitor_price'])
                    if gap > 0.15:
                        comp_status = f"⚠ +{gap:.0%} above competitor"
                    else:
                        comp_status = "✓ Competitive"
                    st.markdown(f"**Price:** ${p['price']:.2f} ({comp_status})")
                    
                    st.markdown(f"**Last Profit:** ${p.get('profit_last_step', 0):.2f}")
                    st.markdown(f"**Estimated Demand:** {p['demand']}")
                    
                    stock = p['stock']
                    stock_color = "red" if stock < 20 else "orange" if stock < 50 else "green"
                    st.progress(max(0.0, min(1.0, stock / 100.0)))
                    msg = f"<span style='color:{stock_color}'>**Stock: {stock}**</span>"
                    st.markdown(msg, unsafe_allow_html=True)

    # ──────────────────── Section 4: Action Panel ─────────────────────────
    with main_col2:
        st.subheader(f"📋 Day {obs.get('day', 0) + 1} Decisions")
        
        strategy_alerts = []
        if any(p['stock'] < 20 for p in products.values()):
            low_stock_prods = [name for name, p in products.items() if p['stock'] < 20]
            strategy_alerts.append(f"⚠ **{', '.join(low_stock_prods)}** running low — consider restocking")
        if obs.get('budget', 0) < 2000:
            strategy_alerts.append("⚠ **Budget is low** — avoid expensive restocking")
        if obs.get('customer_satisfaction', 0) < 0.7:
            strategy_alerts.append("⚠ **Satisfaction dropping** — run influencer campaign")
        
        if strategy_alerts:
            st.info("💡 **Quick Strategy**\n\n" + "\n\n".join(strategy_alerts))
        
        with st.form("action_form"):
            st.markdown("#### Pricing & Restock")
            
            pricing_decisions = {}
            inventory_decisions = {}
            
            for name in product_names:
                p = products[name]
                st.markdown(f"**{name}** (Price: ${p['price']}, Stock: {p['stock']})")
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    pricing_decisions[name] = st.radio(
                        f"Price - {name}", 
                        ["keep", "increase", "decrease"],
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"p_{name}"
                    )
                with c2:
                    inventory_decisions[name] = st.checkbox("Restock", key=f"r_{name}")
            
            st.markdown("#### Marketing")
            marketing_choice = st.radio(
                "Campaign",
                options=["no_campaign", "run_ads", "influencer"],
                captions=["Save money", "Boost demand ($200)", "Boost satisfaction ($350)"],
                label_visibility="collapsed"
            )
            
            submit = st.form_submit_button("▶️ Execute Day", type="primary", use_container_width=True)
            
            if submit:
                action_payload = {
                    "pricing": pricing_decisions,
                    "inventory": inventory_decisions,
                    "marketing": marketing_choice,
                }
                
                try:
                    # Save a snapshot of the current state BEFORE applying the next action to the history array
                    st.session_state.history.append({
                        "day": obs.get("day", 0),
                        "reward": st.session_state.reward,
                        "profit": obs.get("profit", 0.0),
                        "revenue": obs.get("revenue", 0.0),
                        "satisfaction": obs.get("customer_satisfaction", 0.0),
                        "budget": obs.get("budget", 0.0),
                        "marketing": marketing_choice,
                        "stock_per_product": {n: p["stock"] for n, p in products.items()},
                    })
                
                    resp = requests.post(f"{API_BASE}/step", json=action_payload, timeout=10)
                    data = resp.json()
                    new_obs = data.get("observation", data)
                    
                    st.session_state.env_state = new_obs
                    st.session_state.reward = data.get("reward", 0.0)
                    
                    st.rerun()
                except Exception as exc:
                    st.error(f"Step failed: {exc}")

# ──────────────────── Section 5: Performance Charts ─────────────────────────
if st.session_state.history:
    st.divider()
    st.subheader("📊 Performance Charts")
    
    df = pd.DataFrame(st.session_state.history)
    
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Financials", "Satisfaction & Marketing", "Products"])
    
    with tab1:
        st.line_chart(df, x="day", y=["reward", "profit"])
        
    with tab2:
        st.line_chart(df, x="day", y="budget")
        st.bar_chart(df, x="day", y=["revenue", "profit"])
        
    with tab3:
        st.line_chart(df, x="day", y="satisfaction")
        
    with tab4:
        stock_data = []
        for h in st.session_state.history:
            row = {"day": h["day"]}
            row.update(h.get("stock_per_product", {}))
            stock_data.append(row)
        
        if stock_data:
            df_stock = pd.DataFrame(stock_data)
            st.line_chart(df_stock, x="day", y=list(product_names))
