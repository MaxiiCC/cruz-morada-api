"""
estadisticas.py — Cálculo de Estadísticas Descriptivas

Este módulo contiene la lógica matemática para calcular todas las métricas
de resumen estadístico sobre los montos de ventas de Cruz Morada.

Las fórmulas utilizadas corresponden exactamente a lo solicitado en el enunciado
del trabajo y son aplicadas siempre sobre la columna MONTO_APLICADO del dataset.

Métricas calculadas:
- suma:              Suma total de todos los montos del conjunto filtrado.
- conteo:            Cantidad total de transacciones del conjunto filtrado.
- promedio:          Suma dividida por el conteo (promedio aritmético).
- minimo:            El monto más bajo registrado.
- maximo:            El monto más alto registrado.
- mediana:           El valor central cuando los montos se ordenan de menor a mayor.
                     Si hay un número par de valores, se promedia los dos centrales.
- desviacion_estandar: Mide cuánto se dispersan los valores respecto al promedio.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any


def calcular_estadisticas(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula las estadísticas descriptivas sobre la columna MONTO_APLICADO
    del DataFrame recibido.

    Si el DataFrame está vacío (porque los filtros aplicados no encontraron
    registros), retorna un resultado con todos los valores en cero sin lanzar
    ningún error.

    Parámetros:
        df: El conjunto de datos (posiblemente filtrado) sobre el que calcular.

    Retorna:
        Un diccionario con las 7 métricas requeridas por la API.
    """
    monto_col = "MONTO_APLICADO"

    # ── Caso sin datos ────────────────────────────────────────────────────────
    # Si el DataFrame está vacío o la columna de montos no existe, devolvemos
    # todos los valores en cero. Esto es matemáticamente correcto: no hay
    # registros, no hay estadísticas que calcular.
    if df is None or len(df) == 0 or monto_col not in df.columns:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0
        }

    # Extraemos los valores numéricos de MONTO_APLICADO, descartando nulos.
    valores = df[monto_col].dropna().values
    conteo = len(valores)

    # Si después de descartar nulos no queda ningún valor, devolvemos ceros.
    if conteo == 0:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0
        }

    # ── Cálculo de métricas ───────────────────────────────────────────────────

    # 1. SUMA: Suma simple de todos los montos del conjunto.
    suma = float(np.sum(valores))

    # 2. PROMEDIO: Se calcula como suma / conteo, tal como indica el enunciado.
    #    Ejemplo: si la suma es $100.000 y hay 10 ventas → promedio = $10.000
    promedio = float(suma / conteo)

    # 3. MÍNIMO: El monto más pequeño de todas las transacciones filtradas.
    minimo = float(np.min(valores))

    # 4. MÁXIMO: El monto más grande de todas las transacciones filtradas.
    maximo = float(np.max(valores))

    # 5. MEDIANA: Implementación manual exacta según el enunciado del trabajo.
    #    - Primero ordenamos los valores de menor a mayor.
    #    - Si hay un número IMPAR de valores: la mediana es el valor del centro.
    #      Ejemplo: [1, 3, 5] → mediana = 3 (está en la posición del medio)
    #    - Si hay un número PAR de valores: la mediana es el promedio de los
    #      dos valores más cercanos al centro.
    #      Ejemplo: [1, 3, 5, 7] → mediana = (3 + 5) / 2 = 4.0
    valores_ordenados = np.sort(valores)
    if conteo % 2 != 0:
        # Número impar: tomamos el elemento que queda exactamente en el centro.
        mediana = float(valores_ordenados[conteo // 2])
    else:
        # Número par: promediamos los dos elementos centrales.
        idx2 = conteo // 2
        idx1 = idx2 - 1
        mediana = float((valores_ordenados[idx1] + valores_ordenados[idx2]) / 2.0)

    # 6. DESVIACIÓN ESTÁNDAR: Mide qué tan dispersos están los valores respecto
    #    al promedio. Un valor bajo indica que la mayoría de precios son parecidos
    #    al promedio. Un valor alto indica que hay mucha variabilidad de precios.
    #    Usamos ddof=0 (fórmula poblacional) ya que tenemos el universo completo
    #    de datos, no una muestra.
    if conteo > 1:
        desviacion_estandar = float(np.std(valores, ddof=0))
    else:
        # Con solo una transacción, no existe dispersión (la varianza es cero).
        desviacion_estandar = 0.0

    # ── Retorno de resultados ─────────────────────────────────────────────────
    # Redondeamos a 2 decimales para tener una presentación limpia en el JSON.
    return {
        "suma": round(suma, 2),
        "conteo": int(conteo),
        "promedio": round(promedio, 2),
        "minimo": round(minimo, 2),
        "maximo": round(maximo, 2),
        "mediana": round(mediana, 2),
        "desviacion_estandar": round(desviacion_estandar, 2)
    }
