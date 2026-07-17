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

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cruz_morada_api")


# Lifespan para cargar los datos en memoria al levantar el server
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("Iniciando aplicación Cruz Morada Estadísticas API")
    logger.info("==================================================")

    t_start = time.time()
    try:
        # Carga paralela del CSV
        df = cargar_datos_parallel()
        app.state.df = df
        t_duration = time.time() - t_start
        logger.info(f"Datos listos para consultas. Tiempo de carga: {t_duration:.2f}s")
    except Exception as e:
        logger.critical(f"Error crítico al iniciar la app: {str(e)}", exc_info=True)
        import pandas as pd
        app.state.df = pd.DataFrame()  # Fallback vacío si falla

    yield
    logger.info("Apagando servidor Cruz Morada API...")


app = FastAPI(
    title="Cruz Morada — API de Resumen Estadístico",
    description="Servicio REST para obtener estadísticas descriptivas de las ventas en Cruz Morada.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (se desactivan credentials porque allow_origins es "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# Helper para obtener timestamp en formato ISO 8601 UTC
def obtener_utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


# Handlers para errores personalizados según la pauta del trabajo

@app.exception_handler(APIValidationError)
async def api_validation_error_handler(request: Request, exc: APIValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.detail,
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


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    # Formatea los errores de validación de pydantic en un solo string
    errors_list = exc.errors()
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
    # Controla excepciones de tipo HTTP y formatea su salida
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
    # Captura cualquier error no controlado y devuelve HTTP 500
    logger.error(
        f"Error interno en {request.method} {request.url.path}: {str(exc)}",
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
            "errorCode": "IE",
            "errorLabel": "Error Interno",
            "method": request.method
        }
    )