"""
validaciones.py — Reglas de Validación de los Parámetros de Consulta

Este módulo valida que los filtros enviados por el usuario en su petición
GET o POST sean correctos antes de pasarlos al motor de datos.

Si algún parámetro es inválido, este módulo lanza una excepción especial
(APIValidationError) que será capturada por el manejador de errores en main.py
y convertida en una respuesta HTTP 400 con el formato exacto que exige la rúbrica.

Ejemplos de validaciones que se hacen:
- Que CANAL sea uno de los valores permitidos (POS, WEB, APP, etc.).
- Que GENERO sea uno de los valores permitidos (Masculino, Femenino, etc.).
- Que EDAD sea un número entero entre 0 y 120.
- Que LOCAL y CODIGO_PRODUCTO sean números enteros positivos.
- Que FECHA_DESDE y FECHA_HASTA tengan un formato de fecha válido.
- Que el nombre del campo de consulta sea uno de los campos permitidos.
"""

import logging
import pandas as pd
from typing import Dict, Any
from src.config import CANALES_PERMITIDOS, GENEROS_PERMITIDOS

# Logger para registrar eventos de validación si fueran necesarios.
logger = logging.getLogger("cruz_morada_api")


class APIValidationError(Exception):
    """
    Excepción personalizada para errores de validación de la API.

    Se lanza cuando el usuario envía un parámetro con un valor o nombre
    que no cumple las reglas definidas. Al lanzarse, el manejador de
    excepciones en main.py la convierte automáticamente en una respuesta
    HTTP 400 (Bad Request) con el formato de error exacto de la rúbrica.
    """
    def __init__(self, detail: str):
        super().__init__(detail)
        # Guardamos el mensaje de error descriptivo que se enviará al usuario.
        self.detail = detail


def validar_y_mapear_filtros(filtros_raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y normaliza los filtros crudos recibidos desde el request.

    Recibe un diccionario con los filtros en su forma "cruda" (tal como
    los envió el usuario) y los valida uno por uno. Si todos son válidos,
    retorna un diccionario limpio y listo para ser usado por filtros.py.

    Si algún filtro falla la validación, lanza APIValidationError con un
    mensaje explicativo que será mostrado al usuario.

    Parámetros:
        filtros_raw: Diccionario crudo con los filtros del usuario.
                     Ejemplo: {"CANAL": "POS", "LOCAL": "abc"}

    Retorna:
        Diccionario validado y normalizado.
        Ejemplo: {"CANAL": "POS", "LOCAL": 1999}  (LOCAL convertido a entero)

    Lanza:
        APIValidationError si algún filtro es inválido.
    """

    # Diccionario que iremos llenando con los filtros validados.
    filtros_validos = {}

    # Lista oficial de campos permitidos (los únicos nombres de filtro aceptados).
    CAMPOS_PERMITIDOS = {
        "GENERO", "EDAD", "CANAL", "CODIGO_PRODUCTO",
        "ID_PERSONA", "LOCAL", "FECHA_DESDE", "FECHA_HASTA"
    }

    # Procesamos cada filtro recibido del usuario.
    for key, value in filtros_raw.items():

        # Si el valor viene vacío o nulo, simplemente lo ignoramos.
        if value is None or value == "":
            continue

        # Normalizamos el nombre del campo a mayúsculas para comparar.
        campo_norm = key.strip().upper()

        # ── Validación 1: ¿El nombre del campo existe? ────────────────────────
        # Si el usuario envió un campo que no está en la lista permitida
        # (ej: "PRECIO" o "TIENDA"), rechazamos la petición con error 400.
        if campo_norm not in CAMPOS_PERMITIDOS:
            raise APIValidationError(
                f"El campo de consulta '{key}' no está permitido. "
                f"Campos válidos: {', '.join(sorted(CAMPOS_PERMITIDOS))}"
            )

        # ── Validación 2: ¿El valor del campo es correcto según su tipo? ──────

        if campo_norm == "GENERO":
            # GENERO debe ser uno de los valores de texto permitidos.
            # Permitimos variaciones de capitalización (ej: "femenino" → "Femenino").
            val_str = str(value).strip()
            generos_lower = {g.lower(): g for g in GENEROS_PERMITIDOS}
            if val_str.lower() not in generos_lower:
                raise APIValidationError(
                    f"El valor '{value}' no es válido para GENERO. "
                    f"Valores permitidos: {', '.join(sorted(GENEROS_PERMITIDOS))}"
                )
            # Guardamos el género con la capitalización correcta (ej: "Femenino").
            filtros_validos["GENERO"] = generos_lower[val_str.lower()]

        elif campo_norm == "CANAL":
            # CANAL debe ser uno de los canales de venta permitidos.
            val_str = str(value).strip().upper()
            if val_str not in CANALES_PERMITIDOS:
                raise APIValidationError(
                    f"El valor '{value}' no es un canal de venta válido. "
                    f"Canales permitidos: {', '.join(sorted(CANALES_PERMITIDOS))}"
                )
            filtros_validos["CANAL"] = val_str

        elif campo_norm == "EDAD":
            # EDAD debe ser un número entero entre 0 y 120 años.
            # Rechazamos explícitamente valores float no enteros (ej: 31.7)
            # porque int(31.7) los trunca silenciosamente a 31 sin arrojar error,
            # lo que causaría comportamiento inconsistente entre GET y POST.
            # También rechazamos booleanos (True/False) ya que bool es subclase de int.
            try:
                if isinstance(value, bool):
                    raise ValueError()
                if isinstance(value, float) and not value.is_integer():
                    raise ValueError()
                val_int = int(value)
                if val_int < 0 or val_int > 120:
                    raise ValueError()
                filtros_validos["EDAD"] = val_int
            except (ValueError, TypeError):
                raise APIValidationError(
                    f"El valor '{value}' no es un número entero de edad válido (rango 0-120)."
                )

        elif campo_norm == "LOCAL":
            # LOCAL debe ser un número entero estrictamente positivo (mayor a 0).
            # Rechazamos floats no enteros y booleanos para consistencia.
            try:
                if isinstance(value, bool):
                    raise ValueError()
                if isinstance(value, float) and not value.is_integer():
                    raise ValueError()
                val_int = int(value)
                if val_int <= 0:
                    raise ValueError()
                filtros_validos["LOCAL"] = val_int
            except (ValueError, TypeError):
                raise APIValidationError(
                    f"El valor '{value}' no es un número de local entero y positivo válido."
                )

        elif campo_norm == "CODIGO_PRODUCTO":
            # CODIGO_PRODUCTO (SKU) debe ser un número entero estrictamente positivo (mayor a 0).
            # Rechazamos floats no enteros y booleanos para consistencia.
            try:
                if isinstance(value, bool):
                    raise ValueError()
                if isinstance(value, float) and not value.is_integer():
                    raise ValueError()
                val_int = int(value)
                if val_int <= 0:
                    raise ValueError()
                filtros_validos["CODIGO_PRODUCTO"] = val_int
            except (ValueError, TypeError):
                raise APIValidationError(
                    f"El valor '{value}' no es un código de producto (SKU) entero válido."
                )

        elif campo_norm == "ID_PERSONA":
            # ID_PERSONA es un UUID en formato de texto. Solo lo limpiamos.
            filtros_validos["ID_PERSONA"] = str(value).strip()

        elif campo_norm in ("FECHA_DESDE", "FECHA_HASTA"):
            # Las fechas deben estar en formato ISO-8601 (ej: "2024-01-15" o "2024-01-15T10:30:00").
            # Intentamos parsearla; si falla, es porque el formato es inválido.
            val_str = str(value).strip()
            try:
                pd.to_datetime(val_str, errors="raise")
                filtros_validos[campo_norm] = val_str
            except Exception:
                raise APIValidationError(
                    f"El valor '{value}' no es una fecha válida en formato ISO-8601."
                )

    return filtros_validos
