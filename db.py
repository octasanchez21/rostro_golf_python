import sqlite3

db_path = "sap_users.db"

def ver_usuarios():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()

    if usuarios:
        for usuario in usuarios:
            print(usuario)
    else:
        print("⚠️ No hay usuarios en la base de datos.")

ver_usuarios()
