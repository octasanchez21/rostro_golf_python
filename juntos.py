import os
import sqlite3
import requests
import mimetypes
import json
from concurrent.futures import ThreadPoolExecutor
from requests.auth import HTTPDigestAuth
from tago import Analysis

# Configuración
DB_PATH = "sap_users.db"
HOST = "34.221.158.219"
DEV_INDEXES = [
    "F5487AA0-2485-4CFB-9304-835DCF118B43",
    "08395809-0EFA-48EA-B37F-DC628A83398A"
]
USERNAME = 'admin'
PASSWORD = 'Inteliksa6969'
SAP_URL = "http://localhost:3000/get-socios"
SAP_HEADERS = {"Authorization": "SKIntegracionXetuxTruoraAPIREST#.01"}

# Inicializar base de datos
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            employeeNo TEXT PRIMARY KEY,
            faceURL TEXT,
            name TEXT
        )
    """)
    conn.commit()
    conn.close()

# Obtener datos de SAP
def get_sap_users():
    try:
        response = requests.get(SAP_URL, headers=SAP_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [u for u in data.get("contenido", []) if u.get("employeeNo")]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error al obtener usuarios de SAP: {e}")
        return []

# Obtener datos almacenados
def get_stored_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT employeeNo, faceURL FROM usuarios")
    stored = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return stored

# Actualizar la base de datos local
def update_database(users):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios")
    for user in users:
        cursor.execute("INSERT INTO usuarios (employeeNo, faceURL, name) VALUES (?, ?, ?)",
                       (user["employeeNo"], user["faceURL"], user["name"]))
    conn.commit()
    conn.close()

# Eliminar rostro de dispositivo
def delete_face(employee_no, context):
    for devIndex in DEV_INDEXES:
        url = f"http://{HOST}/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&devIndex={devIndex}"
        payload = {
            "FaceInfoDelCond": {
                "faceLibType": "blackFD",
                "EmployeeNoList": [{"employeeNo": employee_no}]
            }
        }
        try:
            response = requests.put(url, json=payload, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=10)
            if response.status_code == 200:
                context.log(f"🗑️ Rostro eliminado: {employee_no} en {devIndex}")
            else:
                context.log(f"⚠️ Error al eliminar rostro {employee_no} en {devIndex}: {response.text}")
        except Exception as e:
            context.log(f"❌ Error al eliminar rostro {employee_no}: {e}")

# Agregar rostro al dispositivo
def add_face(user, context):
    employee_no = user.get("employeeNo")
    image_url = user.get("faceURL")
    if not image_url:
        context.log(f"⚠️ Usuario {employee_no} sin URL de imagen.")
        return

    try:
        img_data = requests.get(image_url, timeout=10).content
        if not img_data:
            context.log(f"⚠️ No se pudo descargar imagen para {employee_no}")
            return

        file_type = mimetypes.guess_type(image_url)[0] or 'image/jpeg'
        face_info = {"FaceInfo": {"employeeNo": employee_no, "faceLibType": "blackFD"}}
        files = {'FaceDataRecord': ("face.jpg", img_data, file_type)}
        data = {'data': json.dumps(face_info)}

        for devIndex in DEV_INDEXES:
            url = f"http://{HOST}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json&devIndex={devIndex}"
            response = requests.post(url, data=data, files=files, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=10)
            if response.status_code == 200:
                context.log(f"✅ Rostro agregado: {employee_no} en {devIndex}")
            else:
                context.log(f"❌ Error agregando rostro {employee_no} en {devIndex}: {response.text}")
    except Exception as e:
        context.log(f"⚠️ Error al agregar rostro para {employee_no}: {e}")

# Comparar y sincronizar usuarios
def sync_users(context):
    sap_users = get_sap_users()
    if not sap_users:
        context.log("⚠️ No se encontraron usuarios desde SAP.")
        return

    stored_users = get_stored_users()
    users_to_update = []
    users_to_create = []

    for user in sap_users:
        emp_no = user["employeeNo"]
        face_url = user["faceURL"]
        if emp_no not in stored_users:
            users_to_create.append(user)
        elif stored_users[emp_no] != face_url:
            users_to_update.append(user)

    for user in users_to_update:
        context.log(f"🔄 Actualizando imagen para {user['employeeNo']}")
        delete_face(user["employeeNo"], context)
        add_face(user, context)

    for user in users_to_create:
        context.log(f"🆕 Agregando nuevo rostro para {user['employeeNo']}")
        add_face(user, context)

    update_database(sap_users)
    context.log("✅ Sincronización completada.")

# Análisis principal
def my_analysis(context, scope):
    context.log("🚀 Iniciando análisis de rostros...")
    sync_users(context)

# Inicializar base de datos e iniciar análisis
init_db()
ANALYSIS_TOKEN = 'a-bf743737-88be-41d7-a6be-edfc32dac943'
if __name__ == "__main__":
    Analysis(ANALYSIS_TOKEN).init(my_analysis)
