import time
import json
import random
import os
import paho.mqtt.client as mqtt

# --- CONFIGURAÇÕES ---
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "localhost")
BROKER_PORT = 1883
TOPIC = "f1/pneus"

# Lista Oficial F1 2024 (Simplificada para caber nos cards)
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
    # Extras para completar 24 carros (Safety Cars ou Reservas)
    "Safety Car - Mercedes", "Safety Car - Aston",
    "F2 - Bearman", "F2 - Antonelli"
]

# Tenta pegar um ID único baseado no hostname do Docker para não repetir nomes
# O Docker nomeia como "projeto_carro_1", "projeto_carro_2"...
try:
    hostname = os.uname()[1]  # Pega o nome do container ex: f1-carro-12
    # Extrai números do hostname
    numero_container = int(''.join(filter(str.isdigit, hostname)))
    # Usa o numero para pegar o index da lista (com modulo para não estourar)
    nome_piloto = PILOTOS[(numero_container - 1) % len(PILOTOS)]
except:
    # Fallback: Se não conseguir ler o hostname, pega aleatório
    nome_piloto = random.choice(PILOTOS)

CAR_ID = nome_piloto

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


# --- CONEXÃO ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CAR_ID}] Conectado!")
    else:
        print(f"Falha conexão: {rc}")


client = mqtt.Client(client_id=f"Car_{random.randint(1000, 9999)}")  # ID MQTT único
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
        # Randomiza um pouco o tempo de envio para evitar que todos mandem EXATAMENTE juntos
        time.sleep(random.uniform(2.5, 3.5))
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()