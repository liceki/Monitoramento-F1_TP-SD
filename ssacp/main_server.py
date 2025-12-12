import sys
import os
from concurrent import futures
import grpc
import pymongo

# Ajuste de path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from protos import f1_pb2, f1_pb2_grpc

# Conexão Mongo
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["f1_telemetria"]
collection = db["pneus"]


class MonitoramentoService(f1_pb2_grpc.MonitoramentoServicer):
    def EnviarDadosPneu(self, request, context):
        # Converte a mensagem gRPC de volta para Dicionário Python para salvar no Mongo
        dados_mongo = {
            "carro_id": request.carro_id,
            "sensor_responsavel": request.sensor_id,
            "velocidade": request.velocidade,
            "volta": request.volta,
            "timestamp": request.timestamp,
            "pneus": {
                "fl": {"temp": request.pneu_fl.temperatura, "desgaste": request.pneu_fl.desgaste,
                       "press": request.pneu_fl.pressao},
                "fr": {"temp": request.pneu_fr.temperatura, "desgaste": request.pneu_fr.desgaste,
                       "press": request.pneu_fr.pressao},
                "rl": {"temp": request.pneu_rl.temperatura, "desgaste": request.pneu_rl.desgaste,
                       "press": request.pneu_rl.pressao},
                "rr": {"temp": request.pneu_rr.temperatura, "desgaste": request.pneu_rr.desgaste,
                       "press": request.pneu_rr.pressao},
            }
        }

        collection.insert_one(dados_mongo)
        print(f"[SACP] {request.carro_id} passou pelo sensor {request.sensor_id} - Salvo no DB.")
        return f1_pb2.Resposta(mensagem="OK", sucesso=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    f1_pb2_grpc.add_MonitoramentoServicer_to_server(MonitoramentoService(), server)
    server.add_insecure_port('[::]:50051')
    print("Servidor SACP rodando na porta 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()