import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger("cruz_morada_api")


def aplicar_filtros(df: pd.DataFrame, filtros: Dict[str, Any]) -> pd.DataFrame:
    # Si no hay datos, retorna directo
    if df is None or len(df) == 0:
        return df

    # No se hace .copy() aquí para no duplicar las 3.2M de filas en memoria.
    # El filtrado de pandas ya genera copias nuevas de los subsets automáticamente.
    filtered_df = df

    for campo, valor in filtros.items():
        if valor is None or valor == "":
            continue

        campo_norm = campo.upper().strip()

        # Filtro de genero
        if campo_norm == "GENERO":
            filtered_df = filtered_df[filtered_df["GENERO"] == str(valor).strip()]

        # Filtro de edad
        elif campo_norm == "EDAD":
            filtered_df = filtered_df[filtered_df["EDAD"] == int(valor)]

        # Filtro de canal
        elif campo_norm == "CANAL":
            filtered_df = filtered_df[filtered_df["CANAL"] == str(valor).strip().upper()]

        # Filtro de SKU
        elif campo_norm == "CODIGO_PRODUCTO":
            filtered_df = filtered_df[filtered_df["CODIGO_PRODUCTO"] == int(valor)]

        # Filtro de ID cliente
        elif campo_norm == "ID_PERSONA":
            filtered_df = filtered_df[filtered_df["ID_PERSONA"] == str(valor).strip()]

        # Filtro de local
        elif campo_norm == "LOCAL":
            filtered_df = filtered_df[filtered_df["LOCAL"] == int(valor)]

        # Filtro de fecha inicial
        elif campo_norm == "FECHA_DESDE":
            fecha_lim = pd.to_datetime(valor, errors="coerce")
            if not pd.isna(fecha_lim):
                if fecha_lim.tzinfo is not None:
                    fecha_lim = fecha_lim.tz_localize(None)
                filtered_df = filtered_df[filtered_df["FECHA"] >= fecha_lim]

        # Filtro de fecha limite
        elif campo_norm == "FECHA_HASTA":
            fecha_lim = pd.to_datetime(valor, errors="coerce")
            if not pd.isna(fecha_lim):
                if fecha_lim.tzinfo is not None:
                    fecha_lim = fecha_lim.tz_localize(None)
                valor_str = str(valor).strip()
                # Si viene sin hora, sumamos todo el dia completo para incluir las ventas de esa fecha
                tiene_hora = "T" in valor_str or " " in valor_str
                if not tiene_hora:
                    fecha_lim = fecha_lim + pd.Timedelta(
                        hours=23, minutes=59, seconds=59, microseconds=999999
                    )
                filtered_df = filtered_df[filtered_df["FECHA"] <= fecha_lim]
        else:
            logger.warning(f"Filtro omitido o desconocido: {campo}")

    return filtered_df
