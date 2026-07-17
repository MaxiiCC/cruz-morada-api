import logging
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from src.modelos import VentasResponse, ConsultaRequest, ErrorResponse
from src.validaciones import validar_y_mapear_filtros, APIValidationError
from src.filtros import aplicar_filtros
from src.estadisticas import calcular_estadisticas

logger = logging.getLogger("cruz_morada_api")
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
    description="Devuelve estadísticas de ventas calculadas sobre MONTO APLICADO con base en filtros opcionales."
)
def get_estadisticas(
    request: Request,
    genero: Optional[str] = Query(None, alias="GENERO", description="Género del cliente"),
    edad: Optional[str] = Query(None, alias="EDAD", description="Edad exacta en años"),
    canal: Optional[str] = Query(None, alias="CANAL", description="Canal de venta"),
    codigo_producto: Optional[str] = Query(None, alias="CODIGO_PRODUCTO", description="SKU del producto"),
    id_persona: Optional[str] = Query(None, alias="ID_PERSONA", description="UUID identificador del cliente"),
    local: Optional[str] = Query(None, alias="LOCAL", description="Número de local comercial"),
    fecha_desde: Optional[str] = Query(None, alias="FECHA_DESDE", description="Rango de fecha de compra (inicio)"),
    fecha_hasta: Optional[str] = Query(None, alias="FECHA_HASTA", description="Rango de fecha de compra (término)")
):
    # Validamos que no vengan query params no permitidos en la URL (GET)
    CAMPOS_PERMITIDOS = {
        "GENERO", "EDAD", "CANAL", "CODIGO_PRODUCTO",
        "ID_PERSONA", "LOCAL", "FECHA_DESDE", "FECHA_HASTA"
    }
    for param_name in request.query_params.keys():
        if param_name.strip().upper() not in CAMPOS_PERMITIDOS:
            raise APIValidationError(
                f"El campo de consulta '{param_name}' no está permitido. "
                f"Campos válidos: {', '.join(sorted(CAMPOS_PERMITIDOS))}"
            )

    # Recolectamos los parametros en un dict
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

    # Descartamos los None
    filtros_raw = {k: v for k, v in filtros_raw.items() if v is not None}

    try:
        filtros = validar_y_mapear_filtros(filtros_raw)
    except APIValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error inesperado en validación GET: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en la validación de filtros")

    try:
        df_completo = getattr(request.app.state, "df", None)
        if df_completo is None:
            raise ValueError("El DataFrame de ventas no está inicializado en la aplicación.")

        df_filtrado = aplicar_filtros(df_completo, filtros)
        stats_res = calcular_estadisticas(df_filtrado)
        return stats_res
    except Exception as e:
        logger.error(f"Error al calcular estadísticas en GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al calcular estadísticas."
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
    description="Devuelve estadísticas de ventas calculadas sobre MONTO APLICADO con base en un listado de filtros dinámicos."
)
def post_estadisticas(request: Request, payload: ConsultaRequest):
    if not payload.consultas or len(payload.consultas) == 0:
        raise APIValidationError("El campo 'consultas' no puede ser nulo o estar vacío.")

    # Mapea el body JSON de consultas a un diccionario plano
    filtros_raw = {}
    for item in payload.consultas:
        if not item.consulta or item.consulta.strip() == "":
            raise APIValidationError("El nombre del campo de consulta no puede estar vacío.")
        filtros_raw[item.consulta] = item.valor

    try:
        filtros = validar_y_mapear_filtros(filtros_raw)
    except APIValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error inesperado en validación POST: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al validar el esquema de filtros")

    try:
        df_completo = getattr(request.app.state, "df", None)
        if df_completo is None:
            raise ValueError("El DataFrame de ventas no está inicializado en la aplicación.")

        df_filtrado = aplicar_filtros(df_completo, filtros)
        stats_res = calcular_estadisticas(df_filtrado)
        return stats_res
    except Exception as e:
        logger.error(f"Error al calcular estadísticas en POST: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al calcular estadísticas."
        )
