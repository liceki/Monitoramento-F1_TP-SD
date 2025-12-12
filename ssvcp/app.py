import os
from flask import Flask, jsonify, render_template # <-- Adicionado render_template
import pymongo

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["f1_telemetria"]
    collection = db["pneus"]
    print(f"Conectado ao Mongo em: {MONGO_URI}")
except Exception as e:
    print(f"ERRO CRÍTICO DE CONEXÃO MONGO: {e}")

# --- NOVA ROTA PARA O DASHBOARD ---
@app.route('/')
def index():
    return render_template('index.html')
# ----------------------------------

@app.route('/api/telemetria', methods=['GET'])
def get_telemetria():
    try:
        # Aumentei o limite para 100 para garantir que pegamos dados de todos os 24 carros
        # senão alguns carros podem sumir do painel se muitos enviarem ao mesmo tempo
        cursor = collection.find({}, {'_id': 0}).sort("timestamp", -1).limit(100)
        dados = list(cursor)
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)