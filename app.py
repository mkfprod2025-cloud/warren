import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration de la page
st.set_page_config(page_title="Warren - Bot AI Trading", layout="wide")

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"bot_running": False, "asset": "BTC/USDT", "target_yield": 5.0, "deadline": "2026-12-31"}

def save_config(config):
    config["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

config = load_config()

# BARRE LATÉRALE - CONTRÔLE
st.sidebar.title("🛠 Panneau de Contrôle")
bot_active = st.sidebar.toggle("🤖 Bot Actif", value=config.get("bot_running", False))

asset = st.sidebar.text_input("Actif (ex: BTC/USDT)", value=config.get("asset", "BTC/USDT"))
yield_target = st.sidebar.number_input("Objectif de Rendement (%)", value=config.get("target_yield", 5.0), step=0.1)
deadline = st.sidebar.date_input("Date Limite", value=datetime.strptime(config.get("deadline", "2026-12-31"), "%Y-%m-%d"))

if st.sidebar.button("💾 Sauvegarder Configuration"):
    new_config = {
        "bot_running": bot_active,
        "asset": asset,
        "target_yield": yield_target,
        "deadline": str(deadline)
    }
    save_config(new_config)
    st.sidebar.success("Configuration mise à jour !")

# ZONE PRINCIPALE - DASHBOARD
st.title("💰 Warren - Autonome Trading Bot")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Statut", "ACTIF" if bot_active else "STOPPÉ")
with col2:
    st.metric("Actif", asset)
with col3:
    st.metric("Objectif", f"{yield_target}%")
with col4:
    st.metric("PNL Actuel", "0.00%", delta="0%")

# Données fictives pour l'instant
st.subheader("📊 Historique des Trades & Raisonnement Gemini")
df_trades = pd.DataFrame(columns=["Date", "Action", "Levier", "PNL", "Raisonnement"])
st.table(df_trades)

# Auto-refresh
time.sleep(1)
if bot_active:
    st.rerun()
