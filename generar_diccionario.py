"""
Genera un CSV (Idioma,Palabra,Traducción) con las N palabras más comunes
de inglés, alemán, italiano y ruso, traducidas al español.

Fuente de las listas de frecuencia:
  FrequencyWords (Hermit Dave) - https://github.com/hermitdave/FrequencyWords
  Listas basadas en subtítulos de cine/TV, ordenadas por frecuencia real de uso.

Traducción:
  deep-translator (usa el motor de Google Translate, sin necesidad de API key).

Instalación de dependencias:
  pip install requests deep-translator

Uso:
  python generar_diccionario.py
  python generar_diccionario.py --n 1000 --out diccionario.csv
"""

import argparse
import csv
import sys
import time

import requests
from deep_translator import GoogleTranslator

# --- Configuración de idiomas -------------------------------------------------
# code_freq: código usado en el repositorio FrequencyWords
# code_translate: código usado por Google Translate (deep-translator)
# nombre: cómo se mostrará en la columna "Idioma" del CSV
IDIOMAS = [
    {"nombre": "Inglés",   "code_freq": "en", "code_translate": "en"},
    {"nombre": "Alemán",   "code_freq": "de", "code_translate": "de"},
    {"nombre": "Italiano", "code_freq": "it", "code_translate": "it"},
    {"nombre": "Ruso",     "code_freq": "ru", "code_translate": "ru"},
]

FREQ_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
    "master/content/2018/{code}/{code}_50k.txt"
)


def descargar_lista_frecuencia(code_freq: str, n: int) -> list[str]:
    """Descarga la lista de frecuencia y devuelve las N primeras palabras únicas."""
    url = FREQ_URL_TEMPLATE.format(code=code_freq)
    print(f"  Descargando lista de frecuencia: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    palabras = []
    vistas = set()
    for linea in resp.text.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        # Cada línea tiene el formato: "palabra recuento"
        partes = linea.split(" ")
        if not partes:
            continue
        palabra = partes[0].strip().lower()

        # Filtros básicos de limpieza: solo letras (incluye acentos/cirílico),
        # sin dígitos ni símbolos, evitando duplicados.
        if not palabra.isalpha():
            continue
        if palabra in vistas:
            continue

        vistas.add(palabra)
        palabras.append(palabra)

        if len(palabras) >= n:
            break

    return palabras


def traducir_palabras(palabras: list[str], code_translate: str, pausa: float = 0.0) -> list[str]:
    """Traduce una lista de palabras al español, una a una (con reintentos)."""
    traductor = GoogleTranslator(source=code_translate, target="es")
    traducciones = []

    for i, palabra in enumerate(palabras, start=1):
        traduccion = None
        for intento in range(3):
            try:
                traduccion = traductor.translate(palabra)
                break
            except Exception as e:
                print(f"    aviso: fallo al traducir '{palabra}' (intento {intento+1}/3): {e}")
                time.sleep(1.5)
        if not traduccion:
            traduccion = ""  # deja vacío si falla tras los reintentos; se puede repasar a mano

        traducciones.append(traduccion)

        if i % 50 == 0:
            print(f"    traducidas {i}/{len(palabras)}")

        if pausa:
            time.sleep(pausa)

    return traducciones


def main():
    parser = argparse.ArgumentParser(description="Genera un diccionario CSV multilingüe.")
    parser.add_argument("--n", type=int, default=1000, help="Número de palabras por idioma (por defecto 1000)")
    parser.add_argument("--out", type=str, default="diccionario.csv", help="Nombre del fichero CSV de salida")
    parser.add_argument("--pausa", type=float, default=0.0, help="Pausa en segundos entre peticiones de traducción")
    args = parser.parse_args()

    filas = []  # (Idioma, Palabra, Traducción)

    for idioma in IDIOMAS:
        print(f"\nProcesando {idioma['nombre']}...")
        try:
            palabras = descargar_lista_frecuencia(idioma["code_freq"], args.n)
        except requests.RequestException as e:
            print(f"  ERROR descargando la lista de {idioma['nombre']}: {e}", file=sys.stderr)
            continue

        print(f"  {len(palabras)} palabras obtenidas. Traduciendo...")
        traducciones = traducir_palabras(palabras, idioma["code_translate"], pausa=args.pausa)

        for palabra, traduccion in zip(palabras, traducciones):
            filas.append((idioma["nombre"], palabra, traduccion))

    print(f"\nEscribiendo {len(filas)} filas en {args.out}...")
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Idioma", "Palabra", "Traducción"])
        writer.writerows(filas)

    print("Listo.")


if __name__ == "__main__":
    main()
