import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
from bitmart.api_contract import APIContract

load_dotenv()

# Config
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
BITMART_API_KEY = os.getenv("BITMART_API_KEY")
BITMART_SECRET = os.getenv("BITMART_SECRET")
BITMART_MEMO = os.getenv("BITMART_MEMO")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                pass
    return {"bot_running": False, "demo_mode": True}

def save_trade(trade_data):
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f:
                trades = json.load(f)
        except:
            pass
    trades.append(trade_data)
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=4)

def get_market_data(asset):
    symbol = asset.replace("/", "")
    contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
    
    try:
        # Détails du contrat pour avoir le prix
        details_resp = contract_api.get_details(symbol)
        # Structure: {'code': 1000, 'data': {'symbols': [...]}}
        details = details_resp[0]['data']['symbols'][0]
        
        # Calcul des timestamps pour les 3 derniers jours
        end_time = int(time.time())
        start_time = end_time - (3 * 24 * 60 * 60)
        
        # Bougies 15min
        k15_resp = contract_api.get_kline(symbol, step=15, start_time=start_time, end_time=end_time)
        # Structure: {'code': 1000, 'data': [...]}
        k15 = k15_resp[0]['data']
        
        # Bougies 1h
        k60_resp = contract_api.get_kline(symbol, step=60, start_time=start_time, end_time=end_time)
        k60 = k60_resp[0]['data']
        
        return {
            "price": details['last_price'],
            "index_price": details['index_price'],
            "history_15m": k15[-288:] if isinstance(k15, list) else [],
            "history_1h": k60[-72:] if isinstance(k60, list) else [],
            "high_24h": details.get('high_24h', 'N/A'),
            "low_24h": details.get('low_24h', 'N/A')
        }
    except Exception as e:
        print(f"Erreur data BitMart: {e}")
        return None

POSITIONS_FILE = "positions.json"
FEE_RATE = 0.0006 # 0.06% de frais moyens sur BitMart Futures

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except: pass
    return default

def get_market_data(asset):
    symbol = asset.replace("/", "")
    contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
    
    try:
        # Détails du contrat
        details_resp = contract_api.get_details(symbol)
        details = details_resp[0]['data']['symbols'][0]
        
        # Carnet d'ordres pour le SPREAD
        depth_resp = contract_api.get_depth(symbol, size=5)
        depth = depth_resp[0]['data']
        best_bid = float(depth['buys'][0]['price']) if depth['buys'] else float(details['last_price'])
        best_ask = float(depth['sells'][0]['price']) if depth['sells'] else float(details['last_price'])
        spread = ((best_ask - best_bid) / best_bid) * 100

        # Bougies
        end_time = int(time.time())
        start_time = end_time - (3 * 24 * 60 * 60)
        k15 = contract_api.get_kline(symbol, step=15, start_time=start_time, end_time=end_time)[0]['data']
        k60 = contract_api.get_kline(symbol, step=60, start_time=start_time, end_time=end_time)[0]['data']
        
        return {
            "price": float(details['last_price']),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": spread,
            "history_15m": k15[-288:] if isinstance(k15, list) else [],
            "history_1h": k60[-72:] if isinstance(k60, list) else [],
            "high_24h": details.get('high_24h', 'N/A'),
            "low_24h": details.get('low_24h', 'N/A')
        }
    except Exception as e:
        print(f"Erreur data BitMart: {e}")
        return None

def ask_gemini(asset, config, market_data):
    prompt = f"""
    Tu es Warren, un trader expert en contrats à terme (Futures).
    Actif : {asset}. Objectif : {config['target_yield']}% avant le {config['deadline']}.
    
    DONNÉES MARCHÉ :
    - Prix actuel : {market_data['price']} (Spread: {market_data['spread_pct']:.4f}%)
    - Bid/Ask : {market_data['best_bid']} / {market_data['best_ask']}
    - Haut/Bas 24h : {market_data['high_24h']} / {market_data['low_24h']}
    - Historique 15min (3 derniers jours) : {market_data['history_15m']}
    - Historique 1h (3 derniers jours) : {market_data['history_1h']}
    
    ANALYSE ET DÉCISION :
    Compare les tendances sur 15min et 1h. Identifie les supports/résistances.
    Prends en compte le SPREAD et les FEES (0.06% par ordre) dans ton calcul de rentabilité.
    Réponds EXCLUSIVEMENT sous forme d'un objet JSON valide.
    Structure attendue :
    {{
        "raisonnement": "analyse technique détaillée",
        "action": "LONG", "SHORT", "CLOSE" ou "HOLD",
        "levier": entier entre 1 et 20,
        "pourcentage_capital": entier entre 1 et 100
    }}
    """
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            return json.loads(json_str)
        return json.loads(content)
    except Exception as e:
        print(f"Erreur parsing Gemini: {e}")
        return {"action": "HOLD", "raisonnement": "Erreur technique (parsing JSON IA)"}

def execute(asset, decision, demo_mode, market_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    positions = load_json(POSITIONS_FILE, {})
    
    action = decision['action']
    current_price = market_data['price']
    
    # Prix d'exécution incluant le spread
    exec_price = market_data['best_ask'] if action == "LONG" else market_data['best_bid']
    if action == "CLOSE":
        # On ferme au prix opposé de la position actuelle
        exec_price = market_data['best_bid'] # Simplifié
    
    trade_info = {
        "timestamp": timestamp,
        "action": action,
        "price": exec_price,
        "levier": decision.get('levier', 1),
        "raisonnement": decision['raisonnement'],
        "mode": "DEMO" if demo_mode else "REEL",
        "fees_paid": 0.0
    }

    if action in ["LONG", "SHORT"]:
        # Calcul des frais d'entrée
        trade_info["fees_paid"] = exec_price * FEE_RATE
        positions[asset] = {
            "entry_price": exec_price,
            "action": action,
            "levier": decision['levier'],
            "timestamp": timestamp
        }
        print(f"[{timestamp}] OUVERTURE {action} à {exec_price} (Spread: {market_data['spread_pct']:.4f}%)")
    
    elif action == "CLOSE" and asset in positions:
        pos = positions[asset]
        pnl = 0
        if pos['action'] == "LONG":
            pnl = (exec_price - pos['entry_price']) / pos['entry_price']
        else:
            pnl = (pos['entry_price'] - exec_price) / pos['entry_price']
        
        # PNL Net = (PNL * Levier) - (Frais Entrée + Frais Sortie)
        net_pnl = (pnl * pos['levier']) - (2 * FEE_RATE)
        trade_info["pnl_net_pct"] = net_pnl * 100
        print(f"[{timestamp}] FERMETURE {asset} | PNL NET: {trade_info['pnl_net_pct']:.2f}%")
        del positions[asset]

    save_trade(trade_info)
    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=4)

def run(single_run=False):
    if not single_run:
        print("Warren est en veille...")

    while True:
        config = get_config()
        if not config.get("bot_running", False):
            if single_run: return
            time.sleep(10)
            continue

        data = get_market_data(config["asset"])
        if data:
            decision = ask_gemini(config["asset"], config, data)
            execute(config["asset"], decision, config.get("demo_mode", True), data)

        if single_run:
            break

        time.sleep(300) # Analyse toutes les 5 minutes

if __name__ == "__main__":
    import sys
    # Si on passe l'argument --single-run, le bot ne fait qu'un cycle
    is_single = "--single-run" in sys.argv
    run(single_run=is_single)

