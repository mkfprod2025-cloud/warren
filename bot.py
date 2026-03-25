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
DEBUG_FILE = "debug_api.json"
ASSETS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

def get_signature(secret_key, params_str):
    return hmac.new(secret_key.encode("utf-8"), params_str.encode("utf-8"), hashlib.sha256).hexdigest()

def send_bingx_request(method, path, params={}):
    if not BINGX_API_KEY or not BINGX_SECRET_KEY:
        return {"code": -1, "msg": "ENV_MISSING"}
        
    params["timestamp"] = int(time.time() * 1000)
    sorted_params = sorted(params.items())
    params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    signature = get_signature(BINGX_SECRET_KEY, params_str)
    url = f"{BASE_URL}{path}?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": BINGX_API_KEY}
    
    try:
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        response = requests.request(method, url, headers=headers, proxies=proxies, timeout=15)
        res_json = response.json()
        
        # Log de debug (sans les clés)
        with open(DEBUG_FILE, "w") as f:
            json.dump({
                "path": path,
                "code": res_json.get("code"),
                "msg": res_json.get("msg"),
                "timestamp": datetime.now().isoformat(),
                "has_proxy": bool(PROXY_URL)
            }, f)
            
        return res_json
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def get_market_info(symbol):
    res = send_bingx_request("GET", "/openApi/swap/v2/quote/latestPrice", {"symbol": symbol})
    if res.get("code") == 0:
        return float(res["data"]["price"])
    return None

def get_balance_info():
    res = send_bingx_request("GET", "/openApi/swap/v2/user/balance")
    if res.get("code") == 0:
        data = res.get("data", {})
        if "balance" in data and isinstance(data["balance"], dict):
            b = data["balance"]
            return {"balance": float(b.get("balance", 0.0)), "equity": float(b.get("equity", 0.0)), "status": "OK"}
    
    error_msg = res.get("msg", "ERREUR")
    if error_msg == "ENV_MISSING":
        return {"balance": 0.0, "equity": 0.0, "status": "Clés Cloud Manquantes"}
    return {"balance": 0.0, "equity": 0.0, "status": f"BINGX: {error_msg}"}

def get_active_positions():
    res = send_bingx_request("GET", "/openApi/swap/v2/user/positions")
    positions = []
    if res.get("code") == 0:
        for p in res.get("data", []):
            if float(p.get("positionAmt", 0)) != 0:
                positions.append({
                    "symbol": p["symbol"],
                    "side": "LONG" if float(p["positionAmt"]) > 0 else "SHORT",
                    "entry": float(p["avgPrice"]),
                    "leverage": p["leverage"],
                    "margin": float(p["isolatedMargin"])
                })
    return positions

def get_ai_decision(symbol, price, balance):
    if not client_ia: return "WAIT", "IA non configurée"
    prompt = f"Analyse {symbol} à {price}. Solde: {balance}. Réponds JSON: {{'decision': 'BUY|SELL|WAIT', 'reason': '...'}}"
    try:
        response = client_ia.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        return data.get("decision", "WAIT"), data.get("reason", "N/A")
    except:
        return "WAIT", "Erreur IA"

def update_dashboard(balance, brain_msg, positions, config, wallet_status="OK"):
    pos_html = ""
    if not positions:
        pos_html = "<tr><td colspan='7' style='text-align:center; padding: 30px; color:#768390;'>Aucune position ouverte.</td></tr>"
    for p in positions:
        side_class = "tag-long" if p['side'] == "LONG" else "tag-short"
        pos_html += f"<tr><td>{p['symbol']}</td><td><span class='tag {side_class}'>{p['side']}</span></td><td>{p['entry']}</td><td>x{p['leverage']}</td><td>-</td><td>-</td><td>{p['margin']:.2f} USDT</td></tr>"

    history_html = ""
    try:
        with open(TRADES_FILE, "r") as f:
            history = json.load(f)
            for t in reversed(history[-10:]):
                history_html += f"<tr><td>{t.get('date', '-')}</td><td>{t.get('symbol', '-')}</td><td>{t.get('type', '-')}</td><td>{t.get('price', '-')}</td><td>{t.get('pnl', '0')}%</td></tr>"
    except: pass

    status_class = "status-active" if config.get("bot_running") else "status-stopped"
    status_text = "EN SERVICE" if config.get("bot_running") else "EN PAUSE"
    
    balance_display = f"{balance:.2f} USDT" if wallet_status == "OK" else f"<span style='color:var(--red); font-size:12px;'>{wallet_status}</span>"

    template = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>WARREN AI v4.0 - Pro Terminal</title>
        <style>
            :root {{ --bg: #0a0e14; --card: #151b23; --text: #adbac7; --accent: #58a6ff; --green: #3fb950; --red: #f85149; --border: #30363d; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 15px; font-size: 14px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 15px; }}
            .status-badge {{ padding: 6px 15px; border-radius: 20px; font-weight: bold; font-size: 12px; }}
            .status-active {{ background: rgba(63, 185, 80, 0.15); color: var(--green); border: 1px solid var(--green); }}
            .status-stopped {{ background: rgba(248, 81, 73, 0.15); color: var(--red); border: 1px solid var(--red); }}
            .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 20px; }}
            .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; }}
            .card h3 {{ margin: 0; font-size: 11px; color: #768390; text-transform: uppercase; letter-spacing: 1px; }}
            .card p {{ margin: 8px 0 0; font-size: 20px; font-weight: bold; }}
            .brain {{ margin-top: 20px; background: #1c2128; border-left: 4px solid var(--accent); padding: 15px; border-radius: 4px; font-style: italic; line-height: 1.5; }}
            .main-view {{ display: grid; grid-template-columns: 1fr 350px; gap: 20px; margin-top: 20px; }}
            .table-container {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; overflow-x: auto; }}
            h2 {{ font-size: 16px; margin-top: 0; color: var(--accent); display: flex; align-items: center; gap: 8px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
            th {{ text-align: left; padding: 10px; color: #768390; border-bottom: 2px solid var(--border); }}
            td {{ padding: 10px; border-bottom: 1px solid var(--border); }}
            .history-scroll {{ max-height: 400px; overflow-y: auto; }}
            .console {{ background: #0d1117; border: 1px solid var(--accent); border-radius: 8px; padding: 15px; position: sticky; top: 15px; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
            button {{ padding: 12px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; }}
            .btn-start {{ background: var(--green); color: white; }}
            .btn-stop {{ background: var(--red); color: white; }}
            .btn-update {{ background: var(--accent); color: white; grid-column: span 2; }}
            .tag {{ padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }}
            .tag-long {{ background: rgba(63, 185, 80, 0.2); color: var(--green); }}
            .tag-short {{ background: rgba(248, 81, 73, 0.2); color: var(--red); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 WARREN AI <small style="font-size: 12px; color: #768390;">PRO TERMINAL v4.0 (BingX)</small></h1>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            <div class="grid">
                <div class="card"><h3>Actifs Scan</h3><p>{len(ASSETS)} unités</p></div>
                <div class="card"><h3>Solde USDT</h3><p style="color: var(--green)">{balance_display}</p></div>
                <div class="card"><h3>Objectif</h3><p>{config.get('target_yield', 15.0)}%</p></div>
                <div class="card"><h3>Deadline</h3><p>{config.get('deadline', '-')}</p></div>
            </div>
            <div class="brain">
                <strong style="color:var(--accent); font-style: normal;">🧠 Dernière Analyse :</strong> "{brain_msg}"
            </div>
            <div class="main-view">
                <div class="left-col">
                    <div class="table-container" style="margin-bottom: 20px;">
                        <h2>📍 Positions Actives</h2>
                        <table>
                            <thead><tr><th>Actif</th><th>Action</th><th>Entrée</th><th>Levier</th><th>SL</th><th>TP</th><th>Capital</th></tr></thead>
                            <tbody>{pos_html}</tbody>
                        </table>
                    </div>
                </div>
                <div class="right-col">
                    <div class="console">
                        <h2>🎮 Warren Remote</h2>
                        <div class="btn-group">
                            <button class="btn-start" onclick="alert('Lancer sur GitHub Actions')">DÉMARRER</button>
                            <button class="btn-stop" onclick="alert('Arrêter sur GitHub Actions')">ARRÊTER</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(template)

def run_cycle():
    print(f"--- Cycle Warren v4.0 - {datetime.now()} ---")
    try:
        with open(CONFIG_FILE, "r") as f: config = json.load(f)
    except: config = {}

    wallet = get_balance_info()
    balance = wallet["equity"]
    positions = get_active_positions()
    
    all_decisions = []
    if config.get("bot_running"):
        for asset in ASSETS:
            price = get_market_info(asset)
            if price:
                decision, reason = get_ai_decision(asset, price, balance)
                all_decisions.append(f"[{asset}] {decision}")
    else:
        all_decisions.append("Bot en pause.")

    brain_msg = " | ".join(all_decisions)
    update_dashboard(balance, brain_msg, positions, config, wallet_status=wallet["status"])
    print(f"Cycle terminé, Statut: {wallet['status']}")

if __name__ == "__main__":
    run_cycle()
