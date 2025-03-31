import os
import requests
import mimetypes
import json
from concurrent.futures import ThreadPoolExecutor
from tago import Analysis
from requests.auth import HTTPDigestAuth

# Configuración
host = "34.221.158.219"
devIndexes = [
    "F5487AA0-2485-4CFB-9304-835DCF118B43",  # Primer dispositivo
    "08395809-0EFA-48EA-B37F-DC628A83398A"   # Segundo dispositivo (ejemplo, reemplazar con el real)
]
username = 'admin'
password = 'Inteliksa6969'

# Endpoint y headers para obtener los datos de SAP
sap_url = "http://localhost:3000/get-socios"
sap_headers = {"Authorization": "SKIntegracionXetuxTruoraAPIREST#.01"}


def get_sap_users():
    try:
        response = requests.get(sap_url, headers=sap_headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or "contenido" not in data:
            print("⚠️ Respuesta inesperada de SAP API: formato incorrecto")
            return []
        return [u for u in data.get("contenido", []) if u.get("employeeNo")]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error al obtener usuarios de SAP: {e}")
        return []


def process_user_for_device(usuario, devIndex, context):
    employee_no = usuario.get("employeeNo")
    image_url = usuario.get("faceURL")
    if not image_url:
        context.log(f"Error: El empleado {employee_no} no tiene una URL de imagen válida.")
        return
    
    try:
        context.log(f"Descargando imagen para empleado {employee_no}: {image_url}")
        img_data = requests.get(image_url, timeout=10).content
        
        if not img_data:
            context.log(f"Error: No se pudo descargar correctamente la imagen para {employee_no}.")
            return
        
        file_type = mimetypes.guess_type(image_url)[0] or 'image/jpeg'
        face_info = {"FaceInfo": {"employeeNo": employee_no, "faceLibType": "blackFD"}}
        files = {'FaceDataRecord': ("face.jpg", img_data, file_type)}
        data = {'data': json.dumps(face_info)}
        
        url_create_face = f"http://{host}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json&devIndex={devIndex}"
        response = requests.post(url_create_face, data=data, files=files, auth=HTTPDigestAuth(username, password), timeout=10)
        
        if response.status_code == 200:
            context.log(f"✅ Rostro agregado correctamente para {employee_no} en dispositivo {devIndex}")
        else:
            context.log(f"❌ Error al agregar rostro para {employee_no} en dispositivo {devIndex}: {response.text}")
    except Exception as e:
        context.log(f"⚠️ Error al procesar imagen para {employee_no} en dispositivo {devIndex}: {e}")


def process_user(usuario, context):
    for devIndex in devIndexes:
        process_user_for_device(usuario, devIndex, context)


def sync_users(context):
    usuarios_sap = get_sap_users()
    if not usuarios_sap:
        context.log("⚠️ No se encontraron usuarios en SAP o error en la respuesta.")
        return
    
    context.log(f"Usuarios a subir: {len(usuarios_sap)}")
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(lambda usuario: process_user(usuario, context), usuarios_sap)
    
    context.log("Proceso completado.")


# Análisis principal
def my_analysis(context, scope):
    context.log('Iniciando análisis...')
    context.log('Alcance del análisis:', scope)
    sync_users(context)

# Inicializar el análisis
ANALYSIS_TOKEN = 'a-bf743737-88be-41d7-a6be-edfc32dac943'
Analysis(ANALYSIS_TOKEN).init(my_analysis)
