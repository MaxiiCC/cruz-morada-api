import logging
import pandas as pd
from typing import Dict, Any
from src.config import CANALES_PERMITIDOS, GENEROS_PERMITIDOS

logger = logging.getLogger("cruz_morada_api")


class APIValidationError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def validar_y_mapear_filtros(filtros_raw: Dict[str, Any]) -> Dict[str, Any]:
    filtros_validos = {}
    CAMPOS_PERMITIDOS = {
        "GENERO", "EDAD", "CANAL", "CODIGO_PRODUCTO",
        "ID_PERSONA", "LOCAL", "FECHA_DESDE", "FECHA_HASTA"
    }

    for key, value in filtros_raw.items():
        if value is None or value == "":
            continue

        campo_norm = key.strip().upper()

        # Valida que el filtro exista en la lista oficial
        if campo_norm not in CAMPOS_PERMITIDOS:
            raise APIValidationError(
                f"El campo de consulta '{key}' no está permitido. "
                f"Campos válidos: {', '.join(sorted(CAMPOS_PERMITIDOS))}"
            )

        # Validación por género
        if campo_norm == "GENERO":
            val_str = str(value).strip()
            generos_lower = {g.lower(): g for g in GENEROS_PERMITIDOS}
            if val_str.lower() not in generos_lower:
                raise APIValidationError(
                    f"El valor '{value}' no es válido para GENERO. "
                    f"Valores permitidos: {', '.join(sorted(GENEROS_PERMITIDOS))}"
                )
            filtros_validos["GENERO"] = generos_lower[val_str.lower()]

        # Validación por canal
        elif campo_norm == "CANAL":
            val_str = str(value).strip().upper()
            if val_str not in CANALES_PERMITIDOS:
                raise APIValidationError(
                    f"El valor '{value}' no es un canal de venta válido. "
                    f"Canales permitidos: {', '.join(sorted(CANALES_PERMITIDOS))}"
                )
            filtros_validos["CANAL"] = val_str

        # Validación por edad
        elif campo_norm == "EDAD":
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

        # Validación por local
        elif campo_norm == "LOCAL":
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

        # Validación por SKU de producto
        elif campo_norm == "CODIGO_PRODUCTO":
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

        # Filtro de ID persona
        elif campo_norm == "ID_PERSONA":
            filtros_validos["ID_PERSONA"] = str(value).strip()

        # Validación de formatos de fecha
        elif campo_norm in ("FECHA_DESDE", "FECHA_HASTA"):
            val_str = str(value).strip()
            try:
                pd.to_datetime(val_str, errors="raise")
                filtros_validos[campo_norm] = val_str
            except Exception:
                raise APIValidationError(
                    f"El valor '{value}' no es una fecha válida en formato ISO-8601."
                )

    return filtros_validos
