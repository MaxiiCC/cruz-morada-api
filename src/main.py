"""
main.py — Punto de Entrada Principal de la Aplicación

Este es el archivo que orquesta y conecta todos los módulos del proyecto.
Es el archivo que se le pasa a uvicorn para arrancar el servidor.
Comando de ejecución: python -m uvicorn src.main:app --reload --port 8000

Sus responsabilidades principales son:

1. CARGA DESATENDIDA AL INICIO (lifespan):
   Cuando el servidor arranca, ANTES de aceptar cualquier petición HTTP,
   carga el archivo CSV completo usando el módulo carga.py y deja los datos
   en memoria para que las consultas sean instantáneas.

2. CONFIGURACIÓN DE LA APLICACIÓN (FastAPI):
   Inicializa FastAPI con título, descripción y versión para que aparezcan
   en la documentación Swagger (/docs).

3. REGISTRO DE RUTAS:
   Conecta el router con los endpoints GET y POST definidos en routes.py.

4. MANEJADORES DE ERRORES PERSONALIZADOS:
   Intercepta errores de validación y errores del servidor, y los convierte
   al formato de JSON exacto que exige la rúbrica del profesor.
"""

import time
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.routes import router
from src.carga import cargar_datos_parallel
from src.validaciones import APIValidationError

# ─── CONFIGURACIÓN DEL SISTEMA DE LOGGING ────────────────────────────────────
# Configuramos el sistema de mensajes de la consola para que muestre el
# timestamp, nivel (INFO, ERROR, CRITICAL) y el nombre del módulo en cada línea.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cruz_morada_api")


# ─── LIFESPAN: CARGA DESATENDIDA DEL CSV ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de ciclo de vida de la aplicación (Lifespan).

    El código ANTES del 'yield' se ejecuta al INICIAR el servidor.
    El código DESPUÉS del 'yield' se ejecuta al DETENER el servidor.

    Al inicio: carga los datos del CSV en memoria (app.state.df) antes
    de comenzar a aceptar peticiones HTTP. Esto garantiza que los datos
    siempre estén listos y disponibles sin intervención manual.

    Si la carga falla (ej: el CSV no existe), el servidor igual arranca
    pero con un DataFrame vacío, registrando el error en la consola.
    """
    logger.info("==================================================")
    logger.info("Iniciando aplicación Cruz Morada Estadísticas API")
    logger.info("==================================================")

    t_start = time.time()
    try:
        # Llamamos a la función de carga paralela definida en carga.py.
        # El resultado es un DataFrame con todos los datos limpios.
        df = cargar_datos_parallel()

        # Guardamos el DataFrame en el estado de la aplicación.
        # Desde aquí, cualquier endpoint puede acceder a él con request.app.state.df
        app.state.df = df

        t_duration = time.time() - t_start
        logger.info(f"Datos listos para consultas. Tiempo de carga: {t_duration:.2f}s")

    except Exception as e:
        # Si ocurre un error crítico durante la carga (ej: archivo no encontrado,
        # error de permisos), lo registramos pero no detenemos el servidor.
        logger.critical(f"ERROR CRÍTICO AL INICIAR APLICACIÓN: {str(e)}", exc_info=True)
        import pandas as pd
        app.state.df = pd.DataFrame()  # DataFrame vacío como fallback

    # El 'yield' marca el punto donde el servidor comienza a atender peticiones.
    yield

    # Código de cierre (se ejecuta al hacer CTRL+C para apagar el servidor).
    logger.info("Apagando servidor Cruz Morada API...")


# ─── INICIALIZACIÓN DE LA APLICACIÓN FASTAPI ─────────────────────────────────
app = FastAPI(
    title="Cruz Morada — API de Resumen Estadístico",
    description="Servicio REST para obtener estadísticas descriptivas de las ventas en Cruz Morada.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",     # Documentación Swagger disponible en http://localhost:8000/docs
    redoc_url="/redoc"    # Documentación ReDoc disponible en http://localhost:8000/redoc
)

# ─── MIDDLEWARE DE CORS ───────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) permite que la API sea accedida desde
# navegadores en dominios diferentes al del servidor (ej: un frontend en React).
# Por seguridad en producción, se debería restringir allow_origins a dominios específicos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REGISTRO DEL ROUTER ─────────────────────────────────────────────────────
# Conectamos el router de routes.py con la aplicación principal.
# Esto hace que los endpoints GET y POST sean accesibles en la ruta /v1/estadisticas/ventas.
app.include_router(router)


# ─── FUNCIÓN AUXILIAR: TIMESTAMP UTC ─────────────────────────────────────────
def obtener_utc_timestamp() -> str:
    """
    Genera un timestamp (marca de tiempo) en formato ISO 8601 con zona UTC.
    Se usa para incluir en todos los mensajes de error la hora exacta del fallo.
    Ejemplo de salida: "2026-07-12T23:35:32.434567Z"
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


# ─── MANEJADORES DE EXCEPCIONES PERSONALIZADOS ───────────────────────────────
# Estos manejadores capturan los errores que ocurren en cualquier parte de la
# aplicación y los convierten al formato de JSON exacto que exige la rúbrica.

@app.exception_handler(APIValidationError)
async def api_validation_error_handler(request: Request, exc: APIValidationError):
    """
    Maneja los errores de validación lanzados manualmente por validaciones.py
    y routes.py. Convierte la excepción en una respuesta HTTP 400 con el
    formato JSON exacto de la rúbrica (campos: detail, instance, status, etc.)
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.detail,
            "instance": request.url.path,
            "status": 400,
            "title": "Bad Request",
            "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
            "timestamp": obtener_utc_timestamp(),
            "errorCode": "VF",          # VF = Validación Fallida
            "errorLabel": "Validación Fallida",
            "method": request.method    # GET o POST según la petición
        }
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Maneja los errores de validación automáticos de Pydantic/FastAPI.
    Se activa cuando el body del POST no tiene el esquema correcto
    (ej: falta el campo "consultas" o tiene un tipo de dato incorrecto).
    También devuelve HTTP 400 con el formato de la rúbrica.
    """
    errors_list = exc.errors()

    # Construimos un mensaje descriptivo combinando todos los errores encontrados.
    detalles_error = []
    for err in errors_list:
        loc = " -> ".join([str(x) for x in err.get("loc", []) if x != "body"])
        msg = err.get("msg", "Formato inválido")
        detalles_error.append(f"[{loc}]: {msg}")

    detail = "; ".join(detalles_error) if detalles_error else "El cuerpo de la petición no tiene un formato válido"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": f"Error de validación de esquema: {detail}",
            "instance": request.url.path,
            "status": 400,
            "title": "Bad Request",
            "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
            "timestamp": obtener_utc_timestamp(),
            "errorCode": "VF",
            "errorLabel": "Validación Fallida",
            "method": request.method
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Maneja los errores HTTP estándar, tanto los que lanza FastAPI internamente
    (ej: 405 Method Not Allowed) como los que lanza el enrutador de Starlette
    cuando una ruta no existe (404 Not Found).

    NOTA IMPORTANTE: se registra sobre StarletteHTTPException (la clase base)
    y no sobre fastapi.exceptions.HTTPException (la subclase), porque el
    enrutador interno de Starlette lanza la excepción base directamente
    cuando una ruta no existe, y ese caso no dispararía un handler registrado
    solo sobre la subclase de FastAPI. Al registrar sobre la clase base,
    capturamos AMBOS casos con el mismo manejador (las HTTPException de
    FastAPI también matchean por herencia).
    """
    # Determinamos el título y código según el tipo de error HTTP.
    title = exc.detail
    error_code = "HE"
    error_label = "Error HTTP"

    if exc.status_code == 400:
        error_code = "VF"
        error_label = "Validación Fallida"
        title = "Bad Request"
    elif exc.status_code == 404:
        title = "Not Found"
        error_code = "RNF"
        error_label = "Recurso No Encontrado"
    elif exc.status_code == 405:
        title = "Method Not Allowed"
        error_code = "MNA"
        error_label = "Método No Permitido"
    elif exc.status_code == 500:
        title = "Internal Server Error"
        error_code = "IE"
        error_label = "Error Interno"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "instance": request.url.path,
            "status": exc.status_code,
            "title": title,
            "type": f"https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/{exc.status_code}",
            "timestamp": obtener_utc_timestamp(),
            "errorCode": error_code,
            "errorLabel": error_label,
            "method": request.method
        }
    )


@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception):
    """
    Manejador de último recurso para cualquier error no previsto que ocurra
    en la aplicación. Devuelve HTTP 500 (Error Interno del Servidor) con
    el formato de la rúbrica, evitando que el servidor se caiga o muestre
    trazas de error al usuario.
    """
    logger.error(
        f"Error interno del servidor en {request.method} {request.url.path}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Error interno al calcular estadísticas: {str(exc)}",
            "instance": request.url.path,
            "status": 500,
            "title": "Internal Server Error",
            "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500",
            "timestamp": obtener_utc_timestamp(),
            "errorCode": "IE",          # IE = Error Interno
            "errorLabel": "Error Interno",
            "method": request.method
        }
    )