from flask import Flask
from juntos import sync_users, init_db

app = Flask(__name__)

# Inicializa la base de datos al cargar el microservicio
init_db()

# Contexto simple que imprime en consola
class Context:
    def log(self, msg):
        print(msg)

# 🔁 Ruta para probar si el servidor está funcionando
@app.route("/", methods=["GET"])
def health_check():
    return {"status": "ok", "message": "Microservicio Flask activo 🎉"}, 200

# Ruta principal para sincronizar rostros
@app.route("/sync_faces", methods=["POST"])
def handle_sync():
    print("📡 Petición recibida para sincronizar rostros...")
    sync_users(Context())
    return {"message": "✅ Rostros sincronizados correctamente"}, 200

