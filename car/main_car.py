import time
import json
import random
import os
import paho.mqtt.client as mqtt

# --- CONFIGURAÇÕES ---
# Pega configurações das variáveis de ambiente (para funcionar no Docker)
BROKER_ADDRESS = os.getenv("BROKER_ADDRESS", "localhost")
BROKER_PORT = 1883
TOPIC = "f1/pneus"

# Se não tiver ID definido no Docker, gera um aleatório
CAR_ID = os.getenv("CAR_ID", f"Carro_Desconhecido_{random.randint(1, 99)}")

# --- ESTADO INICIAL DO CARRO ---
# Mantemos o estado fora do loop para simular a progressão (desgaste acumulativo)
estado_pneus = {
    "fl": {"desgaste": 0.0, "temp": 90.0, "pressao": 22.0},  # Front Left
    "fr": {"desgaste": 0.0, "temp": 90.0, "pressao": 22.0},  # Front Right
    "rl": {"desgaste": 0.0, "temp": 90.0, "pressao": 20.0},  # Rear Left
    "rr": {"desgaste": 0.0, "temp": 90.0, "pressao": 20.0},  # Rear Right
}
volta_atual = 1


def simular_fisica():
    """
    Atualiza o estado dos pneus baseados em uma simulação simples.
    """
    global volta_atual

    # Simula velocidade variável na volta
    velocidade = random.uniform(100.0, 340.0)

    # Fator de desgaste: curvas rápidas desgastam mais
    fator_stress = (velocidade / 340.0) * random.uniform(0.05, 0.2)

    for posicao, pneu in estado_pneus.items():
        # Aumenta desgaste
        pneu["desgaste"] += fator_stress
        if pneu["desgaste"] > 100: pneu["desgaste"] = 100.0

        # Temperatura varia com a velocidade (mais rápido = mais quente)
        # Tenta manter entre 80 e 120 graus
        target_temp = 80 + (velocidade * 0.12)
        pneu["temp"] = (pneu["temp"] * 0.9) + (target_temp * 0.1) + random.uniform(-2, 2)

        # Pressão sobe com a temperatura (Lei dos Gases Ideais simplificada)
        pneu["pressao"] = 20.0 + (pneu["temp"] / 100.0) * 2.5

    # Lógica de volta (a cada 20 envios, conta uma volta - só para exemplo)
    if random.randint(0, 20) == 0:
        volta_atual += 1

    return velocidade


def gerar_payload(velocidade):
    """
    Monta o JSON final conforme esperado pelo sistema
    """
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
        print(f"[{CAR_ID}] Conectado ao Broker MQTT com sucesso!")
    else:
        print(f"[{CAR_ID}] Falha na conexão. Código: {rc}")


print(f"[{CAR_ID}] Iniciando telemetria...")
client = mqtt.Client(client_id=CAR_ID)
client.on_connect = on_connect

# Tenta conectar (loop de retry simples caso o broker ainda esteja subindo)
while True:
    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT)
        break
    except Exception as e:
        print(f"Aguardando Broker em {BROKER_ADDRESS}...")
        time.sleep(2)

client.loop_start()

try:
    while True:
        # 1. Simular
        vel = simular_fisica()

        # 2. Gerar JSON
        dados = gerar_payload(vel)
        payload_str = json.dumps(dados)

        # 3. Publicar
        client.publish(TOPIC, payload_str)
        print(f"[{CAR_ID}] Enviado. Vel: {vel:.1f} km/h | Desgaste FL: {dados['pneus']['dianteiro_esq']['desgaste']}%")

        # Frequência de envio (simula passar pelos sensores ISCCP)
        time.sleep(3)

except KeyboardInterrupt:
    print("Parando carro...")
    client.loop_stop()
    client.disconnect()