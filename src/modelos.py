from pydantic import BaseModel, Field
from typing import List, Any, Optional


class VentasResponse(BaseModel):
    # Esquema de respuesta exitosa de estadisticas
    suma: float = Field(..., description="Suma total de montos aplicados en CLP",
                        json_schema_extra={"example": 1500.5})
    conteo: int = Field(..., description="Cantidad de transacciones filtradas",
                        json_schema_extra={"example": 42})
    promedio: float = Field(..., description="Promedio de los montos aplicados",
                            json_schema_extra={"example": 35.73})
    minimo: float = Field(..., description="Monto aplicado mínimo",
                          json_schema_extra={"example": 10.0})
    maximo: float = Field(..., description="Monto aplicado máximo",
                          json_schema_extra={"example": 100.0})
    mediana: float = Field(..., description="Mediana de los montos aplicados",
                           json_schema_extra={"example": 30.0})
    desviacion_estandar: float = Field(..., description="Desviación estándar de los montos aplicados",
                                       json_schema_extra={"example": 25.4})


class ConsultaItem(BaseModel):
    # Item individual del body de consulta
    consulta: str = Field(...,
                          description="Nombre del campo a filtrar (ej: CANAL, GENERO, EDAD)",
                          json_schema_extra={"example": "CANAL"})
    valor: Any = Field(...,
                       description="Valor del filtro a aplicar",
                       json_schema_extra={"example": "POS"})


class ConsultaRequest(BaseModel):
    # Payload completo del POST
    consultas: Optional[List[ConsultaItem]] = Field(
        None,
        description="Lista de filtros a aplicar sobre los datos de ventas",
        json_schema_extra={"example": [
            {"consulta": "GENERO", "valor": "Femenino"},
            {"consulta": "EDAD", "valor": "31"},
            {"consulta": "CANAL", "valor": "POS"}
        ]}
    )


class ErrorResponse(BaseModel):
    # Estructura de error requerida por la pauta
    detail: str = Field(..., description="Descripción detallada del error",
                        json_schema_extra={"example": "El valor 'qwerty' no es un número entero válido para la edad"})
    instance: str = Field("/v1/estadisticas/ventas", description="URI del recurso donde ocurrió el error")
    status: int = Field(..., description="Código de estado HTTP",
                        json_schema_extra={"example": 400})
    title: str = Field(..., description="Título corto del error",
                       json_schema_extra={"example": "Bad Request"})
    type: str = Field(..., description="Enlace a la documentación del estado HTTP",
                      json_schema_extra={"example": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400"})
    timestamp: str = Field(..., description="Timestamp del error en formato ISO 8601",
                           json_schema_extra={"example": "2026-06-30T20:44:49.201437Z"})
    errorCode: str = Field(..., description="Código corto interno de error",
                           json_schema_extra={"example": "VF"})
    errorLabel: str = Field(..., description="Etiqueta amigable del tipo de error",
                            json_schema_extra={"example": "Validación Fallida"})
    method: str = Field(..., description="Método HTTP utilizado",
                        json_schema_extra={"example": "POST"})
