import pandas as pd
import json
import time
import os
from sklearn.ensemble import RandomForestRegressor
from web3 import Web3
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import traceback
import csv
from datetime import datetime

# 🔐 Charger les variables sécurisées
load_dotenv(dotenv_path=".env")

private_key = os.getenv("HEDERA_PRIVATE_KEY")
raw_my_address = os.getenv("MY_ADDRESS")
hedera_rpc = os.getenv("HEDERA_RPC")
raw_contract_address = os.getenv("CONTRACT_ADDRESS")

# Conversion en checksum address
my_address = Web3.to_checksum_address(raw_my_address)
contract_address = Web3.to_checksum_address(raw_contract_address)

print("🔎 CONTRACT_ADDRESS from env:", raw_contract_address)
print("✅ Checksum contract address:", contract_address)

# Connexion Hedera EVM
w3 = Web3(Web3.HTTPProvider(hedera_rpc))
print("✅ Connected to Hedera RPC:", w3.is_connected())
print(f"Private key: {private_key}")

# Vérification clé privée / adresse
account_from_private = w3.eth.account.from_key(private_key)
print("🔑 Adresse calculée depuis clé privée :", account_from_private.address)
print("👤 Adresse my_address :", my_address)
if account_from_private.address != my_address:
    print("⚠️ Attention : la clé privée ne correspond PAS à l'adresse publique.")

# Chargement du contrat
contract = w3.eth.contract(address=contract_address, abi=[
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint256", "name": "WQI", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "quality", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "WQIAdded",
        "type": "event"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
        "name": "getRecord",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getRecordsCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "records",
        "outputs": [
            {"internalType": "uint256", "name": "WQI", "type": "uint256"},
            {"internalType": "string", "name": "quality", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_wqi", "type": "uint256"},
            {"internalType": "string", "name": "_quality", "type": "string"}
        ],
        "name": "storeWQI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
])

# 📊 Charger le modèle IA
df = pd.read_csv("WQI_Parameter_Scores_1994-2013_modified.csv")
features = ['WQI FC', 'WQI Oxy', 'WQI pH', 'WQI TSS', 'WQI Temp', 'WQI TPN', 'WQI TP', 'WQI Turb']
X = df[features]
y = df['Overall WQI']
model = RandomForestRegressor()
model.fit(X, y)

def quality_check(wqi):
    if wqi >= 95:
        return 'Excellent'
    elif wqi >= 80:
        return 'Good'
    elif wqi >= 65:
        return 'Fair'
    elif wqi >= 45:
        return 'Marginal'
    else:
        return 'Poor'

def save_to_json(wqi, category, timestamp):
    record = {
        "WQI": round(wqi, 2),
        "Quality": category,
        "Timestamp": timestamp
    }
    if os.path.exists("records.json"):
        with open("records.json", "r") as f:
            data = json.load(f)
    else:
        data = []
    data.append(record)
    with open("records.json", "w") as f:
        json.dump(data, f, indent=2)

# === MQTT CALLBACKS — NE PAS TOUCHER L'ORDRE ===

def on_connect(client, userdata, flags, rc):
    print(f"✅ MQTT connecté avec code résultat {rc}")
    client.subscribe("iot/water_quality")
    print("📡 Abonnement au topic 'iot/water_quality' effectué.")

def on_message(client, userdata, msg):
    try:
        print("\n📥 Message MQTT reçu !")
        data = json.loads(msg.payload.decode())
        print(f"Données brutes reçues : {data}")
        df_input = pd.DataFrame([{
            'WQI FC': data['WQI FC'],
            'WQI Oxy': data['WQI Oxy'],
            'WQI pH': data['WQI pH'],
            'WQI TSS': data['WQI TSS'],
            'WQI Temp': data['WQI Temp'],
            'WQI TPN': data['WQI TPN'],
            'WQI TP': data['WQI TP'],
            'WQI Turb': data['WQI Turb']
        }])
        prediction = model.predict(df_input)[0]
        category = quality_check(prediction)
        print(f"📊 WQI prédit : {prediction:.2f} — Qualité : {category}")

        if category in ['Poor', 'Marginal']:
            nonce = w3.eth.get_transaction_count(my_address)
            gas_estimate = contract.functions.storeWQI(int(prediction), category).estimate_gas({'from': my_address})
            txn = contract.functions.storeWQI(int(prediction), category).build_transaction({
                'from': my_address,
                'nonce': nonce,
                'gas': gas_estimate,
                'chainId': 296
            })
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            timestamp = int(time.time())
            print(f"✅ Transaction minée ! Bloc #{receipt.blockNumber} — Hash : {tx_hash.hex()}")
            save_to_json(prediction, category, timestamp)
        else:
            print("🔕 Qualité satisfaisante. Donnée non stockée sur la blockchain.")

    except Exception as e:
        print(f"⚠️ Erreur de traitement détaillée : {e}")
        traceback.print_exc()

# === INITIALISATION CLIENT MQTT FIABLE ===
client = mqtt.Client(client_id="WaterQualitySubscriber")
client.on_connect = on_connect
client.on_message = on_message
client.enable_logger()  # Logs détaillés

client.connect("broker.hivemq.com", 1883)
print("✅ Subscriber MQTT prêt. En attente de messages...\n")
client.loop_forever()
