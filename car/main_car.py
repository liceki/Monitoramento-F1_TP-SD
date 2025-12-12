import time
import json
import random
import os
import paho.mqtt.client as mqtt
import pymongo
from pymongo.errors import DuplicateKeyError, ConnectionFailure

# --- CONFIGURAÇÕES ---
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "localhost")
BROKER_PORT = 1883
TOPIC = "f1/pneus"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

# Lista Oficial (Exatamente 24 Pilotos)
PILOTOS = [
    "RedBull - Verstappen", "RedBull - Perez",
    "Ferrari - Leclerc", "Ferrari - Sainz",
    "Mercedes - Hamilton", "Mercedes - Russell",
    "McLaren - Norris", "McLaren - Piastri",
    "Aston Martin - Alonso", "Aston Martin - Stroll",
    "Alpine - Gasly", "Alpine - Ocon",
    "Williams - Albon", "Williams - Sargeant",
    "RB - Ricciardo", "RB - Tsunoda",
    "Sauber - Bottas", "Sauber - Zhou",
    "Haas - Magnussen", "Haas - Hulkenberg",
    "Safety Car - Mercedes", "Safety Car - Aston",
    "Reserva - Drugovich", "Reserva - Fittipaldi"
]


def registrar_identidade():
    """
    Loop infinito até conseguir um nome único no Banco de Dados.
    """
    print("Tentando conectar ao Grid (MongoDB) para pegar identidade...")

    # Randomiza tempo inicial para evitar 24 conexões simultâneas exatas
    time.sleep(random.uniform(0, 5))

    while True:
        client = None
        try:
            # Tenta conectar (timeout curto para não travar muito)
            client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            db = client["f1_telemetria"]
            col = db["grid_f1"]

            # Embaralha a lista para tentar pegar qualquer vaga livre
            tentativas = list(PILOTOS)
            random.shuffle(tentativas)

            for nome in tentativas:
                try:
                    # Tenta reservar o nome. Se já existe, dá erro e tenta o próximo.
                    col.insert_one({"_id": nome, "timestamp": time.time()})
                    print(f"--- IDENTIDADE CONFIRMADA: {nome} ---")
                    client.close()
                    return nome
                except DuplicateKeyError:
                    continue  # Nome ocupado

            # Se chegou aqui, todos os nomes estão ocupados (ou erro de lógica)
            print("Grid cheio? Tentando novamente em 5s...")
            time.sleep(5)

        except (ConnectionFailure, Exception) as e:
            print(f"Aguardando Banco de Dados... ({e})")
            time.sleep(3)
        finally:
            if client: client.close()


# --- BLOQUEANTE: O CARRO SÓ LIGA SE TIVER NOME ---
CAR_ID = registrar_identidade()

# --- ESTADO INICIAL ---
estado_pneus = {
    "fl": {"desgaste": 0.0, "temp": 90.0, "pressao": 22.0},
    "fr": {"desgaste": 0.0, "temp": 90.0, "pressao": 22.0},
    "rl": {"desgaste": 0.0, "temp": 90.0, "pressao": 20.0},
    "rr": {"desgaste": 0.0, "temp": 90.0, "pressao": 20.0},
}
volta_atual = 1


def simular_fisica():
    global volta_atual
    velocidade = random.uniform(100.0, 340.0)
    fator_stress = (velocidade / 340.0) * random.uniform(0.05, 0.2)

    for posicao, pneu in estado_pneus.items():
        pneu["desgaste"] += fator_stress
        if pneu["desgaste"] > 100: pneu["desgaste"] = 100.0

        target_temp = 80 + (velocidade * 0.12)
        pneu["temp"] = (pneu["temp"] * 0.9) + (target_temp * 0.1) + random.uniform(-2, 2)
        pneu["pressao"] = 20.0 + (pneu["temp"] / 100.0) * 2.5

    if random.randint(0, 20) == 0:
        volta_atual += 1
    return velocidade


def gerar_payload(velocidade):
    return {
        "carro_id": CAR_ID,
        "volta": volta_atual,
        "velocidade": round(velocidade, 2),
        "timestamp": time.time(),
        "pneus": {
            "dianteiro_esq": {
                "temperatura": round(estado_pneus["fl"]["temp"], 1),
                "desgaste": round(estado_pneus["fl"]["desgaste"], 1),
                "pressao": round(estado_pneus["fl"]["pressao"], 2)
            },
            "dianteiro_dir": {
                "temperatura": round(estado_pneus["fr"]["temp"], 1),
                "desgaste": round(estado_pneus["fr"]["desgaste"], 1),
                "pressao": round(estado_pneus["fr"]["pressao"], 2)
            },
            "traseiro_esq": {
                "temperatura": round(estado_pneus["rl"]["temp"], 1),
                "desgaste": round(estado_pneus["rl"]["desgaste"], 1),
                "pressao": round(estado_pneus["rl"]["pressao"], 2)
            },
            "traseiro_dir": {
                "temperatura": round(estado_pneus["rr"]["temp"], 1),
                "desgaste": round(estado_pneus["rr"]["desgaste"], 1),
                "pressao": round(estado_pneus["rr"]["pressao"], 2)
            }
        }
    }


# --- CONEXÃO MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CAR_ID}] Conectado ao Broker MQTT!")


# Client ID aleatório para não dar conflito no Broker
client = mqtt.Client(client_id=f"Car_Conn_{random.randint(1000, 999999)}")
client.on_connect = on_connect

while True:
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT)
        break
    except:
        time.sleep(2)

client.loop_start()

try:
    while True:
        vel = simular_fisica()
        payload = json.dumps(gerar_payload(vel))
        client.publish(TOPIC, payload)
        # Intervalo seguro para não afogar os sensores
        time.sleep(random.uniform(4.0, 6.0))
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()