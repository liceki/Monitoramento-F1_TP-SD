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
SENSOR_ID = f"Sensor_Setor_{random.randint(1, 15)}"

# --- BUFFER GLOBAL ---
buffer_dados = []
lock = threading.Lock()  # Segurança para não dar conflito entre threads

# Config gRPC
channel = grpc.insecure_channel(GRPC_HOST)
stub = f1_pb2_grpc.MonitoramentoStub(channel)


def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_ID}] Conectado ao Broker.")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        # Converte JSON -> Objeto Protobuf
        p_fl = payload['pneus']['dianteiro_esq']
        p_fr = payload['pneus']['dianteiro_dir']
        p_rl = payload['pneus']['traseiro_esq']
        p_rr = payload['pneus']['traseiro_dir']

        objeto_proto = f1_pb2.DadosCarro(
            carro_id=payload['carro_id'],
            sensor_id=SENSOR_ID,
            velocidade=payload['velocidade'],
            volta=payload['volta'],
            timestamp=str(payload['timestamp']),
            pneu_fl=f1_pb2.Pneu(temperatura=p_fl['temperatura'], desgaste=p_fl['desgaste'], pressao=p_fl['pressao']),
            pneu_fr=f1_pb2.Pneu(temperatura=p_fr['temperatura'], desgaste=p_fr['desgaste'], pressao=p_fr['pressao']),
            pneu_rl=f1_pb2.Pneu(temperatura=p_rl['temperatura'], desgaste=p_rl['desgaste'], pressao=p_rl['pressao']),
            pneu_rr=f1_pb2.Pneu(temperatura=p_rr['temperatura'], desgaste=p_rr['desgaste'], pressao=p_rr['pressao']),
        )

        # Em vez de enviar, adiciona no Buffer protegido por Lock
        with lock:
            buffer_dados.append(objeto_proto)
            # Opcional: print a cada X recebimentos para não poluir log
            # print(f"[{SENSOR_ID}] Bufferizado: {payload['carro_id']}")

    except Exception as e:
        print(f"Erro processando mensagem: {e}")


# Função que roda em paralelo para enviar o lote periodicamente
def rotina_envio_periodico():
    while True:
        time.sleep(5)  # Espera 5 segundos

        with lock:
            qtd = len(buffer_dados)
            if qtd > 0:
                print(f"[{SENSOR_ID}] Enviando lote de {qtd} registros para o SACP...")
                try:
                    # Cria o pacote de lista
                    lote = f1_pb2.ListaDadosCarro(dados=buffer_dados)
                    stub.EnviarLotePneus(lote)

                    # Limpa o buffer após envio com sucesso
                    buffer_dados.clear()
                    print(f"[{SENSOR_ID}] Lote enviado com sucesso.")
                except Exception as e:
                    print(f"[{SENSOR_ID}] ERRO ao enviar lote: {e}")
            # Se qtd == 0, não faz nada, só espera mais 5s


# 1. Inicia o MQTT
client = mqtt.Client(client_id=f"ISCCP_{random.randint(1000, 9999)}")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, 1883, 60)
client.loop_start()  # Roda o MQTT numa thread separada

# 2. Roda o loop de envio periódico na thread principal
print(f"[{SENSOR_ID}] Iniciando Coleta Periódica (5s)...")
try:
    rotina_envio_periodico()
except KeyboardInterrupt:
    client.loop_stop()