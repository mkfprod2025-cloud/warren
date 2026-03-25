import os
import json
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from bitmart.api_contract import APIContract

load_dotenv()

# Configuration
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
BITMART_API_KEY = os.getenv("BITMART_API_KEY")
BITMART_SECRET = os.getenv("BITMART_SECRET")
BITMART_MEMO = os.getenv("BITMART_MEMO")

client = genai.Client(api_key=GENAI_API_KEY)

# Modèles IA (Vérifiés 25/03/2026)
MODELS_PRIORITY = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.1-pro-preview"]

CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"
POSITIONS_FILE = "positions.json"
DASHBOARD_HTML = "index.html"
DASHBOARD_MD = "DASHBOARD.md"
FEE_RATE = 0.0006 

# Liste d'actifs pour le Multi-Trading USD-M
ASSETS_TO_WATCH = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

def get_config():
    default = {"bot_running": False, "demo_mode": False, "asset": "BTC/USDT", "target_yield": 15.0, "deadline": "2026-04-01", "macro_info": "RÉEL USD-M", "pnl_reset_date": "2026-03-25 00:00:00"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return default

def save_config(config):
    with open(CONFIG_FILE, "w") as f: json.dump(config, f, indent=4)

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: 
                content = f.read().strip()
                return json.loads(content) if content else default
        except: pass
    return default

def get_wallet_balance():
    """Récupère le solde USDT réel sur BitMart USD-M (Contrats à terme)"""
    try:
        contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
        res = contract_api.get_assets_detail()
        if res and 'data' in res[0]:
            for asset in res[0]['data']:
                if asset.get('currency') == "USDT":
                    return float(asset.get('available_balance', 0.0))
    except Exception as e:
        print(f"Erreur balance USD-M: {e}")
    return 0.0

def check_auto_close(asset, positions, market_data):
    """Vérifie si une position doit être fermée via TP ou SL (v3.5.5)"""
    if asset not in positions: return None
    pos = positions[asset]
    price = market_data['price']
    action = pos['action']
    sl = pos.get('sl')
    tp = pos.get('tp')
    
    reason = None
    if action == "LONG":
        if sl and price <= sl: reason = f"Stop Loss atteint ({price} <= {sl})"
        if tp and price >= tp: reason = f"Take Profit atteint ({price} >= {tp})"
    elif action == "SHORT":
        if sl and price >= sl: reason = f"Stop Loss atteint ({price} >= {sl})"
        if tp and price <= tp: reason = f"Take Profit atteint ({price} <= {tp})"
    
    if reason:
        return {"action": "CLOSE", "raisonnement": f"AUTO-CLOSE USD-M: {reason}", "asset": asset}
    return None

def generate_dashboards(config, trades, positions, last_decision):
    """Génère le Dashboard Pro v3.5.5 (RÉEL USD-M)"""
    status_class = "status-active" if config.get("bot_running") else "status-stopped"
    status_text = "OPÉRATIONNEL" if config.get("bot_running") else "EN PAUSE"
    mode_text = "DÉMO" if config.get("demo_mode") else "RÉEL"
    
    reset_date = config.get("pnl_reset_date", "2000-01-01 00:00:00")
    relevant_trades = [t for t in trades if t.get('timestamp', '0') >= reset_date]
    total_pnl = sum([t.get('pnl_net_pct', 0) for t in relevant_trades if 'pnl_net_pct' in t])
    wallet_balance = get_wallet_balance()

    # HTML Generator (v3.5.5)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WARREN AI v3.5.5 - USD-M</title>
        <meta http-equiv="refresh" content="3600">
        <style>
            :root {{ --bg: #0a0e14; --card: #151b23; --text: #adbac7; --accent: #58a6ff; --green: #3fb950; --red: #f85149; --border: #30363d; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 15px; font-size: 14px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 15px; }}
            .status-badge {{ padding: 6px 15px; border-radius: 20px; font-weight: bold; font-size: 12px; }}
            .status-active {{ background: rgba(63, 185, 80, 0.15); color: var(--green); border: 1px solid var(--green); }}
            .status-stopped {{ background: rgba(248, 81, 73, 0.15); color: var(--red); border: 1px solid var(--red); }}
            .mode-badge {{ margin-left: 10px; font-size: 10px; background: {'#f85149' if not config.get('demo_mode') else '#30363d'}; padding: 2px 8px; border-radius: 4px; }}
            .grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 20px; }}
            .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; }}
            .card h3 {{ margin: 0; font-size: 11px; color: #768390; text-transform: uppercase; }}
            .card p {{ margin: 8px 0 0; font-size: 18px; font-weight: bold; }}
            .brain {{ margin-top: 20px; background: #1c2128; border-left: 4px solid var(--accent); padding: 15px; border-radius: 4px; font-style: italic; }}
            .table-container {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 15px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
            th {{ text-align: left; padding: 10px; color: #768390; border-bottom: 2px solid var(--border); }}
            td {{ padding: 10px; border-bottom: 1px solid var(--border); }}
            .tag {{ padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }}
            .tag-long {{ background: rgba(63, 185, 80, 0.2); color: var(--green); }}
            .tag-short {{ background: rgba(248, 81, 73, 0.2); color: var(--red); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 WARREN AI <small style="font-size: 12px; color: #768390;">PRO v3.5.5</small> <span class="mode-badge">{mode_text}</span></h1>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            <div class="grid">
                <div class="card"><h3>Solde USD-M</h3><p style="color:var(--accent)">{wallet_balance:.2f} USDT</p></div>
                <div class="card"><h3>Session PNL</h3><p style="color: {'var(--green)' if total_pnl >=0 else 'var(--red)'}">{total_pnl:.2f}%</p></div>
                <div class="card"><h3>Scan Multi</h3><p>{len(ASSETS_TO_WATCH)} actifs</p></div>
                <div class="card"><h3>Objectif</h3><p>{config.get('target_yield')}%</p></div>
                <div class="card"><h3>Reset PNL</h3><p style="font-size: 11px;">{reset_date}</p></div>
            </div>
            <div class="brain">
                <strong style="color:var(--accent)">🧠 Analyse USD-M ({last_decision.get('asset', 'N/A')}) :</strong> "{last_decision.get('raisonnement', 'Cycle en cours...')}"
            </div>
            <div class="table-container">
                <h2>📍 Positions Actives USD-M</h2>
                <table>
                    <thead><tr><th>Actif</th><th>Action</th><th>Entrée</th><th>Levier</th><th>SL</th><th>TP</th><th>Capital</th></tr></thead>
                    <tbody>
    """
    for asset, data in positions.items():
        tag = "tag-long" if data.get('action') == "LONG" else "tag-short"
        html_content += f"""<tr><td><strong>{asset}</strong></td><td><span class="tag {tag}">{data.get('action','-')}</span></td><td>{data.get('entry_price','-')}</td><td>{data.get('levier','-')}x</td><td>{data.get('sl','-')}</td><td>{data.get('tp','-')}</td><td>{data.get('capital_pct','-')}%</td></tr>"""
    if not positions: html_content += "<tr><td colspan='7' style='text-align:center; padding: 20px;'>Aucune position ouverte.</td></tr>"
    html_content += "</tbody></table></div></div></body></html>"
    
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f: f.write(html_content)
    
    md_content = f"# 📈 WARREN AI STATUS (v3.5.5)\n**Mode :** {mode_text} | **PNL :** {total_pnl:.2f}% | **Solde USD-M :** {wallet_balance:.2f} USDT\n\n### 🧠 Analyse USD-M ({last_decision.get('asset', 'N/A')})\n> {last_decision.get('raisonnement', 'N/A')}\n"
    with open(DASHBOARD_MD, "w", encoding="utf-8") as f: f.write(md_content)

def ask_gemini_pro(asset, config, market_data):
    trades = load_json(TRADES_FILE, [])
    reset_date = config.get("pnl_reset_date", "2000-01-01 00:00:00")
    relevant_trades = [t for t in trades if t.get('timestamp', '0') >= reset_date]
    total_pnl = sum([t.get('pnl_net_pct', 0) for t in relevant_trades if 'pnl_net_pct' in t])
    
    price = market_data['price']
    prompt = f"Tu es Warren, trader expert USD-M BitMart. Actif: {asset}. Prix: {price}. Objectif: {config['target_yield']}%. PNL: {total_pnl:.2f}%. Analyse et réponds en JSON: raisonnement, action (LONG/SHORT/CLOSE/HOLD), levier (1-20), sl, tp, pourcentage_capital (1-100)."
    
    for model_id in MODELS_PRIORITY:
        try:
            response = client.models.generate_content(model=model_id, contents=prompt, config={"response_mime_type": "application/json"})
            decision = response.parsed if response.parsed else json.loads(response.text)
            decision['model_used'] = model_id
            decision['asset'] = asset
            return decision
        except: continue
    return {"action": "HOLD", "raisonnement": "Saturation IA.", "asset": asset}

def execute(asset, decision, market_data, demo_mode=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    positions = load_json(POSITIONS_FILE, {})
    trades = load_json(TRADES_FILE, [])
    action = decision['action']
    price = market_data['price']
    
    trade_info = { "timestamp": timestamp, "asset": asset, "action": action, "price": price, "mode": "RÉEL" if not demo_mode else "DÉMO" }

    if not demo_mode and action != "HOLD":
        try:
            contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
            symbol = asset.replace("/", "")
            levier = str(min(int(decision.get('levier', 1)), 20))
            
            # Appliquer Levier & Mode Isolé
            contract_api.post_submit_leverage(symbol, leverage=levier, open_type="isolated")
            
            balance = get_wallet_balance()
            capital_usdt = balance * (decision.get('pourcentage_capital', 5) / 100)
            size = int((capital_usdt * int(levier)) / price)
            
            if size > 0:
                side = 1 if action == "LONG" else (2 if action == "SHORT" else (3 if action == "CLOSE" and positions.get(asset,{}).get('action')=="LONG" else 4))
                res = contract_api.post_submit_order(symbol, side=side, type="market", size=size)
                trade_info["bitmart_order_id"] = str(res[0].get('data', {}).get('order_id', 'ERR'))
        except Exception as e:
            trade_info["error"] = str(e)

    if action in ["LONG", "SHORT"]:
        positions[asset] = { "entry_price": price, "action": action, "levier": decision.get('levier', 1), "sl": decision.get('sl'), "tp": decision.get('tp'), "capital_pct": decision.get('pourcentage_capital', 5), "timestamp": timestamp }
    elif action == "CLOSE" and asset in positions:
        pos = positions[asset]
        pnl = (price - pos['entry_price'])/pos['entry_price'] if pos['action']=="LONG" else (pos['entry_price'] - price)/pos['entry_price']
        trade_info["pnl_net_pct"] = (pnl * pos.get('levier', 1) - (2 * FEE_RATE)) * 100
        del positions[asset]
        
    trades.append(trade_info)
    save_json(POSITIONS_FILE, positions)
    save_json(TRADES_FILE, trades)
    return trade_info

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=4)

def get_market_data(asset):
    symbol = asset.replace("/", "")
    contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
    try:
        res = contract_api.get_details(symbol)
        if not res or 'data' not in res[0]: return None
        details = res[0]['data']['symbols'][0]
        return {"price": float(details['last_price'])}
    except: return None

def run_cycle():
    config = get_config()
    if not config.get("bot_running"): return
    
    positions = load_json(POSITIONS_FILE, {})
    trades = load_json(TRADES_FILE, [])
    
    assets = list(set([config["asset"]] + ASSETS_TO_WATCH))
    for asset in assets:
        market = get_market_data(asset)
        if market:
            decision = check_auto_close(asset, positions, market)
            if not decision: decision = ask_gemini_pro(asset, config, market)
            if decision['action'] != "HOLD":
                execute(asset, decision, market, demo_mode=config.get("demo_mode", False))
        time.sleep(2)
    generate_dashboards(config, trades, positions, {"raisonnement": "Cycle USD-M complété."})

if __name__ == "__main__":
    run_cycle()
