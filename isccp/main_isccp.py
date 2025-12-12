import sys
import os
import json
import time
import random
import threading
import paho.mqtt.client as mqtt
import grpc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from protos import f1_pb2, f1_pb2_grpc

# Configurações
BROKER = os.getenv("BROKER_ADDRESS", "localhost")
TOPIC = "f1/pneus"
GRPC_HOST = os.getenv("GRPC_SERVER", "localhost:50051")

# Buffer de Lote
buffer_dados = []
lock = threading.Lock()

# Config gRPC
channel = grpc.insecure_channel(GRPC_HOST)
stub = f1_pb2_grpc.MonitoramentoStub(channel)


def on_connect(client, userdata, flags, rc):
    print(f"[ISCCP] Conectado ao Broker. Aguardando carros...")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        # --- CORREÇÃO AQUI: ADAPTANDO PARA AS NOVAS CHAVES (fl, fr, rl, rr) ---
        p_fl = payload['pneus']['fl']
        p_fr = payload['pneus']['fr']
        p_rl = payload['pneus']['rl']
        p_rr = payload['pneus']['rr']

        # O carro agora calcula onde ele está (GPS), então usamos isso
        sensor_atual = payload.get('sensor_responsavel', f"Sensor_Backup_{random.randint(1, 99)}")

        objeto_proto = f1_pb2.DadosCarro(
            carro_id=payload['carro_id'],
            sensor_id=sensor_atual,  # Usa o nome do setor da pista (ex: "S do Senna")
            velocidade=payload['velocidade'],
            volta=payload['volta'],
            timestamp=str(payload['timestamp']),
            pneu_fl=f1_pb2.Pneu(temperatura=p_fl['temperatura'], desgaste=p_fl['desgaste'], pressao=p_fl['pressao']),
            pneu_fr=f1_pb2.Pneu(temperatura=p_fr['temperatura'], desgaste=p_fr['desgaste'], pressao=p_fr['pressao']),
            pneu_rl=f1_pb2.Pneu(temperatura=p_rl['temperatura'], desgaste=p_rl['desgaste'], pressao=p_rl['pressao']),
            pneu_rr=f1_pb2.Pneu(temperatura=p_rr['temperatura'], desgaste=p_rr['desgaste'], pressao=p_rr['pressao']),
        )

        with lock:
            buffer_dados.append(objeto_proto)

    except Exception as e:
        # Se der erro de chave, mostra no log para sabermos
        print(f"[ISCCP] Erro ao ler JSON do carro: {e}")


def rotina_envio_periodico():
    while True:
        time.sleep(3)  # Envia lote a cada 5 segundos
        with lock:
            qtd = len(buffer_dados)
            if qtd > 0:
                print(f"[ISCCP] Enviando lote de {qtd} telemetrias...")
                try:
                    lote = f1_pb2.ListaDadosCarro(dados=buffer_dados)
                    stub.EnviarLotePneus(lote)
                    buffer_dados.clear()
                    print(f"[ISCCP] Lote enviado com sucesso.")
                except Exception as e:
                    print(f"[ISCCP] ERRO gRPC: {e}")


# Inicia MQTT
client = mqtt.Client(client_id=f"ISCCP_Listener_{random.randint(1000, 9999)}")
client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        client.connect(BROKER, 1883, 60)
        break
    except:
        time.sleep(2)

client.loop_start()

print("ISCCP Rodando: Coletando dados da pista...")
try:
    rotina_envio_periodico()
except KeyboardInterrupt:
    client.loop_stop()