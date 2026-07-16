"""
filtros.py — Motor de Filtrado Dinámico de Datos

Este módulo es el responsable de aplicar los filtros que el usuario envía en
su consulta (ya sea por GET o por POST) sobre el dataset completo cargado en
memoria.

Todos los filtros se combinan usando lógica AND, es decir:
- Si el usuario pide CANAL=POS y LOCAL=371, se devuelven SOLO las filas donde
  el canal es POS Y al mismo tiempo el local es el 371.

Los filtros son completamente opcionales: si no se envía ninguno, se retorna
el dataset completo sin modificaciones.
"""

import pandas as pd
import logging
from typing import Dict, Any

# Logger para registrar advertencias o errores durante el filtrado.
logger = logging.getLogger("cruz_morada_api")


def aplicar_filtros(df: pd.DataFrame, filtros: Dict[str, Any]) -> pd.DataFrame:
    """
    Aplica los filtros recibidos al DataFrame de ventas de forma secuencial.

    Cada filtro reduce progresivamente el número de filas del DataFrame.
    El resultado final es el subconjunto de datos que cumple TODAS las
    condiciones al mismo tiempo (lógica AND).

    Parámetros:
        df:      El DataFrame completo con todos los datos de ventas.
        filtros: Diccionario con los nombres de campo y sus valores a filtrar.
                 Ejemplo: {"CANAL": "POS", "LOCAL": 371, "GENERO": "Femenino"}

    Retorna:
        El DataFrame filtrado, que puede ser una fracción pequeña del original
        o el dataset completo si no se aplicó ningún filtro.
    """

    # Si el DataFrame ya está vacío o no se recibieron filtros, no hay nada que hacer.
    if df is None or len(df) == 0:
        return df

    # Comenzamos con una copia del DataFrame completo.
    # A medida que aplicamos cada filtro, este DataFrame irá reduciéndose.
    filtered_df = df.copy()

    # Recorremos cada par (campo, valor) del diccionario de filtros.
    for campo, valor in filtros.items():

        # Si el valor del filtro es nulo o vacío, simplemente lo ignoramos.
        if valor is None or valor == "":
            continue

        # Normalizamos el nombre del campo a mayúsculas para compararlo.
        campo_norm = campo.upper().strip()

        # ── Filtro por GÉNERO ─────────────────────────────────────────────────
        if campo_norm == "GENERO":
            # Comparación exacta de texto (Masculino, Femenino, Otro, No especificado).
            filtered_df = filtered_df[filtered_df["GENERO"] == str(valor).strip()]

        # ── Filtro por EDAD ───────────────────────────────────────────────────
        elif campo_norm == "EDAD":
            # Buscamos clientes que tengan exactamente esa edad en años.
            # La edad fue calculada al cargar el CSV en carga.py.
            filtered_df = filtered_df[filtered_df["EDAD"] == int(valor)]

        # ── Filtro por CANAL ──────────────────────────────────────────────────
        elif campo_norm == "CANAL":
            # Canal de venta: POS, WEB, APP, CCT, APR, WPR.
            # Convertimos a mayúsculas para que la comparación sea insensible a mayúsculas.
            filtered_df = filtered_df[filtered_df["CANAL"] == str(valor).strip().upper()]

        # ── Filtro por CÓDIGO DE PRODUCTO (SKU) ──────────────────────────────
        elif campo_norm == "CODIGO_PRODUCTO":
            # El código de producto (SKU) es un número entero.
            filtered_df = filtered_df[filtered_df["CODIGO_PRODUCTO"] == int(valor)]

        # ── Filtro por ID DE PERSONA (UUID del cliente) ───────────────────────
        elif campo_norm == "ID_PERSONA":
            # El identificador único del cliente es un texto en formato UUID.
            filtered_df = filtered_df[filtered_df["ID_PERSONA"] == str(valor).strip()]

        # ── Filtro por LOCAL ──────────────────────────────────────────────────
        elif campo_norm == "LOCAL":
            # Número identificador del local donde se realizó la compra.
            filtered_df = filtered_df[filtered_df["LOCAL"] == int(valor)]

        # ── Filtro por FECHA DESDE ────────────────────────────────────────────
        elif campo_norm == "FECHA_DESDE":
            # Retiene solo las filas donde la fecha de la transacción sea
            # mayor o igual a la fecha indicada por el usuario.
            # Ej: FECHA_DESDE = "2024-01-01" → solo ventas desde el 1 de enero de 2024 en adelante.
            fecha_lim = pd.to_datetime(valor, errors="coerce")
            if not pd.isna(fecha_lim):
                filtered_df = filtered_df[filtered_df["FECHA"] >= fecha_lim]

        # ── Filtro por FECHA HASTA ────────────────────────────────────────────
        elif campo_norm == "FECHA_HASTA":
            # Retiene solo las filas donde la fecha de la transacción sea
            # menor o igual a la fecha indicada por el usuario.
            #
            # IMPORTANTE: si el usuario envía solo la fecha sin hora
            # (ej: "2024-12-31"), pandas la interpreta como el instante
            # 2024-12-31T00:00:00, lo que excluiría TODAS las ventas de ese
            # mismo día. Para que "hasta el 31 de diciembre" incluya el día
            # completo, si no viene un componente horario explícito lo
            # extendemos hasta el último instante del día (23:59:59.999999).
            fecha_lim = pd.to_datetime(valor, errors="coerce")
            if not pd.isna(fecha_lim):
                valor_str = str(valor).strip()
                tiene_hora = "T" in valor_str or " " in valor_str
                if not tiene_hora:
                    fecha_lim = fecha_lim + pd.Timedelta(
                        hours=23, minutes=59, seconds=59, microseconds=999999
                    )
                filtered_df = filtered_df[filtered_df["FECHA"] <= fecha_lim]

        else:
            # Si llegamos aquí, el campo no es reconocido en esta capa.
            # Esto no debería pasar porque validaciones.py ya filtra los campos
            # inválidos antes de llegar aquí. Solo registramos una advertencia.
            logger.warning(f"Filtro omitido o desconocido en la capa de datos: {campo}")

    return filtered_df
