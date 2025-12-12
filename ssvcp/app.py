import os
import sys
import logging
from flask import Flask, jsonify, render_template
import pymongo

# Configuração de Logs
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s', stream=sys.stdout)
logger = logging.getLogger("F1_Dashboard")

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")


def get_db_collection():
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000, directConnection=False)
        return client["f1_telemetria"]["pneus"]
    except Exception as e:
        logger.error(f"Erro ao criar cliente Mongo: {e}")
        raise e


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/telemetria', methods=['GET'])
def get_telemetria():
    try:
        collection = get_db_collection()

        # Pipeline corrigido
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$carro_id",
                "doc": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},

            # --- A CORREÇÃO ESTÁ AQUI EMBAIXO ---
            # Remove o campo _id que causa o erro de JSON
            {"$project": {"_id": 0}},
            # ------------------------------------

            {"$sort": {"carro_id": 1}}
        ]

        dados = list(collection.aggregate(pipeline))
        logger.debug(f"Sucesso! Retornando {len(dados)} carros.")
        return jsonify(dados)

    except Exception as e:
        logger.error(f"ERRO FATAL NA API: {str(e)}", exc_info=True)
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)