import os
from flask import Flask, jsonify, render_template
import pymongo

app = Flask(__name__)

# Adicionamos "readPreference=primaryPreferred" para garantir que lemos dados atualizados
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?readPreference=primaryPreferred")

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["f1_telemetria"]
    collection = db["pneus"]
    print(f"Conectado ao Mongo: {MONGO_URI}")
except Exception as e:
    print(f"ERRO CRÍTICO DE CONEXÃO MONGO: {e}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/telemetria', methods=['GET'])
def get_telemetria():
    try:
        # --- A MÁGICA DA AGREGAÇÃO ---
        pipeline = [
            # 1. Ordena tudo do mais novo para o mais antigo
            {"$sort": {"timestamp": -1}},

            # 2. Agrupa por carro_id
            {"$group": {
                "_id": "$carro_id",  # A chave do grupo
                "doc": {"$first": "$$ROOT"}  # Pega o primeiro documento encontrado (o mais novo)
            }},

            # 3. Limpa o formato para devolver o documento original
            {"$replaceRoot": {"newRoot": "$doc"}},

            # 4. Ordena alfabeticamente para o JSON ficar bonito
            {"$sort": {"carro_id": 1}}
        ]

        # O aggregate retorna um cursor, convertemos para lista
        dados = list(collection.aggregate(pipeline))

        return jsonify(dados)
    except Exception as e:
        print(f"Erro na agregação: {e}")
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)