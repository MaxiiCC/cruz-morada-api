# Cruz Morada — API de Resumen Estadístico de Ventas

Servicio REST diseñado en **FastAPI** para calcular y consultar estadísticas descriptivas en tiempo real (suma, conteo, promedio, mínimo, máximo, mediana y desviación estándar) sobre los montos de ventas de farmacias Cruz Morada. 

El servicio incluye carga de datos desatendida al inicio mediante procesamiento paralelo con fragmentación (*chunking*).

---

## Estructura del Proyecto

```
cruz-morada-api/
├── src/
│   ├── __init__.py
│   ├── main.py          # Inicialización, lifespans, middleware y manejadores de errores
│   ├── config.py        # Constantes, configuraciones de variables de entorno y mapeos
│   ├── carga.py         # Carga paralela y preprocesamiento de datos por chunks
│   ├── estadisticas.py  # Fórmulas de cálculo estadístico (mediana par, std poblacional, etc.)
│   ├── filtros.py       # Aplicación de filtros lógicos AND al DataFrame en memoria
│   ├── routes.py       # Definición de endpoints GET y POST con sus controladores
│   ├── validaciones.py  # Reglas de validación de campos y control de tipos
│   └── modelos.py       # Esquemas de datos Pydantic para entrada/salida y documentación
├── tests/
│   └── test_api.py      # Pruebas unitarias de endpoints y validadores
├── datos.json             # Casos de prueba y payloads de ejemplo exigidos
├── data/                # Carpeta para colocar ventas_completas.csv
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Requisitos de Instalación (Ubuntu 24.04 LTS y Windows)

Asegúrate de contar con **Python 3.10** o superior y `pip` instalado.

### 1. Clonar e ingresar al directorio
```bash
git clone https://github.com/MaxiiCC/cruz-morada-api.git
cd cruz-morada-api
```

### 2. Configurar entorno virtual e instalar dependencias

**En Ubuntu / GNU/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**En Windows (PowerShell):**
```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Crea el archivo `.env` copiando la plantilla de ejemplo:

```bash
# Ubuntu
cp .env.example .env

# Windows
Copy-Item .env.example .env
```

El archivo `.env` contiene:
- `CPYD_CSV_PATH`: Ruta al archivo CSV. Por defecto es `data/ventas_completas.csv`.

### 4. Colocar el archivo de datos
Coloca el dataset dentro de la carpeta `data/` del proyecto. El sistema soporta ambos formatos:
- `data/ventas_completas.csv` — archivo descomprimido
- `data/ventas_completas.csv.gz` — archivo comprimido (se lee directo, sin necesidad de descomprimir)

> [!NOTE]
> Aunque el enunciado teórico del laboratorio indica que las columnas del CSV están "separadas por comas", el dataset real oficial distribuido para Cruz Morada utiliza **punto y coma (`;`)** como separador de columnas. El cargador de datos (`carga.py`) ha sido ajustado a este formato real para evitar fallos de lectura.


---

## Ejecución del Servidor

Levanta la API usando `uvicorn` desde la raíz del proyecto:

**En Linux / macOS:**
```bash
python3 -m uvicorn src.main:app --reload --port 8000
```

**En Windows (PowerShell):**
```powershell
python -m uvicorn src.main:app --reload --port 8000
```

Al iniciar, el servidor ejecutará la carga paralela desatendida del CSV. Verás en el log el progreso y la cantidad de filas cargadas en memoria.

---

## Documentación Interactiva (Swagger)

Una vez iniciado el servidor, puedes acceder a la documentación interactiva autogenerada:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Ejemplos de Consultas (cURL)

### 1. Consulta GET sin filtros
```bash
curl http://localhost:8000/v1/estadisticas/ventas
```

### 2. Consulta GET con filtros
```bash
curl "http://localhost:8000/v1/estadisticas/ventas?CANAL=POS&LOCAL=1999&GENERO=Femenino"
```

### 3. Consulta POST con filtros válidos
```bash
curl -X POST http://localhost:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{
    "consultas": [
      {"consulta": "GENERO", "valor": "Femenino"},
      {"consulta": "EDAD", "valor": "31"},
      {"consulta": "CANAL", "valor": "POS"}
    ]
  }'
```

### 4. Consulta POST con error de validación (Filtro inexistente)
```bash
curl -X POST http://localhost:8000/v1/estadisticas/ventas \
  -H "Content-Type: application/json" \
  -d '{
    "consultas": [
      {"consulta": "CAMPO_ERRONEO", "valor": "POS"}
    ]
  }'
```

---

## Pruebas y Validación

### 1. Pruebas Unitarias Automatizadas (con Pytest)
Para ejecutar la suite de 22 pruebas unitarias automatizadas sobre los controladores y el motor de estadísticas:

**En Linux / macOS:**
```bash
pytest -v
```

**En Windows (PowerShell):**
```powershell
python -m pytest -v
```

### 2. Pruebas Funcionales en Vivo (PowerShell - Solo Windows)
Si el servidor de la API está encendido, puedes ejecutar la suite completa de 38 pruebas de integración y validación en vivo corriendo:
```powershell
.\test_manual_completo.ps1
```

---

## Integrantes
- Martin Cerda Fernandez
- Maximiliano Campos Camimil
