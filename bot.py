import os
import json
import time
import hmac
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai

# Chargement configuration
load_dotenv()

BINGX_API_KEY = os.getenv("BINGX_API_KEY")
BINGX_SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PROXY_URL = os.getenv("PROXY_URL")

BASE_URL = "https://open-api.bingx.com"
client_ia = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Fichiers
CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"
POSITIONS_FILE = "positions.json"
DASHBOARD_HTML = "index.html"
ASSETS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

def get_signature(secret_key, params_str):
    return hmac.new(secret_key.encode("utf-8"), params_str.encode("utf-8"), hashlib.sha256).hexdigest()

def send_bingx_request(method, path, params={}):
    if not BINGX_API_KEY or not BINGX_SECRET_KEY:
        return {"code": -1, "msg": "API Keys missing"}
        
    params["timestamp"] = int(time.time() * 1000)
    sorted_params = sorted(params.items())
    params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    signature = get_signature(BINGX_SECRET_KEY, params_str)
    url = f"{BASE_URL}{path}?{params_str}&signature={signature}"
    
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    
    try:
        # On n'utilise pas le proxy localement pour éviter les blocages
        response = requests.request(method, url, headers=headers, timeout=15)
        res_json = response.json()
        return res_json
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_market_info(symbol):
    """Récupère prix actuel"""
    res = send_bingx_request("GET", "/openApi/swap/v2/quote/latestPrice", {"symbol": symbol})
    if res.get("code") == 0:
        return float(res["data"]["price"])
    return None

def get_balance():
    res = send_bingx_request("GET", "/openApi/swap/v2/user/balance")
    if res.get("code") == 0:
        data = res.get("data", {})
        # Format spécifique BingX Perpetual V2
        if "balance" in data and isinstance(data["balance"], dict):
            return float(data["balance"].get("balance", 0.0))
        elif isinstance(data, list):
            for item in data:
                if item.get("asset") == "USDT":
                    return float(item.get("balance", 0.0))
    return 0.0

def get_ai_decision(symbol, price, balance):
    if not client_ia: return "WAIT", "IA non configurée"
    
    prompt = f"""
    En tant que Warren v4 (Trading Bot IA), analyse {symbol} au prix de {price} USDT.
    Ton solde actuel est de {balance} USDT.
    Considère la tendance globale.
    Réponds UNIQUEMENT en JSON avec ce format :
    {{"decision": "BUY|SELL|WAIT", "reason": "courte explication", "leverage": 5}}
    """
    
    try:
        response = client_ia.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        # Nettoyage de la réponse IA
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("decision", "WAIT"), data.get("reason", "N/A")
    except Exception as e:
        return "WAIT", f"Erreur IA: {str(e)}"

def update_dashboard(balance, brain_msg):
    """Génère le dashboard HTML basé sur le style v3.5"""
    template = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>WARREN AI v4.0 - BingX</title>
        <style>
            :root {{ --bg: #0a0e14; --card: #151b23; --text: #adbac7; --accent: #58a6ff; --green: #3fb950; --border: #30363d; }}
            body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .accent {{ color: var(--accent); font-weight: bold; font-size: 28px; }}
            .brain {{ border-left: 4px solid var(--accent); padding: 15px; background: #1c2128; font-style: italic; }}
            h1 {{ border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📈 WARREN AI <small style="font-size: 14px; color: #768390;">v4.0 BINGX REAL</small></h1>
            <div class="card">
                <h3 style="margin-top:0; color: #768390; font-size: 12px; text-transform: uppercase;">Solde Portefeuille</h3>
                <p class="accent">{balance:.4f} USDT</p>
            </div>
            <div class="card brain">
                <p><strong>🧠 Pensée de Warren :</strong> {brain_msg}</p>
            </div>
            <div class="card">
                <p style="margin:0; font-size: 12px; color: #768390;">Dernier check : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(template)

def run_cycle():
    print(f"--- Cycle Warren v4.0 (BingX) - {datetime.now()} ---")
    balance = get_balance()
    print(f"Solde : {balance} USDT")
    
    all_decisions = []
    for asset in ASSETS:
        price = get_market_info(asset)
        if price:
            print(f"Analyse {asset} ({price} USDT)...")
            decision, reason = get_ai_decision(asset, price, balance)
            all_decisions.append(f"[{asset}] {decision}: {reason}")
            print(f"  -> {decision}")
        else:
            print(f"Erreur prix pour {asset}")
            
    brain_msg = " | ".join(all_decisions) if all_decisions else "En attente de données..."
    update_dashboard(balance, brain_msg)
    print("Dashboard mis à jour.")

if __name__ == "__main__":
    run_cycle()
