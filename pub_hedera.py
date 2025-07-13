import paho.mqtt.client as mqtt
import random
import json
import time
import os

# --- Configuration MQTT ---
broker = "localhost"
port = 1883
topic = "iot/water_quality"
log_file = "data_log.json"

client = mqtt.Client(client_id="RealisticWaterPublisher", protocol=mqtt.MQTTv311)
client.connect(broker, port)

# --- Charger les anciennes données (si fichier existe) ---
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        data_log = json.load(f)
else:
    data_log = []

# --- Fonctions de notation ---
def score_ph(pH): return 95 if 6.5 <= pH <= 8.5 else 75 if 6.0 <= pH < 6.5 or 8.5 < pH <= 9.0 else 50
def score_turb(turb): return 100 if turb <= 1 else 80 if turb <= 5 else 60 if turb <= 10 else 40
def score_temp(temp): return 95 if 20 <= temp <= 25 else 75 if 15 <= temp < 20 or 25 < temp <= 30 else 55
def score_oxy(oxy): return 95 if oxy >= 8 else 75 if oxy >= 6 else 55 if oxy >= 4 else 30
def score_tds(tds): return 95 if tds <= 300 else 75 if tds <= 600 else 50
def score_fc(fc): return 100 if fc <= 2 else 80 if fc <= 5 else 60 if fc <= 10 else 40
def score_tp(tp): return 95 if tp <= 0.1 else 75 if tp <= 0.3 else 50
def score_tpn(tpn): return 95 if tpn <= 0.3 else 75 if tpn <= 0.6 else 50
def score_tss(tss): return 95 if tss <= 10 else 75 if tss <= 30 else 50

# --- Simulation ---
print("📡 Simulation en cours (appuie sur Ctrl+C pour arrêter)...")

try:
    while True:
        raw_data = {
            "pH": round(random.uniform(6.0, 9.0), 2),
            "Temp": round(random.uniform(10, 35), 2),
            "TDS": round(random.uniform(100, 1000), 2),
            "Turb": round(random.uniform(0.5, 15), 2),
            "FC": round(random.uniform(0.1, 15), 2),
            "Oxy": round(random.uniform(2, 10), 2),
            "TP": round(random.uniform(0.05, 0.5), 2),
            "TPN": round(random.uniform(0.05, 1.0), 2),
            "TSS": round(random.uniform(1, 60), 2),
        }

        transformed = {
            "WQI pH": score_ph(raw_data["pH"]),
            "WQI Temp": score_temp(raw_data["Temp"]),
            "WQI TDS": score_tds(raw_data["TDS"]),
            "WQI Turb": score_turb(raw_data["Turb"]),
            "WQI FC": score_fc(raw_data["FC"]),
            "WQI Oxy": score_oxy(raw_data["Oxy"]),
            "WQI TP": score_tp(raw_data["TP"]),
            "WQI TPN": score_tpn(raw_data["TPN"]),
            "WQI TSS": score_tss(raw_data["TSS"])
        }

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "raw": raw_data,
            "wqi": transformed
        }

        # Publier sur MQTT
        payload = json.dumps(transformed)
        client.publish(topic, payload)
        print(f"📤 Published: {payload}")

        # Ajouter au log local
        data_log.append(entry)

        # Sauvegarder dans le fichier JSON
        with open(log_file, "w") as f:
            json.dump(data_log, f, indent=4)

        time.sleep(5)

except KeyboardInterrupt:
    print("🛑 Simulation arrêtée.")
    client.disconnect()
