import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
import time
from datetime import datetime
from dotenv import load_dotenv

# Chargement local (pour tests locaux)
load_dotenv()

st.set_page_config(page_title="Warren - AI Trading Dashboard", layout="wide", page_icon="📈")

# CONFIGURATION GITHUB (Pour piloter le bot à distance)
GITHUB_REPO = "mkfprod2025-cloud/warren"
GITHUB_FILE = "config.json"
# On cherche le token dans les secrets Streamlit (Cloud) ou le .env (Local)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

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

def save_json_local(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def push_config_to_github(data):
    """Envoie les nouveaux réglages sur GitHub pour que le Bot les applique"""
    if not GITHUB_TOKEN:
        return False, "GITHUB_TOKEN manquant dans les Secrets Streamlit."
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        # On récupère le SHA actuel du fichier sur GitHub
        resp = requests.get(url, headers=headers)
        sha = resp.json().get("sha") if resp.status_code == 200 else None
        
        content = json.dumps(data, indent=4)
        encoded_content = base64.b64encode(content.encode()).decode()
        
        payload = {
            "message": f"Warren App: Update config ({datetime.now().strftime('%H:%M:%S')})",
            "content": encoded_content,
            "branch": "main"
        }
        if sha: payload["sha"] = sha
        
        put_resp = requests.put(url, headers=headers, json=payload)
        if put_resp.status_code in [200, 201]:
            return True, "✅ Succès : Configuration poussée sur GitHub !"
        else:
            return False, f"❌ Erreur GitHub : {put_resp.json().get('message', 'Inconnue')}"
    except Exception as e:
        return False, f"❌ Erreur Connexion : {str(e)}"

# CHARGEMENT DES DONNÉES
config = load_json(CONFIG_FILE, {"bot_running": False, "demo_mode": True, "asset": "BTC/USDT", "target_yield": 12.0, "deadline": "2026-03-21"})
trades = load_json(TRADES_FILE, [])
positions = load_json(POSITIONS_FILE, {})

# --- BARRE LATÉRALE ---
st.sidebar.title("🎮 Warren Control Center")
st.sidebar.markdown("---")

st.sidebar.subheader("📡 Statut du Bot")
bot_active = st.sidebar.toggle("🤖 Bot Actif (GitHub Actions)", value=config.get("bot_running", False))
demo_mode = st.sidebar.toggle("🛡️ Mode DÉMO (Pas d'argent réel)", value=config.get("demo_mode", True))

st.sidebar.subheader("🎯 Objectifs")
asset = st.sidebar.text_input("Actif (ex: BTC/USDT)", value=config.get("asset", "BTC/USDT"))
yield_target = st.sidebar.number_input("Objectif ROI (%)", value=float(config.get("target_yield", 12.0)))
deadline_str = config.get("deadline", "2026-03-21")
try:
    deadline = st.sidebar.date_input("Date Limite", value=datetime.strptime(deadline_str, "%Y-%m-%d"))
except:
    deadline = st.sidebar.date_input("Date Limite")

if st.sidebar.button("🚀 ENVOYER L'ORDRE AU BOT", use_container_width=True):
    new_config = {
        "bot_running": bot_active,
        "demo_mode": demo_mode,
        "asset": asset,
        "target_yield": yield_target,
        "deadline": deadline.strftime("%Y-%m-%d"),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json_local(CONFIG_FILE, new_config)
    
    if GITHUB_TOKEN:
        success, msg = push_config_to_github(new_config)
        if success: st.sidebar.success(msg)
        else: st.sidebar.error(msg)
    else:
        st.sidebar.warning("💾 Sauvegardé localement. Mais GITHUB_TOKEN absent pour piloter le Bot distant.")
    
    time.sleep(1)
    st.rerun()

# --- ZONE PRINCIPALE (DASHBOARD) ---
st.title("📈 Warren - AI Trading Dashboard")
if config.get("demo_mode", True):
    st.warning("⚠️ MODE DÉMO ACTIVÉ - Les ordres ne sont pas réellement exécutés sur BitMart.")

# METRICS
col1, col2, col3, col4 = st.columns(4)
col1.metric("Bot Status", "EN LIGNE" if config.get("bot_running") else "HORS LIGNE", 
            delta="Actif" if config.get("bot_running") else "Inactif")
col2.metric("Actif Suivi", config.get("asset"))
total_pnl = sum([t.get('pnl_net_pct', 0) for t in trades if 'pnl_net_pct' in t])
col3.metric("PNL Global Net", f"{total_pnl:.2f}%", delta=f"{total_pnl:.2f}%")
col4.metric("Positions", len(positions))

# POSITIONS OUVERTES
st.subheader("📍 Positions Actuellement Ouvertes")
if positions:
    pos_df = []
    for asset, data in positions.items():
        pos_df.append({
            "Actif": asset,
            "Sens": "🟢 LONG" if data['action'] == "LONG" else "🔴 SHORT",
            "Entrée": f"{data['entry_price']:.2f}",
            "Levier": f"{data['levier']}x",
            "Date": data['timestamp']
        })
    st.table(pd.DataFrame(pos_df))
else:
    st.info("Aucune position ouverte. Warren analyse les tendances.")

# JOURNAL DE BORD (IA)
st.markdown("---")
st.subheader("📊 Journal des Décisions (Intelligence Artificielle)")
if trades:
    df = pd.DataFrame(trades).sort_values(by="timestamp", ascending=False)
    
    # Colonnes propres pour l'affichage
    cols_to_show = ["timestamp", "action", "price", "levier", "mode", "model_used"]
    cols_to_show = [c for c in cols_to_show if c in df.columns]
    
    st.dataframe(df[cols_to_show], use_container_width=True)
    
    # Zoom sur le dernier raisonnement
    last_trade = df.iloc[0]
    with st.expander(f"🧠 Analyse détaillée du dernier signal ({last_trade.get('action')})"):
        st.write(f"**Modèle utilisé :** {last_trade.get('model_used', 'Gemini Default')}")
        st.markdown(f"> {last_trade.get('raisonnement', 'N/A')}")
else:
    st.info("Warren n'a pas encore pris de décisions.")

# DIAGNOSTIC DES CLÉS (Sécurisé)
with st.expander("🛠 Diagnostic de Sécurité"):
    keys = {
        "BITMART_API_KEY": st.secrets.get("BITMART_API_KEY") or os.getenv("BITMART_API_KEY"),
        "GEMINI_API_KEY": st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"),
        "GITHUB_TOKEN": GITHUB_TOKEN
    }
    for k, v in keys.items():
        st.write(f"{k}: {'✅ OK' if v else '❌ MANQUANT'}")

if st.button("🔄 Actualiser les données"):
    st.rerun()
