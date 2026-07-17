import os
import logging
import csv
import gzip
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from src.config import CPYD_CSV_PATH, GENERO_MAP

logger = logging.getLogger("cruz_morada_api")


def procesar_un_chunk(chunk_df: pd.DataFrame) -> pd.DataFrame:
    # Quita comillas de los headers
    chunk_df.columns = [c.replace('"', '').strip() for c in chunk_df.columns]

    # Normaliza headers a mayusculas sin espacios
    columns_map = {}
    for col in chunk_df.columns:
        norm_col = col.upper().replace("É", "E").replace(" ", "_")
        columns_map[col] = norm_col
    chunk_df = chunk_df.rename(columns=columns_map)

    # Limpia comillas de los strings cuidando no convertir NaN a string "nan"
    for col in chunk_df.columns:
        if chunk_df[col].dtype == object:
            mask_no_nulo = chunk_df[col].notna()
            chunk_df.loc[mask_no_nulo, col] = (
                chunk_df.loc[mask_no_nulo, col]
                .astype(str)
                .str.replace('"', '', regex=False)
                .str.strip()
            )

    # Convierte montos y unidades a tipos numericos
    if "MONTO_APLICADO" in chunk_df.columns:
        chunk_df["MONTO_APLICADO"] = pd.to_numeric(chunk_df["MONTO_APLICADO"], errors="coerce").fillna(0.0).astype(float)
    if "UNIDADES" in chunk_df.columns:
        chunk_df["UNIDADES"] = pd.to_numeric(chunk_df["UNIDADES"], errors="coerce").fillna(0).astype(int)

    # Filtra filas invalidas
    monto_col = "MONTO_APLICADO"
    unidades_col = "UNIDADES"
    if monto_col in chunk_df.columns and unidades_col in chunk_df.columns:
        chunk_df = chunk_df[(chunk_df[monto_col] > 0) & (chunk_df[unidades_col] > 0)]

    # Convierte genero numerico a texto
    if "GENERO" in chunk_df.columns:
        genero_entero = pd.to_numeric(chunk_df["GENERO"], errors="coerce").fillna(0).astype(int)
        chunk_df["GENERO"] = genero_entero.map(GENERO_MAP).fillna("No especificado")
    else:
        chunk_df["GENERO"] = "No especificado"

    # Calcula la edad basándose en la fecha de transaccion y nacimiento
    if "FECHA" in chunk_df.columns and "FECHA_NACIMIENTO" in chunk_df.columns:
        fecha_trans = pd.to_datetime(chunk_df["FECHA"], errors="coerce")
        fecha_nac = pd.to_datetime(chunk_df["FECHA_NACIMIENTO"], errors="coerce")
        edad_dias = (fecha_trans - fecha_nac).dt.days
        chunk_df["EDAD"] = (edad_dias // 365.25).fillna(-1).astype(int)
        chunk_df.loc[(chunk_df["EDAD"] < 0) | (chunk_df["EDAD"] > 120), "EDAD"] = -1
    else:
        chunk_df["EDAD"] = -1

    # Homologa nombres de columnas para los filtros
    if "SKU" in chunk_df.columns:
        chunk_df["CODIGO_PRODUCTO"] = chunk_df["SKU"]
    if "CODIGO_CLIENTE" in chunk_df.columns:
        chunk_df["ID_PERSONA"] = chunk_df["CODIGO_CLIENTE"]

    columnas_finales = [
        "FECHA", "CANAL", "CODIGO_PRODUCTO", "UNIDADES",
        "PORCENTAJE_DESCUENTO", "MONTO_APLICADO", "LOCAL",
        "ID_PERSONA", "GENERO", "EDAD"
    ]

    # Rellena columnas faltantes
    for col in columnas_finales:
        if col not in chunk_df.columns:
            chunk_df[col] = None

    # Copia el subset final y asegura tipos
    final_df = chunk_df[columnas_finales].copy()
    final_df["FECHA"] = pd.to_datetime(final_df["FECHA"], errors="coerce")
    final_df["CANAL"] = final_df["CANAL"].astype(str).str.strip().str.upper()
    final_df["LOCAL"] = pd.to_numeric(final_df["LOCAL"], errors="coerce").fillna(-1).astype(int)
    final_df["CODIGO_PRODUCTO"] = pd.to_numeric(final_df["CODIGO_PRODUCTO"], errors="coerce").fillna(-1).astype(int)
    final_df["MONTO_APLICADO"] = pd.to_numeric(final_df["MONTO_APLICADO"], errors="coerce").fillna(0.0).astype(float)
    final_df["PORCENTAJE_DESCUENTO"] = pd.to_numeric(final_df["PORCENTAJE_DESCUENTO"], errors="coerce").fillna(0.0).astype(float)

    return final_df


def cargar_datos_parallel() -> pd.DataFrame:
    ruta_csv = Path(CPYD_CSV_PATH)
    ruta_gz = Path(str(ruta_csv) + ".gz")

    # Autodetecta .csv o version comprimida .csv.gz
    if not ruta_csv.exists() and ruta_gz.exists():
        logger.info(f"Archivo .csv no encontrado, usando version comprimida: {ruta_gz.name}")
        ruta_csv = ruta_gz
    elif not ruta_csv.exists():
        logger.error(f"Archivo CSV no encontrado en: {ruta_csv.absolute()}")
        raise FileNotFoundError(
            f"No se encontro el archivo de datos. Coloca 'ventas_completas.csv' "
            f"o 'ventas_completas.csv.gz' en la carpeta data/"
        )

    logger.info(f"Iniciando carga de: {ruta_csv.name}")
    chunk_size = 50000
    chunks_procesados = []
    max_workers = min(os.cpu_count() or 4, 8)
    logger.info(f"Usando {max_workers} procesos para la carga paralela.")

    # Autodetecta el separador del CSV usando csv.Sniffer
    try:
        if str(ruta_csv).endswith('.gz'):
            with gzip.open(ruta_csv, 'rt', encoding='latin-1') as f_sniff:
                primera_linea = f_sniff.readline()
        else:
            with open(ruta_csv, 'r', encoding='latin-1') as f_sniff:
                primera_linea = f_sniff.readline()
        separador_detectado = csv.Sniffer().sniff(primera_linea, delimiters=',;|\t').delimiter
        logger.info(f"Separador CSV detectado automaticamente: '{separador_detectado}'")
    except Exception:
        separador_detectado = ';'
        logger.warning("No se pudo detectar el separador; se usara ';' por defecto.")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        reader = pd.read_csv(
            ruta_csv,
            chunksize=chunk_size,
            sep=separador_detectado,
            encoding='latin-1',
            low_memory=False
        )

        for i, chunk in enumerate(reader):
            futures.append(executor.submit(procesar_un_chunk, chunk))
            if (i + 1) % 10 == 0:
                logger.info(f"Leidos {i + 1} chunks ({(i + 1) * chunk_size:,} filas)...")

        for future in futures:
            chunks_procesados.append(future.result())

    if not chunks_procesados:
        raise ValueError("El archivo CSV no contiene registros procesables.")

    df_completo = pd.concat(chunks_procesados, ignore_index=True)
    logger.info(f"Carga completa. Total filas cargadas: {len(df_completo):,}")
    return df_completo
