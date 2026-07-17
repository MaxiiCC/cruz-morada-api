"""
routes.py — Definición de los Endpoints de la API

Este módulo contiene la implementación de las dos rutas (endpoints) principales
del servicio REST de Cruz Morada:

- GET  /v1/estadisticas/ventas: El usuario envía los filtros como parámetros
  en la URL (query params). Ejemplo:
  http://localhost:8000/v1/estadisticas/ventas?CANAL=POS&LOCAL=371

- POST /v1/estadisticas/ventas: El usuario envía los filtros en el cuerpo (body)
  de la petición en formato JSON. Más flexible para combinaciones complejas.

Ambos endpoints producen exactamente el mismo tipo de respuesta (las 7 métricas
estadísticas) y pasan por el mismo flujo de validación → filtrado → cálculo.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from src.modelos import VentasResponse, ConsultaRequest, ErrorResponse
from src.validaciones import validar_y_mapear_filtros, APIValidationError
from src.filtros import aplicar_filtros
from src.estadisticas import calcular_estadisticas

# Logger para registrar eventos de las rutas (errores, advertencias, etc.)
logger = logging.getLogger("cruz_morada_api")

# El router es el objeto de FastAPI que agrupa y registra los endpoints.
# Se incluye en la app principal desde main.py.
router = APIRouter()


@router.get(
    "/v1/estadisticas/ventas",
    response_model=VentasResponse,
    responses={
        200: {"description": "Estadísticas calculadas correctamente"},
        400: {"model": ErrorResponse, "description": "Validación fallida en los parámetros de entrada"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor al procesar la solicitud"}
    },
    summary="Obtener resumen estadístico vía GET",
    description="Devuelve estadísticas de ventas calculadas sobre MONTO APLICADO con base en filtros opcionales pasados como parámetros de consulta (query params)."
)
def get_estadisticas(
    request: Request,
    # Cada parámetro a continuación corresponde a un filtro opcional que el usuario
    # puede incluir en la URL. Todos son opcionales (Optional[str] con valor None por defecto).
    # FastAPI los extrae automáticamente de la URL y los pasa a esta función.
    genero: Optional[str] = Query(None, alias="GENERO", description="Género del cliente"),
    edad: Optional[str] = Query(None, alias="EDAD", description="Edad exacta en años"),
    canal: Optional[str] = Query(None, alias="CANAL", description="Canal de venta"),
    codigo_producto: Optional[str] = Query(None, alias="CODIGO_PRODUCTO", description="SKU del producto"),
    id_persona: Optional[str] = Query(None, alias="ID_PERSONA", description="UUID identificador del cliente"),
    local: Optional[str] = Query(None, alias="LOCAL", description="Número de local comercial"),
    fecha_desde: Optional[str] = Query(None, alias="FECHA_DESDE", description="Rango de fecha de compra (inicio)"),
    fecha_hasta: Optional[str] = Query(None, alias="FECHA_HASTA", description="Rango de fecha de compra (término)")
):
    """
    Endpoint GET: recibe los filtros como parámetros en la URL.

    Flujo de procesamiento:
    1. Recopila todos los parámetros de la URL en un diccionario.
    2. Elimina los que vengan como None (no enviados por el usuario).
    3. Valida y normaliza los filtros en validaciones.py.
    4. Aplica los filtros sobre el DataFrame en memoria en filtros.py.
    5. Calcula las estadísticas del conjunto filtrado en estadisticas.py.
    6. Devuelve el resultado en formato JSON.
    """

    # Paso 1: Recopilamos todos los parámetros en un diccionario.
    filtros_raw = {
        "GENERO": genero,
        "EDAD": edad,
        "CANAL": canal,
        "CODIGO_PRODUCTO": codigo_producto,
        "ID_PERSONA": id_persona,
        "LOCAL": local,
        "FECHA_DESDE": fecha_desde,
        "FECHA_HASTA": fecha_hasta
    }

    # Paso 2: Eliminamos los filtros que el usuario no envió (valor None).
    filtros_raw = {k: v for k, v in filtros_raw.items() if v is not None}

    # Paso 3: Validamos los filtros. Si alguno es inválido, APIValidationError
    # se propaga y main.py la convierte en una respuesta 400.
    try:
        filtros = validar_y_mapear_filtros(filtros_raw)
    except APIValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error inesperado en validación GET: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en la validación de filtros")

    # Paso 4 y 5: Filtramos y calculamos estadísticas.
    try:
        # Accedemos al DataFrame completo que fue cargado al iniciar la aplicación.
        # Está guardado en el estado global de la app FastAPI (app.state.df).
        df_completo = getattr(request.app.state, "df", None)
        if df_completo is None:
            raise ValueError("El DataFrame de ventas no está inicializado en la aplicación.")

        # Aplicamos los filtros para obtener el subconjunto de datos.
        df_filtrado = aplicar_filtros(df_completo, filtros)

        # Calculamos y retornamos las estadísticas sobre el subconjunto filtrado.
        stats_res = calcular_estadisticas(df_filtrado)
        return stats_res

    except Exception as e:
        logger.error(f"Error al calcular estadísticas en GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al calcular estadísticas: {str(e)}"
        )


@router.post(
    "/v1/estadisticas/ventas",
    response_model=VentasResponse,
    responses={
        200: {"description": "Estadísticas calculadas correctamente"},
        400: {"model": ErrorResponse, "description": "Validación fallida en el cuerpo JSON de la solicitud"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor al procesar la consulta"}
    },
    summary="Obtener resumen estadístico vía POST",
    description="Devuelve estadísticas de ventas calculadas sobre MONTO APLICADO con base en un listado de filtros dinámicos incluidos en el cuerpo de la petición (JSON)."
)
def post_estadisticas(request: Request, payload: ConsultaRequest):
    """
    Endpoint POST: recibe los filtros dentro del body JSON de la petición.

    Flujo de procesamiento:
    1. Verifica que la lista de consultas no sea nula ni esté vacía.
    2. Convierte la lista de objetos ConsultaItem a un diccionario plano.
    3. Valida y normaliza los filtros en validaciones.py.
    4. Aplica los filtros sobre el DataFrame en memoria en filtros.py.
    5. Calcula las estadísticas del conjunto filtrado en estadisticas.py.
    6. Devuelve el resultado en formato JSON.
    """

    # Paso 1: Verificamos que el body tenga consultas válidas.
    # Si la lista de consultas viene nula o vacía, es un error del usuario (400).
    if not payload or not payload.consultas or len(payload.consultas) == 0:
        raise APIValidationError("El campo 'consultas' no puede ser nulo o estar vacío.")

    # Paso 2: Convertimos la lista de ConsultaItem a un diccionario plano.
    # Ejemplo: [{"consulta": "CANAL", "valor": "POS"}] → {"CANAL": "POS"}
    filtros_raw = {}
    for item in payload.consultas:
        if not item.consulta or item.consulta.strip() == "":
            raise APIValidationError("El nombre del campo de consulta no puede estar vacío.")
        filtros_raw[item.consulta] = item.valor

    # Paso 3: Validamos los filtros. Si alguno es inválido, APIValidationError
    # se propaga y main.py la convierte en una respuesta 400.
    try:
        filtros = validar_y_mapear_filtros(filtros_raw)
    except APIValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error inesperado en validación POST: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al validar el esquema de filtros")

    # Paso 4 y 5: Filtramos y calculamos estadísticas.
    try:
        # Accedemos al DataFrame completo cargado al iniciar la aplicación.
        df_completo = getattr(request.app.state, "df", None)
        if df_completo is None:
            raise ValueError("El DataFrame de ventas no está inicializado en la aplicación.")

        # Aplicamos los filtros para obtener el subconjunto de datos.
        df_filtrado = aplicar_filtros(df_completo, filtros)

        # Calculamos y retornamos las estadísticas sobre el subconjunto filtrado.
        stats_res = calcular_estadisticas(df_filtrado)
        return stats_res

    except Exception as e:
        logger.error(f"Error al calcular estadísticas en POST: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al calcular estadísticas: {str(e)}"
        )
