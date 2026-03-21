import os
import json
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from bitmart.api_f_market import Market
from bitmart.api_f_trade import Trade

load_dotenv()

# Configuration API
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
BITMART_API_KEY = os.getenv("BITMART_API_KEY")
BITMART_SECRET = os.getenv("BITMART_SECRET")
BITMART_MEMO = os.getenv("BITMART_MEMO")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

CONFIG_FILE = "config.json"

def get_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def get_market_data(asset):
    # Logique pour récupérer OHLCV via bitmart-python-sdk-api
    # Pour l'instant, simulé
    return {"current_price": 50000, "volume": 1200, "ohlcv": "..."}

def ask_gemini(asset, target, deadline, market_data):
    prompt = f"""
    Tu es un trader autonome sur contrats à terme. 
    Actif : {asset}. Objectif : {target}% ROI avant le {deadline}. 
    Données du marché : {market_data}. 
    Tu as carte blanche sur la stratégie et le levier. Gère ton risque pour éviter la liquidation. 
    Réponds strictement en JSON : {{'raisonnement': 'explication de ton choix', 'action': 'LONG'|'SHORT'|'CLOSE'|'HOLD', 'levier': entier, 'pourcentage_capital': entier}}
    """
    response = model.generate_content(prompt)
    try:
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return {"action": "HOLD", "raisonnement": "Erreur parsing JSON IA"}

def run_bot():
    print("Bot Warren démarré...")
    while True:
        config = get_config()
        if not config["bot_running"]:
            time.sleep(5)
            continue
        
        print(f"Analyse de {config['asset']}...")
        market_data = get_market_data(config["asset"])
        decision = ask_gemini(config["asset"], config["target_yield"], config["deadline"], market_data)
        
        print(f"Décision Gemini: {decision['action']} - {decision['raisonnement']}")
        
        # Logique d'exécution BitMart ici
        
        time.sleep(60) # Pause entre les cycles

if __name__ == "__main__":
    run_bot()
