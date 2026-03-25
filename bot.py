import os
import json
import time
import hmac
import hashlib
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Configuration BingX & IA
BINGX_API_KEY = os.getenv("BINGX_API_KEY")
BINGX_SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
PROXY_URL = os.getenv("PROXY_URL") # Ton serveur static gratuit

BASE_URL = "https://open-api.bingx.com"
client_ia = genai.Client(api_key=GENAI_API_KEY)

# Fichiers de données
CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"
POSITIONS_FILE = "positions.json"
DASHBOARD_HTML = "index.html"

def get_signature(secret_key, params_str):
    return hmac.new(secret_key.encode("utf-8"), params_str.encode("utf-8"), hashlib.sha256).hexdigest()

def send_bingx_request(method, path, params={}):
    params["timestamp"] = int(time.time() * 1000)
    sorted_params = sorted(params.items())
    params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    signature = get_signature(BINGX_SECRET_KEY, params_str)
    url = f"{BASE_URL}{path}?{params_str}&signature={signature}"
    
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    
    try:
        response = requests.request(method, url, headers=headers, proxies=proxies, timeout=10)
        return response.json()
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_balance():
    """Récupère le solde USDT sur BingX Perpetual V2"""
    res = send_bingx_request("GET", "/openApi/swap/v2/user/balance")
    if res.get("code") == 0:
        for item in res.get("data", []):
            if item.get("asset") == "USDT":
                return float(item.get("balance", 0.0))
    return 0.0

def run_cycle():
    print(f"--- Cycle Warren v4.0 (BingX) - {datetime.now()} ---")
    balance = get_balance()
    print(f"Solde détecté : {balance} USDT")
    
    # Génération Dashboard ultra-minimal pour le premier test
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(f"<h1>Warren v4.0 (BingX)</h1><p>Solde: {balance} USDT</p><p>Dernier check: {datetime.now()}</p>")

if __name__ == "__main__":
    run_cycle()
