"""
test_api.py — Pruebas Unitarias e Integración de la API

Este archivo contiene todas las pruebas automatizadas del proyecto.
Las pruebas verifican que la API se comporte correctamente en distintos escenarios:
- Cuando recibe una petición válida (debe responder HTTP 200 con estadísticas correctas).
- Cuando recibe una petición con filtros inválidos (debe responder HTTP 400 con el
  formato de error exacto que exige la rúbrica).

Para ejecutar las pruebas, se usa un conjunto de datos FICTICIO y pequeño (4 filas)
en lugar del archivo CSV real de 3.2 millones de filas. Esto permite que las pruebas
sean rápidas, predecibles y no dependan del archivo de datos externo.

FastAPI provee un "TestClient" que simula el comportamiento del servidor real sin
necesidad de levantarlo explícitamente. Es ideal para pruebas unitarias.

Comando para ejecutar: python -m pytest -v
"""

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

# ─── DATASET FICTICIO PARA PRUEBAS ───────────────────────────────────────────
# Creamos manualmente 4 filas de ventas simuladas que representan distintos
# escenarios: diferentes géneros, canales, locales y edades.
# Los valores de MONTO_APLICADO son simples para que sea fácil verificar los cálculos.
#   - Filas de montos: [10000, 20000, 30000, 40000]
#   - Suma: 100000 | Promedio: 25000 | Mediana: (20000+30000)/2 = 25000
df_mock = pd.DataFrame([
    {
        "FECHA": pd.to_datetime("2026-05-08T00:02:53"),
        "CANAL": "POS",
        "CODIGO_PRODUCTO": 1095,
        "UNIDADES": 1,
        "PORCENTAJE_DESCUENTO": 0.15,
        "MONTO_APLICADO": 10000.0,
        "LOCAL": 1999,
        "ID_PERSONA": "550e8400-e29b-41d4-a716-446655440000",
        "GENERO": "Masculino",
        "EDAD": 31
    },
    {
        "FECHA": pd.to_datetime("2026-05-09T12:00:00"),
        "CANAL": "WEB",
        "CODIGO_PRODUCTO": 1096,
        "UNIDADES": 1,
        "PORCENTAJE_DESCUENTO": 0.10,
        "MONTO_APLICADO": 20000.0,
        "LOCAL": 2000,
        "ID_PERSONA": "550e8400-e29b-41d4-a716-446655440001",
        "GENERO": "Femenino",
        "EDAD": 25
    },
    {
        "FECHA": pd.to_datetime("2026-05-10T15:30:22"),
        "CANAL": "APP",
        "CODIGO_PRODUCTO": 1095,
        "UNIDADES": 1,
        "PORCENTAJE_DESCUENTO": 0.20,
        "MONTO_APLICADO": 30000.0,
        "LOCAL": 1999,
        "ID_PERSONA": "550e8400-e29b-41d4-a716-446655440002",
        "GENERO": "Masculino",
        "EDAD": 45
    },
    {
        "FECHA": pd.to_datetime("2026-05-11T18:45:10"),
        "CANAL": "POS",
        "CODIGO_PRODUCTO": 1097,
        "UNIDADES": 1,
        "PORCENTAJE_DESCUENTO": 0.05,
        "MONTO_APLICADO": 40000.0,
        "LOCAL": 2001,
        "ID_PERSONA": "550e8400-e29b-41d4-a716-446655440003",
        "GENERO": "Femenino",
        "EDAD": 60
    }
])


@pytest.fixture(autouse=True)
def setup_mock_data():
    """
    Fixture de configuración automática que se ejecuta ANTES de cada prueba.

    Inyecta el DataFrame ficticio (df_mock) en el estado de la aplicación FastAPI,
    reemplazando el CSV real. Así las pruebas son independientes del archivo de datos.
    'autouse=True' significa que se aplica automáticamente a TODAS las pruebas del archivo.
    """
    app.state.df = df_mock


# Creamos el cliente de pruebas que simulará las peticiones HTTP al servidor.
client = TestClient(app)


# ─── PRUEBA 1: GET sin filtros ────────────────────────────────────────────────
def test_get_sin_filtros():
    """
    Verifica que el endpoint GET responda correctamente cuando no se envía
    ningún filtro. Debe calcular estadísticas sobre el dataset completo (4 filas).

    Valores esperados sobre [10000, 20000, 30000, 40000]:
    - suma = 100000
    - conteo = 4
    - promedio = 25000
    - minimo = 10000
    - maximo = 40000
    - mediana = (20000 + 30000) / 2 = 25000 (conteo par → promedio de los 2 centrales)
    """
    response = client.get("/v1/estadisticas/ventas")
    assert response.status_code == 200     # Esperamos HTTP 200 OK
    data = response.json()

    assert data["suma"] == 100000.0
    assert data["conteo"] == 4
    assert data["promedio"] == 25000.0
    assert data["minimo"] == 10000.0
    assert data["maximo"] == 40000.0
    assert data["mediana"] == 25000.0
    assert data["desviacion_estandar"] > 0


# ─── PRUEBA 2: GET con filtro de GENERO ──────────────────────────────────────
def test_get_con_filtro_genero():
    """
    Verifica que el filtro por GENERO funcione correctamente.

    En el dataset ficticio, las filas con GENERO = "Femenino" son las de montos
    20000 y 40000. La suma debe ser 60000 y el conteo 2.
    """
    response = client.get("/v1/estadisticas/ventas?GENERO=Femenino")
    assert response.status_code == 200
    data = response.json()

    assert data["suma"] == 60000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 30000.0
    assert data["mediana"] == 30000.0   # Con 2 elementos: (20000+40000)/2 = 30000


# ─── PRUEBA 3: GET con filtro de LOCAL ───────────────────────────────────────
def test_get_con_filtro_local():
    """
    Verifica que el filtro por LOCAL funcione correctamente.

    En el dataset ficticio, las filas con LOCAL = 1999 son las de montos 10000 y 30000.
    La suma debe ser 40000 y el conteo 2.
    """
    response = client.get("/v1/estadisticas/ventas?LOCAL=1999")
    assert response.status_code == 200
    data = response.json()

    assert data["suma"] == 40000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 20000.0


# ─── PRUEBA 4: GET con valor inválido para LOCAL ──────────────────────────────
def test_get_error_tipo_invalido():
    """
    Verifica que la API rechace correctamente un valor no numérico para LOCAL.

    Si el usuario envía LOCAL=qwerty (un texto en lugar de un número),
    la API debe responder con HTTP 400 y el formato de error de la rúbrica.
    Específicamente verifica:
    - El código HTTP es 400.
    - errorCode es "VF" (Validación Fallida).
    - errorLabel es "Validación Fallida".
    - El detail contiene el valor inválido para que el usuario sepa qué falló.
    - El method es "GET" (el método de la petición original).
    """
    response = client.get("/v1/estadisticas/ventas?LOCAL=qwerty")
    assert response.status_code == 400
    data = response.json()

    assert data["status"] == 400
    assert data["errorCode"] == "VF"
    assert data["errorLabel"] == "Validación Fallida"
    assert "qwerty" in data["detail"]
    assert data["method"] == "GET"


# ─── PRUEBA 5: POST con lista de consultas vacía ──────────────────────────────
def test_post_sin_filtros_error():
    """
    Verifica que la API rechace un POST con la lista de consultas vacía.

    Según la rúbrica, "consultas vacío o nulo" es un error de validación (400).
    """
    response = client.post("/v1/estadisticas/ventas", json={"consultas": []})
    assert response.status_code == 400
    data = response.json()
    assert data["errorCode"] == "VF"


# ─── PRUEBA 6: POST con filtros combinados válidos ────────────────────────────
def test_post_con_filtros():
    """
    Verifica que el endpoint POST responda correctamente con múltiples filtros.

    Filtramos por CANAL=POS y GENERO=Femenino. En el dataset ficticio, la única
    fila que cumple AMBAS condiciones (AND lógico) es la de monto 40000.
    """
    payload = {
        "consultas": [
            {"consulta": "CANAL", "valor": "POS"},
            {"consulta": "GENERO", "valor": "Femenino"}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Solo 1 fila cumple ambos filtros: monto = 40000
    assert data["suma"] == 40000.0
    assert data["conteo"] == 1
    assert data["promedio"] == 40000.0
    assert data["minimo"] == 40000.0
    assert data["maximo"] == 40000.0
    assert data["mediana"] == 40000.0


# ─── PRUEBA 7: POST con campo de consulta no permitido ───────────────────────
def test_post_error_campo_invalido():
    """
    Verifica que la API rechace un POST con un nombre de campo que no existe.

    Si el usuario envía "CAMPO_INVALIDO" como nombre de consulta, la API debe
    responder con HTTP 400 y el formato de error de la rúbrica.
    Verificamos que el mensaje de error contenga el nombre del campo inválido
    para que el usuario sepa exactamente qué está mal.
    """
    payload = {
        "consultas": [
            {"consulta": "CAMPO_INVALIDO", "valor": "WEB"}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["errorCode"] == "VF"
    assert "CAMPO_INVALIDO" in data["detail"]

# ─── PRUEBA 8: GET con filtro de CODIGO_PRODUCTO ──────────────────────────────
def test_get_con_filtro_codigo_producto():
    """
    CODIGO_PRODUCTO=1095 aparece en 2 filas del mock (montos 10000 y 30000).
    """
    response = client.get("/v1/estadisticas/ventas?CODIGO_PRODUCTO=1095")
    assert response.status_code == 200
    data = response.json()
 
    assert data["suma"] == 40000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 20000.0
    assert data["minimo"] == 10000.0
    assert data["maximo"] == 30000.0
 
 
# ─── PRUEBA 9: GET con filtro de ID_PERSONA ───────────────────────────────────
def test_get_con_filtro_id_persona():
    """
    Filtra por un UUID específico; debe devolver exactamente 1 fila (monto 20000).
    """
    response = client.get(
        "/v1/estadisticas/ventas?ID_PERSONA=550e8400-e29b-41d4-a716-446655440001"
    )
    assert response.status_code == 200
    data = response.json()
 
    assert data["conteo"] == 1
    assert data["suma"] == 20000.0
    assert data["desviacion_estandar"] == 0.0  # con 1 solo valor, dispersión = 0
 
 
# ─── PRUEBA 10: GET con rango FECHA_DESDE / FECHA_HASTA ───────────────────────
def test_get_con_filtro_rango_fechas():
    """
    Filtra ventas entre 2026-05-09 y 2026-05-10 (inclusive).
    Deben quedar las filas con montos 20000 (09 may) y 30000 (10 may).
    """
    response = client.get(
        "/v1/estadisticas/ventas?FECHA_DESDE=2026-05-09&FECHA_HASTA=2026-05-10T23:59:59"
    )
    assert response.status_code == 200
    data = response.json()
 
    assert data["conteo"] == 2
    assert data["suma"] == 50000.0
    assert data["minimo"] == 20000.0
    assert data["maximo"] == 30000.0
 
 
# ─── PRUEBA 11: Consulta que no encuentra ninguna fila ────────────────────────
def test_get_sin_resultados_devuelve_ceros():
    """
    Un filtro válido pero que no matchea ninguna fila (LOCAL inexistente)
    no debe lanzar error: debe devolver 200 con todas las métricas en 0.
    """
    response = client.get("/v1/estadisticas/ventas?LOCAL=99999")
    assert response.status_code == 200
    data = response.json()
 
    assert data["suma"] == 0.0
    assert data["conteo"] == 0
    assert data["promedio"] == 0.0
    assert data["minimo"] == 0.0
    assert data["maximo"] == 0.0
    assert data["mediana"] == 0.0
    assert data["desviacion_estandar"] == 0.0
 
 
# ─── PRUEBA 12: POST con GENERO inválido (400) ────────────────────────────────
def test_post_error_genero_invalido():
    """
    El mismo caso de la prueba 8 del enunciado original (GENERO inválido)
    pero probado por la vía POST en vez de GET, ya que la validación se
    comparte pero el 'method' reportado en el error debe ser distinto.
    """
    payload = {
        "consultas": [
            {"consulta": "GENERO", "valor": "Extraterrestre"}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 400
    data = response.json()
 
    assert data["errorCode"] == "VF"
    assert "Extraterrestre" in data["detail"]
    assert data["method"] == "POST"
 
 
# ─── PRUEBA 13: POST con CANAL inválido (400) ─────────────────────────────────
def test_post_error_canal_invalido():
    payload = {
        "consultas": [
            {"consulta": "CANAL", "valor": "PIRATA"}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 400
    data = response.json()
 
    assert data["errorCode"] == "VF"
    assert "PIRATA" in data["detail"]
 
 
# ─── PRUEBA 14: Formato de error 500 ───────────────────────────────────────────
def test_get_error_interno_formato_500(monkeypatch):
    """
    Fuerza un error 500 rompiendo intencionalmente el motor de estadísticas,
    para verificar que el formato de error interno cumple exactamente con
    la rúbrica (errorCode 'IE', title 'Internal Server Error', etc.)
    """
    import src.routes as routes_module
 
    def calcular_estadisticas_roto(df):
        raise RuntimeError("fallo simulado para probar error 500")
 
    monkeypatch.setattr(routes_module, "calcular_estadisticas", calcular_estadisticas_roto)
 
    response = client.get("/v1/estadisticas/ventas")
    assert response.status_code == 500
    data = response.json()
 
    assert data["status"] == 500
    assert data["title"] == "Internal Server Error"
    assert data["errorCode"] == "IE"
    assert data["errorLabel"] == "Error Interno"
    assert data["method"] == "GET"
    assert "instance" in data and data["instance"] == "/v1/estadisticas/ventas"
    assert "timestamp" in data
 
 
# ─── PRUEBA 15: Ruta inexistente → 404 con formato de la rúbrica ──────────────
def test_ruta_inexistente_404():
    response = client.get("/v1/ruta/que/no/existe")
    assert response.status_code == 404
    data = response.json()
 
    assert data["status"] == 404
    assert data["errorCode"] == "RNF"
    assert data["title"] == "Not Found"