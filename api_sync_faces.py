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

import os
# ... (código de configuración de Flask, rutas, etc.)

if __name__ == "__main__":
    # Obtiene el puerto desde la variable de entorno PORT, con un default por si falta
    port = int(os.environ.get("PORT", 5000))
    # Inicia la aplicación Flask escuchando en todas las interfaces (0.0.0.0) y en el puerto especificado
    app.run(host="0.0.0.0", port=port)


