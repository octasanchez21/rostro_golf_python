from flask import Flask, request, jsonify
import os
import requests
import mimetypes
import json
from urllib import request as url_request
from tago import Analysis
from requests.auth import HTTPDigestAuth

app = Flask(__name__)

# Configuración
host = "34.221.158.219"
devIndex = "F5487AA0-2485-4CFB-9304-835DCF118B43"
url_delete_face = f"http://{host}/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&devIndex={devIndex}"
url_create_face = f"http://{host}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json&devIndex={devIndex}"
username = 'admin'
password = 'Inteliksa6969'

# Sincronización de usuarios
def sync_users(context):

    # Procesar rostros
    for usuario in usuarios_sap: # Itera sobre los usuarios de SAP
        employee_no = usuario.get("employeeNo") # Obtiene el numero de empleado actual.
        if not employee_no: # Si el usuario no tiene "employee_no" se saltea este usuario
            continue

        # Eliminar rostro existente
        delete_payload = { # Contrucción del payload para eliminar rostro
            "FaceInfoDelCond": {
                "faceLibType": "blackFD",
                "EmployeeNoList": [{"employeeNo": employee_no}] # Solo se incluye el numero de empleado del usuario actual.
            }
        }
        try:
            response = requests.put(url_delete_face, json=delete_payload, auth=HTTPDigestAuth(username, password), timeout=10)
            if response.status_code == 200:
                context.log(f"🗑️ Rostro eliminado para empleado {employee_no}")
            else:
                context.log(f"⚠️ Error al eliminar rostro para {employee_no}: {response.text}")
        except requests.exceptions.RequestException as e:
            context.log(f"⚠️ Error en la solicitud DELETE para {employee_no}: {e}")

    # Filtrar usuarios que tienen faceURL en SAP (para subir nuevos rostros)
    usuarios_a_subir = [u for u in usuarios_sap if u.get("faceURL")] # Crea nueva lista que contiene los usuarios de SAP con "faceURL"
    context.log(f"Usuarios a subir: {len(usuarios_a_subir)}") 

    # Subir imágenes a Hikvision
    for usuario in usuarios_a_subir:
        image_url = usuario.get("faceURL") # Obtiene la URL de la imagen
        employee_no = usuario.get("employeeNo") # Obtiene el "employeeNo" del usuario
        if not image_url: # Si el usuario no tiene "URL" valida se salta este usuario.
            context.log(f"Error: El empleado {employee_no} no tiene una URL de imagen válida.")
            continue

        temp_image_path = f"{employee_no}.jpg" # Usa el "employee_no" para nombrar temporalmente el archivo que se va descargar
        context.log(f"Descargando imagen para empleado {employee_no}: {image_url}")
        try:
            # Descargar imagen
            request.urlretrieve(image_url, temp_image_path) # Descarga la imagen desde la URL y se guarda con el nombre temporal

            # Verificar que la imagen se haya guardado correctamente
            # "os.path.exists(temp_image_path)" verifica que el archivo exista
            # "os.path.getsize(temp_image_path)" verifica si el archivo tiene un tamaño mayor a cero
            if not os.path.exists(temp_image_path) or os.path.getsize(temp_image_path) == 0:
                context.log(f"Error: No se pudo descargar correctamente la imagen para {employee_no}.")
                continue

            # Leer la imagen
            with open(temp_image_path, "rb") as img_file: # Abre el archivo en modo binario "rb" y lee su contenido
                img_data = img_file.read() # Guarda los datos de la imagen en la variable "img_data"

            file_type = mimetypes.guess_type(temp_image_path)[0] or 'image/jpeg' # Determina el tipo MIME de la imagen

            # Datos de FaceInfo para Hikvision
            face_info = {
                "FaceInfo": {
                    "employeeNo": employee_no,
                    "faceLibType": "blackFD"
                }
            }

            # Enviar la imagen a Hikvision
            files = {'FaceDataRecord': ("face.jpg", img_data, file_type)}
            data = {'data': json.dumps(face_info)}
            response = requests.post(url_create_face, data=data, files=files, auth=HTTPDigestAuth(username, password), timeout=10) # ENVIO DE IMAGEN
            if response.status_code == 200:
                context.log(f"✅ Rostro agregado correctamente para {employee_no}")
            else:
                context.log(f"❌ Error al agregar rostro para {employee_no}: {response.text}")
        except Exception as e:
            context.log(f"⚠️ Error al procesar imagen para {employee_no}: {e}")
        finally:
            # Eliminar archivo temporal después de usarlo
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                context.log(f"🗑️ Archivo temporal eliminado: {temp_image_path}")

    context.log("Proceso completado.")
@app.route('/sync', methods=['POST'])
def sync():
    sync_users()
    return jsonify({"status": "success", "message": "Sincronización completada"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
# Análisis principal
def my_analysis(context, scope):
    context.log('Iniciando análisis...')
    context.log('Alcance del análisis:', scope)
    sync_users(context)

# Inicializar el análisis
ANALYSIS_TOKEN = 'a-6d6726c2-f167-4610-a9e5-5a08a92b6bb3'  # Reemplaza con tu token de análisis de TagoIO
Analysis(ANALYSIS_TOKEN).init(my_analysis)