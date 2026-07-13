"""
modelos.py — Esquemas de Datos de la API (Pydantic)

Este módulo define la "forma" que deben tener los datos que entran y salen
de la API. En FastAPI, estos esquemas (modelos) se usan para:

1. VALIDACIÓN AUTOMÁTICA: Si el usuario envía un cuerpo JSON en el POST con un
   campo de tipo incorrecto, FastAPI automáticamente rechaza la petición con
   un error descriptivo antes de que el código siquiera se ejecute.

2. DOCUMENTACIÓN SWAGGER: FastAPI lee estos modelos y genera automáticamente
   la documentación interactiva en /docs, mostrando los ejemplos y descripciones
   de cada campo.

3. SERIALIZACIÓN: Cuando la API retorna datos, FastAPI los convierte
   automáticamente al formato JSON correcto basándose en estos modelos.
"""

from pydantic import BaseModel, Field
from typing import List, Any, Optional


class VentasResponse(BaseModel):
    """
    Modelo de la respuesta exitosa (HTTP 200 OK).

    Define exactamente qué campos deben estar presentes en la respuesta JSON
    cuando la consulta de estadísticas se procesa correctamente.

    Todos los campos son numéricos:
    - suma y promedio son de punto flotante (permiten decimales).
    - conteo es un número entero (no puede haber media transacción).
    """
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
    """
    Modelo de un único ítem de consulta dentro del body del POST.

    Cada ítem representa un filtro: tiene un nombre de campo (consulta)
    y el valor a filtrar (valor).

    Ejemplo de uso en el JSON del body:
        {"consulta": "CANAL", "valor": "POS"}
    """
    consulta: str = Field(...,
                          description="Nombre del campo a filtrar (ej: CANAL, GENERO, EDAD)",
                          json_schema_extra={"example": "CANAL"})
    valor: Any = Field(...,
                       description="Valor del filtro a aplicar",
                       json_schema_extra={"example": "POS"})


class ConsultaRequest(BaseModel):
    """
    Modelo del cuerpo (body) completo de la petición POST.

    Contiene una lista de ítems de consulta. Esta lista puede contener
    cualquier combinación de los filtros permitidos.

    Ejemplo completo del body:
        {
            "consultas": [
                {"consulta": "GENERO", "valor": "Femenino"},
                {"consulta": "EDAD", "valor": "31"},
                {"consulta": "CANAL", "valor": "POS"}
            ]
        }
    """
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
    """
    Modelo del formato de error de la API (HTTP 400 o HTTP 500).

    Este es el esquema de JSON que devuelve la API cuando ocurre un error.
    El formato fue definido exactamente según los requisitos de la rúbrica
    del profesor, con todos los campos obligatorios:

    - detail:     Descripción legible del error específico que ocurrió.
    - instance:   La ruta del endpoint donde ocurrió el error.
    - status:     El código HTTP del error (400 o 500).
    - title:      El nombre del tipo de error HTTP ("Bad Request" o "Internal Server Error").
    - type:       Enlace a la documentación oficial del código HTTP en MDN Web Docs.
    - timestamp:  La fecha y hora exacta en que ocurrió el error (formato ISO 8601 UTC).
    - errorCode:  Código corto interno ("VF" para validación, "IE" para error interno).
    - errorLabel: Texto legible del código de error ("Validación Fallida", "Error Interno").
    - method:     El método HTTP de la petición que causó el error ("GET" o "POST").
    """
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
