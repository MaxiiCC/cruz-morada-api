import pytest
import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

# Datos ficticios para los tests (4 filas simples)
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
    # Inyecta los datos de prueba antes de cada test
    app.state.df = df_mock

client = TestClient(app)

# Test de GET sin filtros (calcula todo el dataset)
def test_get_sin_filtros():
    response = client.get("/v1/estadisticas/ventas")
    assert response.status_code == 200
    data = response.json()
    assert data["suma"] == 100000.0
    assert data["conteo"] == 4
    assert data["promedio"] == 25000.0
    assert data["minimo"] == 10000.0
    assert data["maximo"] == 40000.0
    assert data["mediana"] == 25000.0
    assert data["desviacion_estandar"] > 0

# Test de GET con filtro de genero
def test_get_con_filtro_genero():
    response = client.get("/v1/estadisticas/ventas?GENERO=Femenino")
    assert response.status_code == 200
    data = response.json()
    assert data["suma"] == 60000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 30000.0
    assert data["mediana"] == 30000.0

# Test de GET con filtro de local
def test_get_con_filtro_local():
    response = client.get("/v1/estadisticas/ventas?LOCAL=1999")
    assert response.status_code == 200
    data = response.json()
    assert data["suma"] == 40000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 20000.0

# Test de error 400 si el parametro tiene tipo invalido
def test_get_error_tipo_invalido():
    response = client.get("/v1/estadisticas/ventas?LOCAL=qwerty")
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == 400
    assert data["errorCode"] == "VF"
    assert data["errorLabel"] == "Validación Fallida"
    assert "qwerty" in data["detail"]
    assert data["method"] == "GET"

# Test de error 400 si el POST viene vacio
def test_post_sin_filtros_error():
    response = client.post("/v1/estadisticas/ventas", json={"consultas": []})
    assert response.status_code == 400
    data = response.json()
    assert data["errorCode"] == "VF"

# Test de POST con multiples filtros combinados (AND)
def test_post_con_filtros():
    payload = {
        "consultas": [
            {"consulta": "CANAL", "valor": "POS"},
            {"consulta": "GENERO", "valor": "Femenino"}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["suma"] == 40000.0
    assert data["conteo"] == 1
    assert data["promedio"] == 40000.0
    assert data["minimo"] == 40000.0
    assert data["maximo"] == 40000.0
    assert data["mediana"] == 40000.0

# Test de error 400 si el POST tiene un campo de consulta invalido
def test_post_error_campo_invalido():
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

# Test de GET con filtro de codigo de producto
def test_get_con_filtro_codigo_producto():
    response = client.get("/v1/estadisticas/ventas?CODIGO_PRODUCTO=1095")
    assert response.status_code == 200
    data = response.json()
    assert data["suma"] == 40000.0
    assert data["conteo"] == 2
    assert data["promedio"] == 20000.0
    assert data["minimo"] == 10000.0
    assert data["maximo"] == 30000.0

# Test de GET con filtro de ID de persona
def test_get_con_filtro_id_persona():
    response = client.get(
        "/v1/estadisticas/ventas?ID_PERSONA=550e8400-e29b-41d4-a716-446655440001"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conteo"] == 1
    assert data["suma"] == 20000.0
    assert data["desviacion_estandar"] == 0.0

# Test de GET con rango de fechas
def test_get_con_filtro_rango_fechas():
    response = client.get(
        "/v1/estadisticas/ventas?FECHA_DESDE=2026-05-09&FECHA_HASTA=2026-05-10T23:59:59"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conteo"] == 2
    assert data["suma"] == 50000.0
    assert data["minimo"] == 20000.0
    assert data["maximo"] == 30000.0

# Test de retorno de ceros si el filtro no encuentra filas
def test_get_sin_resultados_devuelve_ceros():
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

# Test de POST con genero no permitido (400)
def test_post_error_genero_invalido():
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

# Test de POST con canal no permitido (400)
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

# Test de estructura de error 500
def test_get_error_interno_formato_500(monkeypatch):
    import src.routes as routes_module
    def calcular_estadisticas_roto(df):
        raise RuntimeError("Fallo forzado en tests")
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

# Test de ruta inexistente (404)
def test_ruta_inexistente_404():
    response = client.get("/v1/ruta/que/no/existe")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == 404
    assert data["errorCode"] == "RNF"
    assert data["title"] == "Not Found"

# Test de FECHA_HASTA sin hora (debe incluir el dia completo)
def test_get_filtro_fecha_hasta_sin_hora_incluye_dia_completo():
    response = client.get(
        "/v1/estadisticas/ventas?FECHA_DESDE=2026-05-09&FECHA_HASTA=2026-05-10"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conteo"] == 2
    assert data["suma"] == 50000.0
    assert data["minimo"] == 20000.0
    assert data["maximo"] == 30000.0

# Test de GET con edad booleana (400)
def test_get_error_edad_booleano():
    response = client.get("/v1/estadisticas/ventas?EDAD=true")
    assert response.status_code == 400
    data = response.json()
    assert data["errorCode"] == "VF"
    assert "true" in data["detail"].lower()

# Test de POST con edad booleana (400)
def test_post_error_edad_booleano():
    payload = {
        "consultas": [
            {"consulta": "EDAD", "valor": True}
        ]
    }
    response = client.post("/v1/estadisticas/ventas", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["errorCode"] == "VF"
    assert "true" in data["detail"].lower()