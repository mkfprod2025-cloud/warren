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

# Modèles IA (Vérifiés 23/03/2026)
MODELS_PRIORITY = ["gemini-3.1-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"]

CONFIG_FILE = "config.json"
TRADES_FILE = "trades_history.json"
POSITIONS_FILE = "positions.json"
DASHBOARD_HTML = "index.html"
DASHBOARD_MD = "DASHBOARD.md"
FEE_RATE = 0.0006 

# Liste d'actifs pour le Multi-Trading
ASSETS_TO_WATCH = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

def get_config():
    default = {"bot_running": False, "demo_mode": True, "asset": "BTC/USDT", "target_yield": 15.0, "deadline": "2026-03-24", "macro_info": ""}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return default

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: 
                content = f.read().strip()
                return json.loads(content) if content else default
        except: pass
    return default

def generate_dashboards(config, trades, positions, last_decision):
    """Génère le Dashboard HTML5 Pro-View (v3.5)"""
    status_class = "status-active" if config.get("bot_running") else "status-stopped"
    status_text = "OPÉRATIONNEL" if config.get("bot_running") else "EN PAUSE"
    total_pnl = sum([t.get('pnl_net_pct', 0) for t in trades if 'pnl_net_pct' in t])
    
    # 1. GÉNÉRATION HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WARREN AI - Pro Terminal</title>
        <style>
            :root {{ --bg: #0a0e14; --card: #151b23; --text: #adbac7; --accent: #58a6ff; --green: #3fb950; --red: #f85149; --border: #30363d; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 15px; font-size: 14px; }}
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
            .form-group {{ margin-bottom: 12px; }}
            label {{ display: block; font-size: 11px; color: #768390; margin-bottom: 5px; }}
            input, select, textarea {{ width: 100%; background: #1c2128; border: 1px solid var(--border); color: white; padding: 10px; border-radius: 6px; box-sizing: border-box; }}
            .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px; }}
            button {{ padding: 12px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; transition: 0.2s; }}
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
                <h1>📈 WARREN AI <small style="font-size: 12px; color: #768390; font-weight: normal;">PRO TERMINAL v3.5</small></h1>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            <div class="grid">
                <div class="card"><h3>Actifs Scan</h3><p>{len(ASSETS_TO_WATCH)} unités</p></div>
                <div class="card"><h3>PNL Global</h3><p style="color: {'var(--green)' if total_pnl >=0 else 'var(--red)'}">{total_pnl:.2f}%</p></div>
                <div class="card"><h3>Objectif</h3><p>{config.get('target_yield')}%</p></div>
                <div class="card"><h3>Deadline</h3><p style="font-size: 16px;">{config.get('deadline')}</p></div>
            </div>
            <div class="brain">
                <strong style="color:var(--accent); font-style: normal;">🧠 Dernière Analyse ({last_decision.get('asset', 'N/A')}) :</strong> "{last_decision.get('raisonnement', 'En attente de cycle...')}"
            </div>
            <div class="main-view">
                <div class="left-col">
                    <div class="table-container" style="margin-bottom: 20px;">
                        <h2>📍 Positions Actives</h2>
                        <table>
                            <thead><tr><th>Actif</th><th>Action</th><th>Entrée</th><th>Levier</th><th>SL</th><th>TP</th><th>Capital</th></tr></thead>
                            <tbody>
    """
    for asset, data in positions.items():
        tag = "tag-long" if data['action'] == "LONG" else "tag-short"
        html_content += f"""<tr><td><strong>{asset}</strong></td><td><span class="tag {tag}">{data['action']}</span></td><td>{data['entry_price']}</td><td>{data['levier']}x</td><td style="color:var(--red)">{data.get('sl','-')}</td><td style="color:var(--green)">{data.get('tp','-')}</td><td>{data.get('capital_pct','-')}%</td></tr>"""
    if not positions: html_content += "<tr><td colspan='7' style='text-align:center; padding: 30px; color:#768390;'>Aucune position ouverte.</td></tr>"
    html_content += """
                            </tbody>
                        </table>
                    </div>
                    <div class="table-container">
                        <h2>📜 Journal des Trades</h2>
                        <div class="history-scroll">
                            <table>
                                <thead><tr><th>Date</th><th>Actif</th><th>Ordre</th><th>Prix</th><th>PNL %</th></tr></thead>
                                <tbody>
    """
    for t in reversed(trades[-50:]):
        pnl = t.get('pnl_net_pct')
        pnl_display = f"<span style='color:{'var(--green)' if pnl >=0 else 'var(--red)'}'>{pnl:+.2f}%</span>" if pnl is not None else "-"
        tag = "tag-long" if t['action'] in ["LONG", "OPEN"] else ("tag-short" if t['action'] in ["SHORT", "SELL"] else "")
        html_content += f"""<tr><td style="color:#768390">{t['timestamp']}</td><td>{t.get('asset', 'BTC/USDT')}</td><td><span class="tag {tag}">{t['action']}</span></td><td>{t['price']}</td><td><strong>{pnl_display}</strong></td></tr>"""
    html_content += f"""
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="right-col">
                    <div class="console">
                        <h2>🎮 Warren Remote</h2>
                        <div class="form-group"><label>Instruction Macro</label><textarea id="macro" rows="3">{config.get('macro_info', '')}</textarea></div>
                        <div class="form-group"><label>Focus Actif</label><input type="text" id="asset" value="{config.get('asset')}"></div>
                        <div class="form-group"><label>Objectif ROI %</label><input type="number" id="yield" value="{config.get('target_yield')}"></div>
                        <div class="form-group"><label>Date Limite</label><input type="date" id="deadline" value="{config.get('deadline')}"></div>
                        <div class="btn-group">
                            <button class="btn-start" onclick="sendCommand('START')">DÉMARRER</button>
                            <button class="btn-stop" onclick="sendCommand('STOP')">ARRÊTER</button>
                            <button class="btn-update" onclick="sendCommand('UPDATE_CONFIG')">MAJ CONFIG</button>
                        </div>
                        <p id="log" style="font-size: 11px; margin-top: 15px; color: #768390; text-align: center;"></p>
                    </div>
                </div>
            </div>
        </div>
        <script>
            async function sendCommand(cmd) {{
                const token = localStorage.getItem('GITHUB_TOKEN') || prompt('GITHUB_TOKEN :');
                if (!token) return;
                localStorage.setItem('GITHUB_TOKEN', token);
                const log = document.getElementById('log');
                log.innerText = "⏳ Envoi...";
                const payload = {{ ref: 'main', inputs: {{ command: cmd, asset: document.getElementById('asset').value, target_yield: document.getElementById('yield').value, macro_info: document.getElementById('macro').value, deadline: document.getElementById('deadline').value }} }};
                try {{
                    const res = await fetch('https://api.github.com/repos/mkfprod2025-cloud/warren/actions/workflows/bot.yml/dispatches', {{
                        method: 'POST',
                        headers: {{ 'Authorization': `token ${{token}}`, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
                        body: JSON.stringify(payload)
                    }});
                    if (res.ok) {{ log.innerText = "✅ Succès !"; log.style.color = "var(--green)"; }}
                    else {{ log.innerText = "❌ Erreur"; log.style.color = "var(--red)"; }}
                }} catch (e) {{ log.innerText = "❌ Erreur connexion"; }}
            }}
        </script>
    </body>
    </html>
    """
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f: f.write(html_content)

    # 2. GÉNÉRATION MARKDOWN
    md_content = f"""# 📈 WARREN AI STATUS (v3.5)\n**État :** {status_text} | **PNL :** {total_pnl:.2f}%\n\n### 🧠 Analyse ({last_decision.get('asset', 'N/A')})\n> {last_decision.get('raisonnement', 'N/A')}\n\n### 📍 Positions Actives\n| Actif | Action | Entrée | SL | TP | Cap |\n|---|---|---|---|---|---|\n"""
    for asset, data in positions.items():
        md_content += f"| {asset} | {data['action']} | {data['entry_price']} | {data.get('sl','-')} | {data.get('tp','-')} | {data.get('capital_pct','-')}% |\n"
    with open(DASHBOARD_MD, "w", encoding="utf-8") as f: f.write(md_content)

def ask_gemini_pro(asset, config, market_data):
    prompt = f"""Tu es Warren, trader expert Futures BitMart. OBJECTIF: {config['target_yield']}% net d'ici le {config['deadline']}. ACTIF: {asset}. MACRO: {config.get('macro_info', 'N/A')}. DONNÉES: Prix {market_data['price']} | Bid/Ask {market_data['best_bid']}/{market_data['best_ask']}. RÉPONDS STRICTEMENT EN JSON: {{"raisonnement": "analyse détaillée", "action": "LONG"|"SHORT"|"CLOSE"|"HOLD", "levier": 1-20, "sl": prix, "tp": prix, "pourcentage_capital": 1-100}}"""
    for model_id in MODELS_PRIORITY:
        try:
            response = client.models.generate_content(model=model_id, contents=prompt, config={"response_mime_type": "application/json"})
            decision = response.parsed if response.parsed else json.loads(response.text)
            decision['model_used'] = model_id
            decision['asset'] = asset
            return decision
        except Exception: continue
    return {"action": "HOLD", "raisonnement": "Saturation IA.", "asset": asset}

def execute(asset, decision, market_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    positions = load_json(POSITIONS_FILE, {})
    trades = load_json(TRADES_FILE, [])
    action = decision['action']
    price = market_data['price']
    trade_info = { "timestamp": timestamp, "asset": asset, "action": action, "price": price, "levier": decision.get('levier', 1), "raisonnement": decision['raisonnement'], "model_used": decision.get('model_used', 'N/A') }
    if action in ["LONG", "SHORT"]:
        positions[asset] = { "entry_price": price, "action": action, "levier": decision['levier'], "sl": decision.get('sl'), "tp": decision.get('tp'), "capital_pct": decision.get('pourcentage_capital', 10), "timestamp": timestamp }
    elif action == "CLOSE" and asset in positions:
        pos = positions[asset]
        pnl = (price - pos['entry_price'])/pos['entry_price'] if pos['action']=="LONG" else (pos['entry_price'] - price)/pos['entry_price']
        trade_info["pnl_net_pct"] = (pnl * pos['levier'] - (2 * FEE_RATE)) * 100
        del positions[asset]
    trades.append(trade_info)
    with open(POSITIONS_FILE, "w") as f: json.dump(positions, f, indent=4)
    with open(TRADES_FILE, "w") as f: json.dump(trades, f, indent=4)
    return trade_info

def run_cycle():
    config = get_config()
    trades = load_json(TRADES_FILE, [])
    positions = load_json(POSITIONS_FILE, {})
    if not config.get("bot_running"):
        generate_dashboards(config, trades, positions, {"raisonnement": "Bot en pause."})
        return
    last_decision = {"raisonnement": "Analyse Multi-Trading..."}
    assets = list(set([config["asset"]] + ASSETS_TO_WATCH))
    for asset in assets:
        data = get_market_data(asset)
        if data:
            decision = ask_gemini_pro(asset, config, data)
            if decision['action'] != "HOLD" or asset == config["asset"]:
                execute(asset, decision, data)
                last_decision = decision
        time.sleep(1)
    generate_dashboards(config, trades, positions, last_decision)

def get_market_data(asset):
    symbol = asset.replace("/", "")
    contract_api = APIContract(BITMART_API_KEY, BITMART_SECRET, BITMART_MEMO)
    try:
        res = contract_api.get_details(symbol)
        if not res or 'data' not in res[0]: return None
        details = res[0]['data']['symbols'][0]
        depth = contract_api.get_depth(symbol)[0]['data']
        best_bid = float(depth['bids'][0][0]) if depth['bids'] else float(details['last_price'])
        best_ask = float(depth['asks'][0][0]) if depth['asks'] else float(details['last_price'])
        return {"price": float(details['last_price']), "best_bid": best_bid, "best_ask": best_ask}
    except Exception as e: return None

if __name__ == "__main__":
    try: run_cycle()
    except Exception as e:
        import traceback
        with open(DASHBOARD_MD, "w", encoding="utf-8") as f: f.write(f"# 🚨 ERREUR CRITIQUE v3.5\n```python\n{traceback.format_exc()}\n```")
