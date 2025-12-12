import sys
import os
from concurrent import futures
import grpc
import pymongo

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from protos import f1_pb2, f1_pb2_grpc


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["f1_telemetria"]
collection = db["pneus"]


class MonitoramentoService(f1_pb2_grpc.MonitoramentoServicer):

    # Agora implementamos o EnviarLotePneus
    def EnviarLotePneus(self, request, context):
        lista_para_salvar = []

        # Itera sobre a lista recebida no gRPC (request.dados)
        for item in request.dados:
            dados_mongo = {
                "carro_id": item.carro_id,
                "sensor_responsavel": item.sensor_id,
                "velocidade": item.velocidade,
                "volta": item.volta,
                "timestamp": item.timestamp,
                "pneus": {
                    "fl": {"temp": item.pneu_fl.temperatura, "desgaste": item.pneu_fl.desgaste,
                           "press": item.pneu_fl.pressao},
                    "fr": {"temp": item.pneu_fr.temperatura, "desgaste": item.pneu_fr.desgaste,
                           "press": item.pneu_fr.pressao},
                    "rl": {"temp": item.pneu_rl.temperatura, "desgaste": item.pneu_rl.desgaste,
                           "press": item.pneu_rl.pressao},
                    "rr": {"temp": item.pneu_rr.temperatura, "desgaste": item.pneu_rr.desgaste,
                           "press": item.pneu_rr.pressao},
                }
            }
            lista_para_salvar.append(dados_mongo)

        if lista_para_salvar:
            collection.insert_many(lista_para_salvar)
            print(f"[SACP] Lote recebido com {len(lista_para_salvar)} registros. Salvo no DB.")

        return f1_pb2.Resposta(mensagem="Lote Processado", sucesso=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    f1_pb2_grpc.add_MonitoramentoServicer_to_server(MonitoramentoService(), server)
    server.add_insecure_port('[::]:50051')
    print("Servidor SACP (Modo Lote) rodando na porta 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()