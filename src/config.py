import os
from pathlib import Path
from dotenv import load_dotenv

# Carga variables del .env si existe
load_dotenv()

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = BASE_DIR / "data" / "ventas_completas.csv"
CPYD_CSV_PATH = os.getenv("CPYD_CSV_PATH", str(DEFAULT_CSV_PATH))

# Canales de venta permitidos
CANALES_PERMITIDOS = {"POS", "WEB", "APP", "CCT", "APR", "WPR"}

# Generos para filtros y mapeo desde el CSV
GENEROS_PERMITIDOS = {"No especificado", "Masculino", "Femenino", "Otro"}
GENERO_MAP = {
    1: "Masculino",
    2: "Femenino"
}
