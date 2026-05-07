import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime

# ================= CONFIG =================
BASE_URL = os.getenv(
    "API_URL",
    "https://nolimits-backend-final.onrender.com/api/v1"
)

API_URL = f"{BASE_URL}/productos"
LOGIN_URL = f"{BASE_URL}/auth/login"

TIPOS_URL = f"{BASE_URL}/tipo-productos"
PLATAFORMAS_URL = f"{BASE_URL}/plataformas"
CLASIFICACIONES_URL = f"{BASE_URL}/clasificaciones"
ESTADOS_URL = f"{BASE_URL}/estados"

# ================= TOKEN AUTOMÁTICO =================
def obtener_token():
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        raise Exception(
            "Faltan credenciales.\n"
            'Usa:\n$env:ADMIN_EMAIL="tu_email"\n$env:ADMIN_PASSWORD="tu_password"'
        )

    resp = requests.post(
        LOGIN_URL,
        json={"email": email, "password": password},
        timeout=10
    )

    if resp.status_code != 200:
        raise Exception(f"Login fallido: {resp.status_code} → {resp.text}")

    token = resp.json().get("token")

    if not token:
        raise Exception("No se recibió token")

    print("✅ Token obtenido correctamente")
    return token


TOKEN = os.getenv("JWT_TOKEN") or obtener_token()

headers_backend = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ================= CATÁLOGOS DINÁMICOS =================
def normalizar(texto):
    return texto.lower().strip()


def obtener_catalogo(url, nombre_catalogo):
    resp = requests.get(url, headers=headers_backend, timeout=10)

    if resp.status_code != 200:
        raise Exception(f"No se pudo obtener {nombre_catalogo}: {resp.status_code}")

    data = resp.json()

    mapa = {
        normalizar(item["nombre"]): item["id"]
        for item in data
    }

    print(f"✅ {nombre_catalogo} cargado:", mapa)
    return mapa


TIPOS = obtener_catalogo(TIPOS_URL, "tipos de producto")
PLATAFORMAS = obtener_catalogo(PLATAFORMAS_URL, "plataformas")
CLASIFICACIONES = obtener_catalogo(CLASIFICACIONES_URL, "clasificaciones")
ESTADOS = obtener_catalogo(ESTADOS_URL, "estados")

TIPO_PELICULA = TIPOS.get("película")
PLATAFORMA_ML = PLATAFORMAS.get("mercado libre")
CLASIFICACION_ID = CLASIFICACIONES.get("pg-13")
ESTADO_ID = ESTADOS.get("disponible")

if not TIPO_PELICULA:
    raise Exception("No se encontró el tipo: Película.")

if not PLATAFORMA_ML:
    raise Exception("No se encontró la plataforma Mercado Libre.")

if not CLASIFICACION_ID:
    raise Exception("No se encontró la clasificación PG-13.")

if not ESTADO_ID:
    raise Exception("No se encontró el estado Disponible.")

# ================= SCRAPER =================
def scrapear_harry_potter_coleccion():
    busqueda = "harry potter coleccion 8 peliculas blu ray"
    query = busqueda.replace(" ", "-")
    url = f"https://listado.mercadolibre.cl/{query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        print(f"❌ Error conexión Mercado Libre: {e}")
        return []

    if response.status_code != 200:
        print(f"❌ Error al conectar con Mercado Libre: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    productos = soup.select("li.ui-search-layout__item")

    print(f"🔎 '{busqueda}' → {len(productos)} encontrados")

    for producto in productos:
        nombre_tag = producto.select_one("h3.poly-component__title-wrapper a")
        precio_tag = producto.select_one(".andes-money-amount__fraction")

        if not nombre_tag:
            continue

        nombre = nombre_tag.text.strip()
        nombre_lower = nombre.lower()

        # Debe ser una colección de Harry Potter con 8 películas
        if "harry potter" not in nombre_lower:
            continue

        if not (
            "coleccion" in nombre_lower
            or "colección" in nombre_lower
            or "8 peliculas" in nombre_lower
            or "8 películas" in nombre_lower
            or "8-films" in nombre_lower
            or "8 films" in nombre_lower
        ):
            continue

        if "usado" in nombre_lower:
            continue

        if len(nombre) > 100:
            nombre = nombre[:97] + "..."

        link = nombre_tag.get("href", "").split("#")[0]

        precio = 0
        if precio_tag:
            precio_texto = precio_tag.text.strip().replace(".", "")
            if precio_texto.isdigit():
                precio = int(precio_texto)

        producto_final = {
            "nombre": nombre,
            "precio": float(precio),
            "sinopsis": "",
            "urlTrailer": "",
            "tipoProductoId": TIPO_PELICULA,
            "clasificacionId": CLASIFICACION_ID,
            "estadoId": ESTADO_ID,
            "saga": "Harry Potter",
            "portadaSaga": "",
            "plataformasIds": [PLATAFORMA_ML],
            "generosIds": [],
            "empresasIds": [],
            "desarrolladoresIds": [],
            "imagenesRutas": [],
            "linksCompra": [
                {
                    "plataformaId": PLATAFORMA_ML,
                    "url": link,
                    "label": "Mercado Libre",
                    "precio": float(precio),
                    "precioActual": float(precio)
                }
            ]
        }

        return [producto_final]

    return []


# ================= EJECUCIÓN =================
todos_los_productos = scrapear_harry_potter_coleccion()

print(f"\n📦 Total productos scrapeados: {len(todos_los_productos)}")

# ================= EXPORT =================
fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

df = pd.DataFrame(todos_los_productos)

df.to_csv(f"productos_{fecha}.csv", index=False, encoding="utf-8-sig")
print("✅ CSV creado")

df.to_json(f"productos_{fecha}.json", orient="records", force_ascii=False, indent=4)
print("✅ JSON creado")

# ================= ENVÍO AL BACKEND =================
print("\n🚀 Enviando al backend...")

exitosos = 0
duplicados = 0
errores = 0

for producto in todos_los_productos:
    try:
        respuesta = requests.post(
            API_URL,
            json=producto,
            headers=headers_backend,
            timeout=10
        )

        if respuesta.status_code == 201:
            print(f"✅ Creado: {producto['nombre']}")
            exitosos += 1

        elif respuesta.status_code in [409, 500]:
            print(f"⚠️ Duplicado/rechazado: {producto['nombre']}")
            duplicados += 1

        else:
            print(f"❌ Error {respuesta.status_code}: {producto['nombre']} → {respuesta.text}")
            errores += 1

    except Exception as e:
        print(f"❌ Error conexión: {producto['nombre']} → {e}")
        errores += 1

print("\n📊 RESUMEN FINAL")
print(f"✅ Creados: {exitosos}")
print(f"⚠️ Duplicados/rechazados: {duplicados}")
print(f"❌ Errores: {errores}")