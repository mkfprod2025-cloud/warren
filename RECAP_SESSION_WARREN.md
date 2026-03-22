# 📚 RÉSUMÉ DE SESSION : PROJET WARREN (21/03/2026)

**Objectif :** Création d'un bot de trading algorithmique autonome pour BitMart Futures, piloté par l'IA Gemini 2.5 Flash.

## 1. Architecture Technique
*   **Moteur (`bot.py`)** : Analyse multi-temporelle (bougies 15 min et 1 h sur 3 jours). Calcul automatique du **spread** (via carnet d'ordres) et déduction des **frais de transaction (0.06%)**. Gestion des **positions persistantes** via `positions.json`.
*   **Interface (`app.py`)** : Panneau de contrôle Streamlit affichant le Statut, l'Actif, le PNL Net Total et les Positions Ouvertes en temps réel.
*   **Persistance** : Utilisation de fichiers JSON pour sauvegarder les réglages et l'état du bot même après fermeture.

## 2. Autonomie & Cloud
*   **Hébergement App** : Déploiement sur Streamlit Cloud (`https://warren-zrgzvecrtwjeuwbsqfo9kr.streamlit.app/`).
*   **Hébergement Bot** : Configuration d'une **GitHub Action** pour lancer un cycle d'analyse toutes les 15 minutes, 24h/24.
*   **Permissions** : Configuration des "Workflow permissions" en "Read and write" sur GitHub pour permettre la sauvegarde des données.

## 3. Sécurité (CRITIQUE)
*   **Incident** : Le fichier `.env` a été exposé sur GitHub. Nettoyage immédiat de l'historique et sécurisation du repo effectué.
*   **Conséquence** : La clé Gemini API a été révoquée par Google (protection automatique).
*   **Action requise** : Générer une nouvelle clé sur Google AI Studio et mettre à jour le `.env`, les Secrets GitHub et Streamlit.

## 4. État Final (Mise à jour le 21/03/2026)
*   **Correction Code** : Suppression des doublons dans `bot.py` et fiabilisation du parsing JSON de l'IA.
*   **Modèle Gemini** : Utilisation de `gemini-2.0-flash` avec `response_mime_type: application/json` pour une fiabilité totale des décisions.
*   **Configuration** : Fichier `.env` reformaté proprement avec les variables `BITMART_API_KEY` et `BITMART_SECRET`.
*   **Sécurité** : `.env` confirmé dans le `.gitignore`. 
*   **Prochaine étape** : Lancer un cycle test pour valider l'IA.

⚠️ **Action requise** : Pensez à vérifier vos secrets sur GitHub Actions (Secrets and variables > Actions) pour que le bot autonome puisse s'exécuter sur GitHub avec les mêmes clés.
