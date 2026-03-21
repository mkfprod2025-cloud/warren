import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Warren - Bot AI Trading", layout="wide")

CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"
POSITIONS_FILE = "positions.json"

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except: pass
    return default

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

config = load_json(CONFIG_FILE, {"bot_running": False, "demo_mode": True, "asset": "BTC/USDT", "target_yield": 5.0, "deadline": "2026-12-31"})
trades = load_json(TRADES_FILE, [])
positions = load_json(POSITIONS_FILE, {})

# BARRE LATÉRALE
st.sidebar.title("🛠 Contrôle Warren")
bot_active = st.sidebar.toggle("🤖 Bot Actif", value=config.get("bot_running", False))
demo_mode = st.sidebar.toggle("🛡️ Mode DÉMO", value=config.get("demo_mode", True))
asset = st.sidebar.text_input("Actif", value=config.get("asset", "BTC/USDT"))
yield_target = st.sidebar.number_input("Objectif (%)", value=float(config.get("target_yield", 5.0)))
deadline = st.sidebar.date_input("Date Limite", value=datetime.strptime(config.get("deadline", "2026-12-31"), "%Y-%m-%d"))

if st.sidebar.button("💾 Sauvegarder Config"):
    config.update({"bot_running": bot_active, "demo_mode": demo_mode, "asset": asset, "target_yield": yield_target, "deadline": deadline.strftime("%Y-%m-%d")})
    save_json(CONFIG_FILE, config)
    st.sidebar.success("Config synchronisée !")
    st.rerun()

# ZONE PRINCIPALE
st.title("💰 Warren - Autonome Trading Bot")
if config.get("demo_mode", True):
    st.warning("⚠️ MODE DÉMO ACTIVÉ")

# METRICS
col1, col2, col3, col4 = st.columns(4)
col1.metric("Statut", "ACTIF" if config.get("bot_running") else "STOPPÉ")
col2.metric("Actif", config.get("asset"))

# Calcul du PNL Global
total_pnl = sum([t.get('pnl_net_pct', 0) for t in trades if 'pnl_net_pct' in t])
col3.metric("PNL Total Net", f"{total_pnl:.2f}%")
col4.metric("Positions", len(positions))

# POSITIONS OUVERTES
st.subheader("📍 Positions Actuellement Ouvertes")
if positions:
    pos_data = []
    for asset, data in positions.items():
        pos_data.append({
            "Actif": asset,
            "Sens": data['action'],
            "Entrée": data['entry_price'],
            "Levier": f"{data['levier']}x",
            "Date": data['timestamp']
        })
    st.table(pd.DataFrame(pos_data))
else:
    st.info("Aucune position ouverte.")

# HISTORIQUE
st.markdown("---")
st.subheader("📊 Historique des Décisions Gemini")
if trades:
    df = pd.DataFrame(trades).sort_values(by="timestamp", ascending=False)
    st.dataframe(df, use_container_width=True)

if st.button("🔄 Rafraîchir"):
    st.rerun()
