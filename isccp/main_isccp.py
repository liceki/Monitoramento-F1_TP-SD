import sys
import os
import json
import random
import paho.mqtt.client as mqtt
import grpc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from protos import f1_pb2, f1_pb2_grpc

# Configurações
BROKER = os.getenv("BROKER_ADDRESS", "localhost")
TOPIC = "f1/pneus"
GRPC_HOST = os.getenv("GRPC_SERVER", "localhost:50051")

# GERA UM ID PARA ESTE SENSOR (Simula ser um sensor específico na pista)
SENSOR_ID = f"Sensor_Interlagos_Setor_{random.randint(1, 15)}"

# Config gRPC
channel = grpc.insecure_channel(GRPC_HOST)
stub = f1_pb2_grpc.MonitoramentoStub(channel)


def on_connect(client, userdata, flags, rc):
    print(f"[{SENSOR_ID}] Conectado ao Broker MQTT.")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[{SENSOR_ID}] Detectou carro: {payload['carro_id']}")

        # Mapeando JSON do Carro -> Objeto gRPC
        # Nota: O nome das chaves deve bater com o JSON gerado no main_car.py
        p_fl = payload['pneus']['dianteiro_esq']
        p_fr = payload['pneus']['dianteiro_dir']
        p_rl = payload['pneus']['traseiro_esq']
        p_rr = payload['pneus']['traseiro_dir']

        rpc_request = f1_pb2.DadosCarro(
            carro_id=payload['carro_id'],
            sensor_id=SENSOR_ID,  # O sensor assina a mensagem
            velocidade=payload['velocidade'],
            volta=payload['volta'],
            timestamp=str(payload['timestamp']),
            pneu_fl=f1_pb2.Pneu(temperatura=p_fl['temperatura'], desgaste=p_fl['desgaste'], pressao=p_fl['pressao']),
            pneu_fr=f1_pb2.Pneu(temperatura=p_fr['temperatura'], desgaste=p_fr['desgaste'], pressao=p_fr['pressao']),
            pneu_rl=f1_pb2.Pneu(temperatura=p_rl['temperatura'], desgaste=p_rl['desgaste'], pressao=p_rl['pressao']),
            pneu_rr=f1_pb2.Pneu(temperatura=p_rr['temperatura'], desgaste=p_rr['desgaste'], pressao=p_rr['pressao']),
        )

        # Envia para o SACP via gRPC
        stub.EnviarDadosPneu(rpc_request)

    except Exception as e:
        print(f"Erro processando mensagem: {e}")


client = mqtt.Client(client_id=f"ISCCP_{random.randint(1000, 9999)}")
client.on_connect = on_connect
client.on_message = on_message

print(f"[{SENSOR_ID}] Iniciando ponte MQTT -> gRPC...")
client.connect(BROKER, 1883, 60)
client.loop_forever()