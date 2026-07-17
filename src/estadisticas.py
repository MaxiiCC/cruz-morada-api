import numpy as np
import pandas as pd
from typing import Dict, Any


def calcular_estadisticas(df: pd.DataFrame) -> Dict[str, Any]:
    monto_col = "MONTO_APLICADO"

    # Si no hay registros válidos, se retorna todo en cero
    if df is None or len(df) == 0 or monto_col not in df.columns:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0
        }

    valores = df[monto_col].dropna().values
    conteo = len(valores)

    if conteo == 0:
        return {
            "suma": 0.0, "conteo": 0, "promedio": 0.0,
            "minimo": 0.0, "maximo": 0.0, "mediana": 0.0,
            "desviacion_estandar": 0.0
        }

    # Calculo de metricas descriptivas basicas
    suma = float(np.sum(valores))
    promedio = float(suma / conteo)
    minimo = float(np.min(valores))
    maximo = float(np.max(valores))

    # Calculo manual de la mediana según lo requerido
    valores_ordenados = np.sort(valores)
    if conteo % 2 != 0:
        mediana = float(valores_ordenados[conteo // 2])
    else:
        idx2 = conteo // 2
        idx1 = idx2 - 1
        mediana = float((valores_ordenados[idx1] + valores_ordenados[idx2]) / 2.0)

    # Desviación estándar poblacional (ddof=0)
    if conteo > 1:
        desviacion_estandar = float(np.std(valores, ddof=0))
    else:
        desviacion_estandar = 0.0

    return {
        "suma": round(suma, 2),
        "conteo": int(conteo),
        "promedio": round(promedio, 2),
        "minimo": round(minimo, 2),
        "maximo": round(maximo, 2),
        "mediana": round(mediana, 2),
        "desviacion_estandar": round(desviacion_estandar, 2)
    }
