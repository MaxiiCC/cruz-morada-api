"""
config.py — Configuración General del Proyecto

Este archivo es el punto central de configuración de toda la aplicación.
Aquí se definen las constantes y se leen las variables de entorno que el
usuario puede personalizar sin tocar el código fuente (solo editando el
archivo .env en la raíz del proyecto).

Si quieres cambiar la ruta del CSV, solo edita el archivo .env.
No es necesario modificar nada más.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar las variables definidas en el archivo .env (si existe en el proyecto).
# Esto permite que el usuario configure la aplicación sin tocar el código.
load_dotenv()

# ─── RUTAS DEL PROYECTO ──────────────────────────────────────────────────────

# Calculamos la ruta base del proyecto de forma automática.
# __file__ es la ruta de este archivo (config.py), que está dentro de src/.
# Con .parent.parent subimos dos niveles hasta llegar a la carpeta raíz del proyecto.
BASE_DIR = Path(__file__).resolve().parent.parent

# Ruta por defecto al archivo CSV de ventas.
# Si el usuario no define CPYD_CSV_PATH en su .env, se usará esta ruta.
DEFAULT_CSV_PATH = BASE_DIR / "data" / "ventas_completas.csv"

# Leemos la ruta del CSV desde las variables de entorno.
# Si no existe la variable CPYD_CSV_PATH en el archivo .env, usamos la ruta por defecto.
# Ejemplo de .env: CPYD_CSV_PATH=data/ventas_completas.csv
CPYD_CSV_PATH = os.getenv("CPYD_CSV_PATH", str(DEFAULT_CSV_PATH))

# ─── VALORES PERMITIDOS PARA LOS FILTROS ─────────────────────────────────────

# Lista de canales de venta válidos según los datos de Cruz Morada.
# Si se recibe un canal diferente a estos en una consulta, la API rechazará
# la petición con un error 400 (Validación Fallida).
CANALES_PERMITIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}

# Géneros válidos que puede recibir la API como filtro de texto.
# Nota: en el CSV los géneros vienen como números (1 o 2), pero la API
# los expone al usuario de forma legible (Masculino, Femenino, etc.).
GENEROS_PERMITIDOS = {"No especificado", "Masculino", "Femenino", "Otro"}

# Tabla de conversión entre el número del género (tal como viene en el CSV)
# y su equivalente en texto legible.
# - 1 en el CSV → "Masculino" en la API
# - 2 en el CSV → "Femenino" en la API
# - Cualquier otro valor → "No especificado" (lo maneja el cargador de datos)
GENERO_MAP = {
    1: "Masculino",
    2: "Femenino"
}
