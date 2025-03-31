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
    "F5487AA0-2485-4CFB-9304-835DCF118B43",  # Primer dispositivo
    "08395809-0EFA-48EA-B37F-DC628A83398A"   # Segundo dispositivo (ejemplo, cambiar por el real)
]
USERNAME = 'admin'
PASSWORD = 'Inteliksa6969'
SAP_URL = "http://localhost:3000/get-socios"
SAP_HEADERS = {"Authorization": "SKIntegracionXetuxTruoraAPIREST#.01"}

# Inicializar la base de datos
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

# Obtener datos de la base de datos
def get_stored_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT employeeNo, faceURL FROM usuarios")
    stored_users = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return stored_users

# Guardar nueva respuesta en la base de datos
def update_database(users):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios")  # Limpiar datos anteriores
    for user in users:
        cursor.execute("INSERT INTO usuarios (employeeNo, faceURL, name) VALUES (?, ?, ?)",
                       (user["employeeNo"], user["faceURL"], user["name"]))
    conn.commit()
    conn.close()

# Eliminar rostro en Hikvision
def delete_face(employee_no, context):
    for devIndex in DEV_INDEXES:
        delete_url = f"http://{HOST}/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&devIndex={devIndex}"
        delete_payload = {
            "FaceInfoDelCond": {
                "faceLibType": "blackFD",
                "EmployeeNoList": [{"employeeNo": employee_no}]
            }
        }
        try:
            response = requests.put(delete_url, json=delete_payload, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=10)
            if response.status_code == 200:
                context.log(f"🗑️ Rostro eliminado para {employee_no} en dispositivo {devIndex}")
            else:
                context.log(f"⚠️ Error al eliminar rostro para {employee_no} en dispositivo {devIndex}: {response.text}")
        except requests.exceptions.RequestException as e:
            context.log(f"⚠️ Error en la solicitud DELETE para {employee_no} en dispositivo {devIndex}: {e}")

# Agregar nuevo rostro en Hikvision
def add_face(usuario, context):
    employee_no = usuario.get("employeeNo")
    image_url = usuario.get("faceURL")
    if not image_url:
        context.log(f"⚠️ El empleado {employee_no} no tiene una URL de imagen válida.")
        return
    
    try:
        context.log(f"Descargando imagen para empleado {employee_no}: {image_url}")
        img_data = requests.get(image_url, timeout=10).content
        
        if not img_data:
            context.log(f"⚠️ Error: No se pudo descargar correctamente la imagen para {employee_no}.")
            return
        
        file_type = mimetypes.guess_type(image_url)[0] or 'image/jpeg'
        face_info = {"FaceInfo": {"employeeNo": employee_no, "faceLibType": "blackFD"}}
        files = {'FaceDataRecord': ("face.jpg", img_data, file_type)}
        data = {'data': json.dumps(face_info)}
        
        for devIndex in DEV_INDEXES:
            create_url = f"http://{HOST}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json&devIndex={devIndex}"
            response = requests.post(create_url, data=data, files=files, auth=HTTPDigestAuth(USERNAME, PASSWORD), timeout=10)
            if response.status_code == 200:
                context.log(f"✅ Rostro agregado correctamente para {employee_no} en dispositivo {devIndex}")
            else:
                context.log(f"❌ Error al agregar rostro para {employee_no} en dispositivo {devIndex}: {response.text}")
    except Exception as e:
        context.log(f"⚠️ Error al procesar imagen para {employee_no}: {e}")

# Comparar usuarios y actualizar Hikvision
def sync_users(context):
    new_users = get_sap_users()
    stored_users = get_stored_users()
    
    changed_users = [u for u in new_users if u["employeeNo"] in stored_users and stored_users[u["employeeNo"]] != u["faceURL"]]
    
    if changed_users:
        context.log(f"Usuarios con cambios en la imagen: {[u['employeeNo'] for u in changed_users]}")
        for user in changed_users:
            delete_face(user["employeeNo"], context)
            add_face(user, context)
    else:
        context.log("No hay cambios en las imágenes de los usuarios.")
    
    update_database(new_users)
    context.log("Proceso completado.")

# Análisis principal
def my_analysis(context, scope):
    context.log('Iniciando análisis...')
    sync_users(context)

# Inicializar la base de datos e iniciar el análisis
init_db()
ANALYSIS_TOKEN = 'a-bf743737-88be-41d7-a6be-edfc32dac943'
Analysis(ANALYSIS_TOKEN).init(my_analysis)
