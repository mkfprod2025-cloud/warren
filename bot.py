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

def get_config():
    default = {"bot_running": False, "demo_mode": True, "asset": "BTC/USDT", "target_yield": 12.0, "deadline": "2026-12-31", "macro_info": ""}
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
    """Génère le Dashboard HTML5 et le résumé Markdown (v3.3)"""
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
        <title>WARREN AI - Terminal</title>
        <style>
            :root {{ --bg: #0a0e14; --card: #151b23; --text: #adbac7; --accent: #58a6ff; --green: #3fb950; --red: #f85149; }}
            body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 15px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
            .status-badge {{ padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }}
            .status-active {{ background: rgba(63, 185, 80, 0.2); color: var(--green); }}
            .status-stopped {{ background: rgba(248, 81, 73, 0.2); color: var(--red); }}
            .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 15px; }}
            .card {{ background: var(--card); border: 1px solid #30363d; border-radius: 6px; padding: 12px; }}
            .card h3 {{ margin: 0; font-size: 11px; color: #768390; text-transform: uppercase; }}
            .card p {{ margin: 5px 0 0; font-size: 18px; font-weight: bold; }}
            .brain {{ margin-top: 15px; background: #1c2128; border-left: 4px solid var(--accent); padding: 12px; border-radius: 4px; font-size: 13px; }}
            .console {{ margin-top: 20px; background: #0d1117; border: 1px solid var(--accent); border-radius: 8px; padding: 15px; }}
            .console h2 {{ font-size: 16px; margin-top: 0; color: var(--accent); }}
            .form-group {{ margin-bottom: 10px; }}
            label {{ display: block; font-size: 11px; color: #768390; margin-bottom: 4px; }}
            input, select, textarea {{ width: 100%; background: #1c2128; border: 1px solid #30363d; color: white; padding: 8px; border-radius: 4px; box-sizing: border-box; }}
            .btn-group {{ display: flex; gap: 10px; margin-top: 15px; }}
            button {{ flex: 1; padding: 10px; border-radius: 6px; border: none; font-weight: bold; cursor: pointer; }}
            .btn-start {{ background: var(--green); color: white; }}
            .btn-stop {{ background: var(--red); color: white; }}
            .btn-update {{ background: var(--accent); color: white; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #30363d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 WARREN AI <small style="font-size: 10px; color: #768390;">v3.3</small></h1>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
            
            <div class="grid">
                <div class="card"><h3>Actif</h3><p>{config.get('asset')}</p></div>
                <div class="card"><h3>PNL Net</h3><p style="color: {'var(--green)' if total_pnl >=0 else 'var(--red)'}">{total_pnl:.2f}%</p></div>
                <div class="card"><h3>Objectif %</h3><p>{config.get('target_yield')}%</p></div>
                <div class="card"><h3>Date Limite</h3><p style="font-size: 14px;">{config.get('deadline')}</p></div>
            </div>

            <div class="brain">
                <strong style="color:var(--accent);">🧠 Analyse :</strong> "{last_decision.get('raisonnement', 'En attente de cycle...')}"
            </div>

            <div class="console">
                <h2>🎮 Télécommande Warren</h2>
                <div class="form-group">
                    <label>Donnée Macro / Instruction</label>
                    <textarea id="macro" placeholder="Ex: Marché très volatil...">{config.get('macro_info', '')}</textarea>
                </div>
                <div class="grid" style="grid-template-columns: 1fr 1fr 1fr;">
                    <div class="form-group"><label>Actif</label><input type="text" id="asset" value="{config.get('asset')}"></div>
                    <div class="form-group"><label>Obj. %</label><input type="number" id="yield" value="{config.get('target_yield')}"></div>
                    <div class="form-group"><label>Deadline</label><input type="date" id="deadline" value="{config.get('deadline')}"></div>
                </div>
                <div class="btn-group">
                    <button class="btn-start" onclick="sendCommand('START')">DÉMARRER</button>
                    <button class="btn-stop" onclick="sendCommand('STOP')">ARRÊTER</button>
                    <button class="btn-update" onclick="sendCommand('UPDATE_CONFIG')">MAJ CONFIG</button>
                </div>
                <p id="log" style="font-size: 10px; margin-top: 10px; color: #768390; text-align: center;"></p>
            </div>

            <script>
                async function sendCommand(cmd) {{
                    const token = localStorage.getItem('GITHUB_TOKEN') || prompt('Entrez votre GITHUB_TOKEN :');
                    if (!token) return;
                    localStorage.setItem('GITHUB_TOKEN', token);
                    const log = document.getElementById('log');
                    log.innerText = "⏳ Envoi de l'ordre...";
                    const payload = {{ ref: 'main', inputs: {{ command: cmd, asset: document.getElementById('asset').value, target_yield: document.getElementById('yield').value, macro_info: document.getElementById('macro').value, deadline: document.getElementById('deadline').value }} }};
                    try {{
                        const res = await fetch('https://api.github.com/repos/mkfprod2025-cloud/warren/actions/workflows/bot.yml/dispatches', {{
                            method: 'POST',
                            headers: {{ 'Authorization': `token ${{token}}`, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json' }},
                            body: JSON.stringify(payload)
                        }});
                        if (res.ok) {{ log.innerText = "✅ Ordre reçu !"; log.style.color = "var(--green)"; }}
                        else {{ const err = await res.json(); log.innerText = "❌ Erreur : " + (err.message || 'Inconnue'); log.style.color = "var(--red)"; }}
                    }} catch (e) {{ log.innerText = "❌ Erreur de connexion : " + e.message; }}
                }}
            </script>

            <h2>📍 Positions Ouvertes</h2>
            <table>
                <thead><tr><th>Actif</th><th>Sens</th><th>Entrée</th><th>Levier</th></tr></thead>
                <tbody>
    """
    for asset, data in positions.items():
        sens = f"<span style='color:var(--green)'>LONG</span>" if data['action'] == "LONG" else f"<span style='color:var(--red)'>SHORT</span>"
        html_content += f"<tr><td>{asset}</td><td>{sens}</td><td>{data['entry_price']}</td><td>{data['levier']}x</td></tr>"
    
    if not positions: html_content += "<tr><td colspan='4' style='text-align:center;'>Aucune position.</td></tr>"

    html_content += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f: f.write(html_content)

    # 2. GÉNÉRATION MARKDOWN
    md_content = f"""# 📈 WARREN AI STATUS (v3.3)
**État :** {status_text} | **PNL :** {total_pnl:.2f}% | **Actif :** {config.get('asset')}

### 🧠 Dernière Analyse
> {last_decision.get('raisonnement', 'N/A')}

### 📍 Positions
"""
    if positions:
        md_content += "| Actif | Action | Prix Entrée | Levier |\n|---|---|---|---|\n"
        for asset, data in positions.items():
            md_content += f"| {asset} | {data['action']} | {data['entry_price']} | {data['levier']}x |\n"
    else:
        md_content += "_Aucune position ouverte._\n"
    
    with open(DASHBOARD_MD, "w", encoding="utf-8") as f: f.write(md_content)

def ask_gemini_pro(asset, config, market_data):
    prompt = f"""
    Tu es Warren, un trader IA expert Futures sur BitMart.
    OBJECTIF : {config['target_yield']}% net d'ici le {config['deadline']}.
    MACRO : {config.get('macro_info', 'N/A')}
    DONNÉES MARCHÉ : Prix {market_data['price']} | Bid/Ask {market_data['best_bid']}/{market_data['best_ask']}
    
    RÉPONDS STRICTEMENT EN JSON :
    {{
        "raisonnement": "analyse technique et macro ultra-détaillée",
        "action": "LONG" | "SHORT" | "CLOSE" | "HOLD" | "SET_SL_TP",
        "levier": 1-20,
        "sl": prix, "tp": prix, "pourcentage_capital": 1-100
    }}
    """
    for model_id in MODELS_PRIORITY:
        try:
            response = client.models.generate_content(model=model_id, contents=prompt, config={"response_mime_type": "application/json"})
            decision = response.parsed if response.parsed else json.loads(response.text)
            decision['model_used'] = model_id
            return decision
        except Exception: continue
    return {"action": "HOLD", "raisonnement": "Saturation IA ou erreur modèle."}

def execute(asset, decision, market_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    positions = load_json(POSITIONS_FILE, {})
    trades = load_json(TRADES_FILE, [])
    
    action = decision['action']
    price = market_data['price']
    
    trade_info = {
        "timestamp": timestamp, "action": action, "price": price, 
        "levier": decision.get('levier', 1), "raisonnement": decision['raisonnement'],
        "model_used": decision.get('model_used', 'N/A')
    }

    if action in ["LONG", "SHORT"]:
        positions[asset] = {
            "entry_price": price, "action": action, "levier": decision['levier'],
            "sl": decision.get('sl'), "tp": decision.get('tp'), "timestamp": timestamp
        }
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
        print("Warren est en pause. Mise à jour des dashboards.")
        generate_dashboards(config, trades, positions, {"raisonnement": "Bot en pause (OFF)."})
        return

    data = get_market_data(config["asset"])
    if data:
        decision = ask_gemini_pro(config["asset"], config, data)
        execute(config["asset"], decision, data)
        generate_dashboards(config, trades, positions, decision)
    else:
        generate_dashboards(config, trades, positions, {"raisonnement": "Erreur de connexion BitMart."})

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
    except Exception as e:
        print(f"Erreur BitMart: {e}")
        return None

if __name__ == "__main__":
    run_cycle()
