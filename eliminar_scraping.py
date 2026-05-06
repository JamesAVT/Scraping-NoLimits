import requests
import os
import time

BASE_URL = os.getenv(
    "API_URL",
    "https://nolimits-backend-final.onrender.com/api/v1"
)

API_URL = f"{BASE_URL}/productos"
PAGINACION_URL = f"{API_URL}/paginacion"

TOKEN = os.getenv("JWT_TOKEN")

if not TOKEN:
    raise Exception(
        "Falta JWT_TOKEN.\n"
        'Usa en PowerShell:\n$env:JWT_TOKEN="tu_token"'
    )

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ================= OBTENER TODOS LOS PRODUCTOS =================
productos = []
page = 1
size = 50

while True:
    resp = requests.get(
        f"{PAGINACION_URL}?page={page}&size={size}",
        headers=headers,
        timeout=30
    )

    if resp.status_code != 200:
        print("❌ Error al obtener productos:", resp.status_code, resp.text)
        exit()

    data = resp.json()
    contenido = data.get("contenido", [])
    total_paginas = data.get("totalPaginas", 1)

    productos.extend(contenido)

    if page >= total_paginas:
        break

    page += 1

print(f"📦 Total productos encontrados: {len(productos)}")

# ================= ELIMINAR TODOS =================
eliminados = 0
errores = 0

for p in productos:
    id_producto = p.get("id")
    nombre = p.get("nombre", "sin nombre")

    try:
        r = requests.delete(
            f"{API_URL}/{id_producto}",
            headers=headers,
            timeout=60
        )

        if r.status_code == 204:
            print(f"🗑 Eliminado: {nombre}")
            eliminados += 1
        else:
            print(f"❌ Error al eliminar {nombre}: {r.status_code} → {r.text}")
            errores += 1

    except requests.exceptions.Timeout:
        print(f"⏳ Timeout eliminando {nombre}. Se continúa con el siguiente.")
        errores += 1

    except Exception as e:
        print(f"❌ Error eliminando {nombre}: {e}")
        errores += 1

    time.sleep(0.2)

print("\n📊 RESUMEN")
print(f"🗑 Eliminados: {eliminados}")
print(f"❌ Errores: {errores}")