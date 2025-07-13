import streamlit as st
import subprocess
import pandas as pd
import os
import time
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import threading
import platform

# --------- MQTT Listener (en fond, simple) ----------
messages = []

def on_connect(client, userdata, flags, rc):
    print("Connecté au broker MQTT")
    client.subscribe("iot/water_quality")

def on_message(client, userdata, msg):
    messages.append(msg.payload.decode())

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("broker.hivemq.com", 1883, 60)
threading.Thread(target=client.loop_forever, daemon=True).start()

# --------- UI Streamlit -----------
st.set_page_config(page_title="💧 Water Quality Hedera DApp", layout="wide")
st.title("💧 Water Quality Monitoring Interface (Hedera)")

# --- CSS amélioré ---
st.markdown("""
<style>
    /* Arrière-plan général */
    .main {
        background-color: #f3f6fb;
    }

    /* Boutons stylisés */
    .stButton > button {
        background: linear-gradient(90deg, #1d3557, #457b9d);
        color: #ffffff !important;
        font-weight: 600;
        font-size: 16px;
        border: none;
        border-radius: 12px !important;
        padding: 11px 26px !important;
        margin: 8px 4px !important;
        box-shadow: 0 2px 8px rgba(69, 123, 157, 0.18);
        transition: all 0.22s cubic-bezier(.4,0,.2,1);
    }

    .stButton > button:hover {
        background: linear-gradient(90deg, #274472, #1d3557);
        box-shadow: 0 6px 18px rgba(69, 123, 157, 0.24);
        transform: scale(1.03);
    }

    /* Cadre DataFrame */
    .stDataFrame {
        border-radius: 14px !important;
        border: 1.5px solid #457b9d !important;
        background-color: #ffffff;
        box-shadow: 0 4px 14px rgba(30, 41, 59, 0.06);
        padding: 6px;
    }

    /* En-tête du tableau */
    .css-1iyq50i, .css-1bqk63h {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        font-weight: 700;
        text-align: center;
        font-size: 15px;
        border-top-left-radius: 14px !important;
        border-top-right-radius: 14px !important;
    }

    /* Cellules du tableau */
    .dataframe td {
        background-color: #f8fafc !important; /* Gris bleuté neutre */
        color: #1e293b !important;
        padding: 13px;
        font-size: 15px;
        border-bottom: 1px solid #e2e8f0;
    }

    /* Lignes zébrées */
    .dataframe tbody tr:nth-child(even) td {
        background-color: #e8f0fa !important; /* Bleu-gris clair */
    }

    /* Hover sur les lignes */
    .dataframe tbody tr:hover td {
        background-color: #dbeafe !important; /* Bleu pro pastel */
        transition: background-color 0.18s cubic-bezier(.4,0,.2,1);
    }

    /* Surbrillance des cellules qualité (exemple : adapter si tu fais du coloring conditionnel en Pandas) */
    td.quality-excellent {background-color:#b9fbc0!important; color:#164e24!important;}
    td.quality-good      {background-color:#e7fbb9!important; color:#4d6219!important;}
    td.quality-fair      {background-color:#fff4b9!important; color:#785b00!important;}
    td.quality-marginal  {background-color:#ffe4b9!important; color:#6b3600!important;}
    td.quality-poor      {background-color:#fbb9b9!important; color:#7c2323!important;}
</style>

""", unsafe_allow_html=True)

# --- INIT état session ---
if "publisher_launched" not in st.session_state:
    st.session_state.publisher_launched = False
if "subscriber_launched" not in st.session_state:
    st.session_state.subscriber_launched = False

# --- Section 1: Boutons ---
st.header("⚙️ Contrôle des modules Publisher/Subscriber")

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Démarrer le Publisher"):
        if not st.session_state.publisher_launched:
            subprocess.Popen(["python", "pub_hedera.py"])
            time.sleep(1)
            st.session_state.publisher_launched = True
            st.success("✅ Publisher lancé !")
        else:
            st.warning("🚫 Publisher déjà lancé.")
    if st.button("🛑 Arrêter le Publisher"):
        if st.session_state.publisher_launched:
            if platform.system() == "Windows":
                os.system('taskkill /f /im python.exe /fi "WINDOWTITLE eq pub_hedera.py*"')
                os.system('taskkill /f /im python.exe /fi "CMDLINE eq *pub_hedera.py*"')
            else:
                os.system("pkill -f pub_hedera.py")
            st.session_state.publisher_launched = False
            st.success("🛑 Publisher arrêté.")
        else:
            st.info("Publisher n'est pas lancé.")

with col2:
    if st.button("📡 Démarrer le Subscriber"):
        if not st.session_state.subscriber_launched:
            subprocess.Popen(["python", "subs_hedera.py"])
            time.sleep(1)
            st.session_state.subscriber_launched = True
            st.success("✅ Subscriber lancé !")
        else:
            st.warning("🚫 Subscriber déjà lancé.")
    if st.button("🛑 Arrêter le Subscriber"):
        if st.session_state.subscriber_launched:
            if platform.system() == "Windows":
                os.system('taskkill /f /im python.exe /fi "WINDOWTITLE eq subs_hedera.py*"')
                os.system('taskkill /f /im python.exe /fi "CMDLINE eq *subs_hedera.py*"')
            else:
                os.system("pkill -f subs_hedera.py")
            st.session_state.subscriber_launched = False
            st.success("🛑 Subscriber arrêté.")
        else:
            st.info("Subscriber n'est pas lancé.")

# --- Section 2: MQTT en live ---
st.header("🛰️ 10 derniers messages MQTT reçus")
if messages:
    for m in messages[-10:][::-1]:
        st.code(m, language="json")
else:
    st.info("En attente de messages MQTT...")

# --- Section 3: Affichage JSON (Historique local) ---
st.header("🔗 Suivi des transactions enregistrées sur la Blockchain Hedera")

json_file = "records.json"
def load_json_table():
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            try:
                data = json.load(f)
                for d in data:
                    # Conversion Timestamp unix -> lisible
                    if "Timestamp" in d and isinstance(d["Timestamp"], (int, float)):
                        d["Timestamp"] = datetime.fromtimestamp(d["Timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        d["Timestamp"] = "N/A"
                return pd.DataFrame(data)
            except json.JSONDecodeError:
                return pd.DataFrame()
    else:
        return pd.DataFrame()

df_json = load_json_table()
def highlight_quality(row):
    color_map = {
        'Excellent': 'background-color: #f6fbf7; color: #217a38; font-weight: 500;',   # Vert-gris très pâle, texte vert foncé
        'Good':      'background-color: #f4f7fb; color: #245082; font-weight: 500;',   # Bleu-gris pâle, texte bleu foncé
        'Fair':      'background-color: #fafaf7; color: #a89b42; font-weight: 500;',   # Gris très clair, texte bronze
        'Marginal':  'background-color: #f9f7f4; color: #be8945; font-weight: 500;',   # Beige clair, texte ambre foncé
        'Poor':      'background-color: #f6f1f2; color: #9b2323; font-weight: 600;',   # Gris rosé pâle, texte bordeaux
    }
    quality = row.get('Quality', None)
    return [color_map.get(quality, 'background-color: #ffffff; color: #23272b;')] * len(row)

if df_json.empty:
    st.warning("Aucun enregistrement local trouvé dans `records.json`.")
else:
    st.dataframe(
        df_json.style
            .apply(highlight_quality, axis=1)
            .set_properties(**{'border-radius': '8px', 'font-size': '16px'})
            .hide(axis="index"),
        use_container_width=True
    )

# --- Rafraîchissement manuel ---
st.markdown("---")
if st.button("🔄 Rafraîchir les données"):
    st.experimental_rerun()
