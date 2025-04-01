from flask import Flask
from juntos import sync_users, init_db

app = Flask(__name__)

# Contexto simple que imprime en consola
class Context:
    def log(self, msg):
        print(msg)

@app.route("/sync_faces", methods=["POST"])
def handle_sync():
    print("📡 Petición recibida para sincronizar rostros...")
    sync_users(Context())
    return {"message": "✅ Rostros sincronizados correctamente"}, 200

if __name__ == "__main__":
    init_db()  # Asegura que la base de datos esté lista
import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
