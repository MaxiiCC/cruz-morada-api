"""
carga.py — Carga Paralela y Preprocesamiento del Archivo CSV

Este módulo es el encargado de leer el archivo de datos de ventas (ventas_completas.csv)
al inicio de la aplicación, de forma automática y sin intervención del usuario.

Como el archivo tiene más de 3.2 millones de filas, no es eficiente leerlo de una sola
vez. En cambio, lo dividimos en trozos (chunks) de 50.000 filas cada uno, y procesamos
varios trozos al mismo tiempo usando múltiples núcleos del procesador (paralelismo).

Al terminar la carga, todos los datos quedan limpios y listos en la memoria del servidor
para que las consultas de la API sean instantáneas.
"""

import os
import logging
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from src.config import CPYD_CSV_PATH, GENERO_MAP

# Creamos un logger (sistema de registro de mensajes) para este módulo.
# Esto nos permite ver en la consola qué está haciendo el sistema en cada momento.
logger = logging.getLogger("cruz_morada_api")


def procesar_un_chunk(chunk_df: pd.DataFrame) -> pd.DataFrame:
    """
    Esta función procesa UN TROZO (chunk) del archivo CSV.

    Es la función que se ejecuta en paralelo: mientras un núcleo del procesador
    trabaja en el trozo 1, otro trabaja en el trozo 2, y así sucesivamente.
    Esto hace que la carga sea mucho más rápida que si procesáramos fila por fila.

    Pasos que realiza sobre cada trozo:
    1. Limpia las comillas dobles que vienen en el CSV alrededor de los valores.
    2. Normaliza los nombres de las columnas (las pone en MAYÚSCULAS y sin espacios).
    3. Convierte el GÉNERO de número (1/2) a texto (Masculino/Femenino).
    4. Calcula la EDAD del cliente a partir de su fecha de nacimiento y la fecha de compra.
    5. Renombra columnas clave (SKU → CODIGO_PRODUCTO, etc.) para que coincidan con los filtros.
    6. Devuelve solo las columnas que necesita la API, eliminando el resto para ahorrar memoria.
    """

    # ── Paso 0: Limpiar las comillas dobles de los nombres de columnas ──────────
    # El CSV de Cruz Morada envuelve los encabezados en comillas dobles (ej: "FECHA").
    # Aquí las removemos para que los nombres queden limpios (ej: FECHA).
    chunk_df.columns = [c.replace('"', '').strip() for c in chunk_df.columns]

    # ── Paso 1: Normalizar los nombres de las columnas ──────────────────────────
    # Convertimos todos los nombres a MAYÚSCULAS y reemplazamos espacios con guiones bajos.
    # Por ejemplo: "MONTO APLICADO" → "MONTO_APLICADO"
    # También corregimos la tilde del acento en "GÉNERO" → "GENERO"
    columns_map = {}
    for col in chunk_df.columns:
        norm_col = col.upper().replace("É", "E").replace(" ", "_")
        columns_map[col] = norm_col
    chunk_df = chunk_df.rename(columns=columns_map)

    # ── Paso 2: Limpiar comillas dobles de los valores de texto ─────────────────
    # Los valores del CSV también vienen con comillas (ej: "POS", "3198").
    # Aquí las removemos de todas las columnas de texto para poder operar con los datos.
    for col in chunk_df.columns:
        if chunk_df[col].dtype == object:
            chunk_df[col] = chunk_df[col].astype(str).str.replace('"', '', regex=False).str.strip()

    # ── Paso 3: Convertir columnas numéricas clave antes de filtrar ─────────────
    # Necesitamos que MONTO_APLICADO y UNIDADES sean números para poder filtrar
    # solo las ventas válidas (monto > 0 y unidades > 0).
    if "MONTO_APLICADO" in chunk_df.columns:
        chunk_df["MONTO_APLICADO"] = pd.to_numeric(chunk_df["MONTO_APLICADO"], errors="coerce").fillna(0.0).astype(float)
    if "UNIDADES" in chunk_df.columns:
        chunk_df["UNIDADES"] = pd.to_numeric(chunk_df["UNIDADES"], errors="coerce").fillna(0).astype(int)

    # ── Paso 4: Eliminar filas inválidas ────────────────────────────────────────
    # Descartamos transacciones donde el monto sea 0 o negativo, o las unidades sean 0.
    # Estas filas son registros corruptos o errores de entrada de datos.
    monto_col = "MONTO_APLICADO"
    unidades_col = "UNIDADES"
    if monto_col in chunk_df.columns and unidades_col in chunk_df.columns:
        chunk_df = chunk_df[(chunk_df[monto_col] > 0) & (chunk_df[unidades_col] > 0)]

    # ── Paso 5: Convertir el género de número a texto ───────────────────────────
    # En el CSV, el género viene como un número entero (1 o 2).
    # Aquí lo convertimos a texto legible usando la tabla GENERO_MAP de config.py.
    # Si el valor es 0 o no es reconocido, lo marcamos como "No especificado".
    if "GENERO" in chunk_df.columns:
        genero_entero = pd.to_numeric(chunk_df["GENERO"], errors="coerce").fillna(0).astype(int)
        chunk_df["GENERO"] = genero_entero.map(GENERO_MAP).fillna("No especificado")
    else:
        chunk_df["GENERO"] = "No especificado"

    # ── Paso 6: Calcular la edad del cliente ─────────────────────────────────────
    # La edad no existe directamente en el CSV. La calculamos restando la fecha de
    # nacimiento del cliente a la fecha de la transacción, y convirtiendo el resultado
    # de días a años (dividiendo por 365.25, que considera los años bisiestos).
    # Si la fecha de nacimiento está vacía o la edad calculada no es plausible
    # (ej: mayor a 120 años o negativa), asignamos -1 como valor centinela.
    if "FECHA" in chunk_df.columns and "FECHA_NACIMIENTO" in chunk_df.columns:
        fecha_trans = pd.to_datetime(chunk_df["FECHA"], errors="coerce")
        fecha_nac = pd.to_datetime(chunk_df["FECHA_NACIMIENTO"], errors="coerce")
        edad_dias = (fecha_trans - fecha_nac).dt.days
        chunk_df["EDAD"] = (edad_dias // 365.25).fillna(-1).astype(int)
        chunk_df.loc[(chunk_df["EDAD"] < 0) | (chunk_df["EDAD"] > 120), "EDAD"] = -1
    else:
        chunk_df["EDAD"] = -1

    # ── Paso 7: Renombrar columnas para que coincidan con los nombres de los filtros ──
    # La API expone los filtros con nombres estándar (CODIGO_PRODUCTO, ID_PERSONA),
    # pero en el CSV se llaman diferente (SKU, CODIGO_CLIENTE).
    # Aquí hacemos la equivalencia para que los filtros funcionen correctamente.
    if "SKU" in chunk_df.columns:
        chunk_df["CODIGO_PRODUCTO"] = chunk_df["SKU"]
    if "CODIGO_CLIENTE" in chunk_df.columns:
        chunk_df["ID_PERSONA"] = chunk_df["CODIGO_CLIENTE"]

    # ── Paso 8: Quedarse solo con las columnas que necesita la API ───────────────
    # Descartamos todo lo que no se usa (RUN_CLIENTE, NOMBRES, APELLIDOS, etc.)
    # para ahorrar memoria RAM durante la ejecución del servidor.
    columnas_finales = [
        "FECHA", "CANAL", "CODIGO_PRODUCTO", "UNIDADES",
        "PORCENTAJE_DESCUENTO", "MONTO_APLICADO", "LOCAL",
        "ID_PERSONA", "GENERO", "EDAD"
    ]

    # Si alguna columna esperada no existe en el trozo (por ejemplo, en un CSV incompleto),
    # la creamos con valor nulo (None) para evitar errores al seleccionarla más adelante.
    for col in columnas_finales:
        if col not in chunk_df.columns:
            chunk_df[col] = None

    # Extraemos solo las columnas necesarias y las convertimos a sus tipos definitivos.
    final_df = chunk_df[columnas_finales].copy()
    final_df["FECHA"] = pd.to_datetime(final_df["FECHA"], errors="coerce")
    final_df["CANAL"] = final_df["CANAL"].astype(str).str.strip().str.upper()
    final_df["LOCAL"] = pd.to_numeric(final_df["LOCAL"], errors="coerce").fillna(-1).astype(int)
    final_df["CODIGO_PRODUCTO"] = pd.to_numeric(final_df["CODIGO_PRODUCTO"], errors="coerce").fillna(-1).astype(int)
    final_df["MONTO_APLICADO"] = pd.to_numeric(final_df["MONTO_APLICADO"], errors="coerce").fillna(0.0).astype(float)
    final_df["PORCENTAJE_DESCUENTO"] = pd.to_numeric(final_df["PORCENTAJE_DESCUENTO"], errors="coerce").fillna(0.0).astype(float)

    return final_df


def cargar_datos_parallel() -> pd.DataFrame:
    """
    Función principal de carga del CSV usando múltiples núcleos del procesador.

    Proceso:
    1. Verifica que el archivo CSV exista en la ruta configurada.
    2. Abre el archivo y lo divide en trozos de 50.000 filas.
    3. Envía cada trozo a un proceso paralelo que ejecuta procesar_un_chunk().
    4. Espera a que todos los procesos terminen y une sus resultados en un solo DataFrame.
    5. Retorna el DataFrame completo con todos los datos limpios y listos en memoria.

    El número de procesos paralelos se ajusta automáticamente a los núcleos
    disponibles en el servidor (máximo 8 para no saturar el sistema).
    """
    # Verificamos que el archivo exista antes de intentar abrirlo.
    ruta_csv = Path(CPYD_CSV_PATH)
    if not ruta_csv.exists():
        logger.error(f"Archivo CSV no encontrado en la ruta configurada: {ruta_csv.absolute()}")
        raise FileNotFoundError(f"No se encontró el archivo CSV en: {ruta_csv.absolute()}")

    logger.info(f"Iniciando carga paralela de: {ruta_csv.name}")

    # Tamaño de cada trozo: 50.000 filas por fragmento.
    chunk_size = 50000

    # Lista donde iremos guardando el resultado procesado de cada trozo.
    chunks_procesados = []

    # Calculamos cuántos procesos paralelos usar.
    # Usamos todos los núcleos disponibles del CPU, con un máximo de 8.
    max_workers = min(os.cpu_count() or 4, 8)
    logger.info(f"Usando {max_workers} procesos en paralelo para la carga y limpieza de datos.")

    # Abrimos el archivo CSV dividiéndolo en trozos y procesamos en paralelo.
    # El CSV de Cruz Morada usa coma (,) como separador de columnas según el enunciado,
    # y la codificación latin-1 para soportar caracteres del español (ñ, á, é, etc.).
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        reader = pd.read_csv(
            ruta_csv,
            chunksize=chunk_size,
            sep=',',
            encoding='latin-1',
            low_memory=False
        )

        # Por cada trozo leído, enviamos el trabajo de limpieza a un proceso en paralelo.
        # "futures" es una lista de "tareas pendientes" que irán completándose.
        for i, chunk in enumerate(reader):
            futures.append(executor.submit(procesar_un_chunk, chunk))
            # Cada 10 trozos (500.000 filas), mostramos el progreso en la consola.
            if (i + 1) % 10 == 0:
                logger.info(f"Leídos {i + 1} chunks ({(i + 1) * chunk_size:,} filas)...")

        # Esperamos a que todos los procesos terminen y recogemos sus resultados.
        for future in futures:
            chunks_procesados.append(future.result())

    # Si el archivo estaba vacío o no tenía datos válidos, lanzamos un error.
    if not chunks_procesados:
        raise ValueError("El archivo CSV no contiene registros procesables.")

    # Unimos todos los trozos en un solo DataFrame gigante y lo retornamos.
    df_completo = pd.concat(chunks_procesados, ignore_index=True)
    logger.info(f"Carga completa. Total filas válidas cargadas: {len(df_completo):,}")
    return df_completo
