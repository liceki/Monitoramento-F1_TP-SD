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

# --- MAPEAMENTO DA PISTA DE INTERLAGOS (BASEADO NA FIGURA 1) ---
# Interlagos é Anti-Horário (Esquerda). Pneus da DIREITA sofrem mais.
# stress: 1.0 = normal, >1 = curva forte, <1 = reta
TRACK_MAP = [
    {"id": 1, "nome": "S do Senna (Entrada)", "vel_min": 70, "vel_max": 110, "stress": 2.5, "lado_apoio": "direita"},
    {"id": 2, "nome": "S do Senna (Saída)", "vel_min": 120, "vel_max": 180, "stress": 2.0, "lado_apoio": "direita"},
    {"id": 3, "nome": "Curva do Sol", "vel_min": 180, "vel_max": 230, "stress": 1.8, "lado_apoio": "direita"},
    {"id": 4, "nome": "Reta Oposta", "vel_min": 290, "vel_max": 330, "stress": 0.5, "lado_apoio": "neutro"},
    {"id": 5, "nome": "Descida do Lago", "vel_min": 130, "vel_max": 170, "stress": 2.2, "lado_apoio": "direita"},
    {"id": 6, "nome": "Ferradura", "vel_min": 150, "vel_max": 200, "stress": 2.0, "lado_apoio": "direita"},
    {"id": 7, "nome": "Laranjinha", "vel_min": 160, "vel_max": 210, "stress": 1.8, "lado_apoio": "direita"},
    {"id": 8, "nome": "Pinheirinho", "vel_min": 80, "vel_max": 120, "stress": 2.3, "lado_apoio": "esquerda"},
    # Curva p/ direita (rara em Interlagos)
    {"id": 9, "nome": "Bico de Pato", "vel_min": 70, "vel_max": 100, "stress": 2.5, "lado_apoio": "direita"},
    {"id": 10, "nome": "Mergulho", "vel_min": 180, "vel_max": 220, "stress": 1.5, "lado_apoio": "direita"},
    {"id": 11, "nome": "Junção", "vel_min": 110, "vel_max": 140, "stress": 2.4, "lado_apoio": "direita"},
    {"id": 12, "nome": "Subida dos Boxes", "vel_min": 240, "vel_max": 280, "stress": 1.0, "lado_apoio": "direita"},
    {"id": 13, "nome": "Arquibancadas A", "vel_min": 290, "vel_max": 315, "stress": 0.6, "lado_apoio": "neutro"},
    {"id": 14, "nome": "Arquibancadas B", "vel_min": 300, "vel_max": 325, "stress": 0.6, "lado_apoio": "neutro"},
    {"id": 15, "nome": "Reta Principal", "vel_min": 310, "vel_max": 340, "stress": 0.5, "lado_apoio": "neutro"},
]

PILOTOS = [
    "RedBull - Verstappen", "RedBull - Perez", "Ferrari - Leclerc", "Ferrari - Sainz",
    "Mercedes - Hamilton", "Mercedes - Russell", "McLaren - Norris", "McLaren - Piastri",
    "Aston Martin - Alonso", "Aston Martin - Stroll", "Alpine - Gasly", "Alpine - Ocon",
    "Williams - Albon", "Williams - Sargeant", "RB - Ricciardo", "RB - Tsunoda",
    "Sauber - Bottas", "Sauber - Zhou", "Haas - Magnussen", "Haas - Hulkenberg",
    "Safety Car - Mercedes", "Safety Car - Aston", "Reserva - Drugovich", "Reserva - Fittipaldi"
]


# --- REGISTRO DE IDENTIDADE ---
def registrar_identidade():
    time.sleep(random.uniform(0, 5))
    while True:
        client = None
        try:
            client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            db = client["f1_telemetria"]
            col = db["grid_f1"]
            tentativas = list(PILOTOS)
            random.shuffle(tentativas)
            for nome in tentativas:
                try:
                    col.insert_one({"_id": nome, "timestamp": time.time()})
                    print(f"--- PILOTO CONFIRMADO: {nome} ---")
                    client.close()
                    return nome
                except DuplicateKeyError:
                    continue
            time.sleep(5)
        except Exception:
            time.sleep(3)
        finally:
            if client: client.close()


CAR_ID = registrar_identidade()

# --- ESTADO INICIAL ---
# Pressão base fria (psi)
estado_pneus = {
    "fl": {"desgaste": 0.0, "temp": 80.0, "pressao": 22.0},
    "fr": {"desgaste": 0.0, "temp": 80.0, "pressao": 22.0},
    "rl": {"desgaste": 0.0, "temp": 80.0, "pressao": 20.0},
    "rr": {"desgaste": 0.0, "temp": 80.0, "pressao": 20.0},
}
volta_atual = 1
indice_setor = 0  # Começa no setor 1


def simular_fisica_realista():
    global volta_atual, indice_setor

    # Pega o setor atual da lista
    setor = TRACK_MAP[indice_setor]

    # 1. Velocidade baseada no setor
    velocidade = random.uniform(setor["vel_min"], setor["vel_max"])

    # 2. Física dos Pneus
    for posicao, pneu in estado_pneus.items():
        # Fator base de desgaste
        stress_real = setor["stress"] * random.uniform(0.08, 0.12)

        # Interlagos é Anti-Horário: Pneus da DIREITA sofrem mais
        if setor["lado_apoio"] == "direita" and "r" in posicao:  # fr ou rr
            stress_real *= 1.8  # 80% mais desgaste/calor nos pneus de apoio
        elif setor["lado_apoio"] == "esquerda" and "l" in posicao:  # fl ou rl
            stress_real *= 1.8

        # Velocidade extrema também desgasta (mesmo em retas)
        if velocidade > 300:
            stress_real += 0.05

        # Aplica desgaste
        pneu["desgaste"] += stress_real
        if pneu["desgaste"] > 100: pneu["desgaste"] = 100.0

        # Temperatura: Sobe nas curvas, desce levemente nas retas (refrigeração)
        target_temp = 90 + (stress_real * 100)  # Curvas jogam temp pra 110-120
        if setor["stress"] < 1.0:  # Reta
            target_temp = 85 + (velocidade * 0.05)  # Resfria um pouco mas mantém quente pela rotação

        # Inércia térmica (temperatura não muda instantaneamente)
        pneu["temp"] = (pneu["temp"] * 0.8) + (target_temp * 0.2) + random.uniform(-1, 1)

        # Lei dos Gases (Gay-Lussac): Pressão sobe com temperatura
        # P = k * T (Simplificado)
        pneu["pressao"] = 20.0 + (pneu["temp"] / 100.0) * 3.5

    # Avança para o próximo setor
    setor_nome_atual = setor["nome"]
    indice_setor += 1

    # Se passou do último setor (15), volta pro 1 e conta volta
    if indice_setor >= len(TRACK_MAP):
        indice_setor = 0
        volta_atual += 1

    return velocidade, setor_nome_atual


def gerar_payload(velocidade, setor_nome):
    return {
        "carro_id": CAR_ID,
        "sensor_responsavel": setor_nome,  # AQUI O TRUQUE: O carro avisa onde está
        "volta": volta_atual,
        "velocidade": round(velocidade, 0),
        "timestamp": time.time(),
        "pneus": {
            k: {
                "temperatura": round(v["temp"], 1),
                "desgaste": round(v["desgaste"], 2),
                "pressao": round(v["pressao"], 2)
            } for k, v in estado_pneus.items()
        }
    }


# --- CONEXÃO MQTT ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{CAR_ID}] Pronto para largada!")


client = mqtt.Client(client_id=f"F1Car_{random.randint(1000, 99999)}")
client.on_connect = on_connect

while True:
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT)
        break
    except:
        time.sleep(2)

client.loop_start()

try:
    # Largada aleatória para espalhar o grid
    time.sleep(random.uniform(0, 10))

    while True:
        # Simula um trecho da pista
        vel, trecho = simular_fisica_realista()

        payload = json.dumps(gerar_payload(vel, trecho))
        client.publish(TOPIC, payload)

        # Tempo para percorrer o setor (Retas são rápidas, Curvas lentas)
        # Ajustado para dar uma volta em ~1min10s
        tempo_setor = 7200 / vel  # Ex: 300km/h = ~2.4s, 80km/h = ~9s (escala reduzida)
        time.sleep(tempo_setor * 0.2)  # Aceleramos o tempo x5 para a demo ser dinâmica

except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()