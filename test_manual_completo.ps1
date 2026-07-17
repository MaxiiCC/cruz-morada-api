# =============================================================================
# test_manual_completo.ps1
# Script de prueba manual exhaustivo para la API Cruz Morada
# Requiere que el servidor esté corriendo en http://localhost:8000
# =============================================================================

$BASE = "http://localhost:8000/v1/estadisticas/ventas"
$OK = 0
$FAIL = 0

function Test-Caso {
    param($nombre, $status_esperado, $body_json = $null, $url = $BASE)
    try {
        if ($body_json) {
            $resp = Invoke-WebRequest -Uri $url -Method POST -UseBasicParsing `
                -Body $body_json -ContentType "application/json" -ErrorAction Stop
        } else {
            $resp = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -ErrorAction Stop
        }
        $status_real = $resp.StatusCode
    } catch {
        $status_real = $_.Exception.Response.StatusCode.value__
    }

    if ($status_real -eq $status_esperado) {
        Write-Host "  OK  $nombre (HTTP $status_real)" -ForegroundColor Green
        $script:OK++
    } else {
        Write-Host "  FAIL  $nombre --- esperado $status_esperado, obtuvo $status_real" -ForegroundColor Red
        $script:FAIL++
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   SUITE DE PRUEBAS MANUAL --- Cruz Morada API" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n[GET] Sin filtros" -ForegroundColor Yellow
Test-Caso "GET dataset completo" 200

Write-Host "`n[GET] Cada filtro permitido individualmente" -ForegroundColor Yellow
Test-Caso "Filtro GENERO=Femenino"         200 -url "$BASE`?GENERO=Femenino"
Test-Caso "Filtro GENERO=Masculino"        200 -url "$BASE`?GENERO=Masculino"
Test-Caso "Filtro EDAD=31"                 200 -url "$BASE`?EDAD=31"
Test-Caso "Filtro CANAL=POS"              200 -url "$BASE`?CANAL=POS"
Test-Caso "Filtro CANAL=WEB"              200 -url "$BASE`?CANAL=WEB"
Test-Caso "Filtro LOCAL=371"              200 -url "$BASE`?LOCAL=371"
Test-Caso "Filtro CODIGO_PRODUCTO=201"    200 -url "$BASE`?CODIGO_PRODUCTO=201"
Test-Caso "Filtro FECHA_DESDE=2023-01-01" 200 -url "$BASE`?FECHA_DESDE=2023-01-01"
Test-Caso "Filtro FECHA_HASTA=2024-12-31" 200 -url "$BASE`?FECHA_HASTA=2024-12-31"
Test-Caso "Rango de fechas sin hora (bug fix)" 200 -url "$BASE`?FECHA_DESDE=2023-11-01&FECHA_HASTA=2023-11-30"
Test-Caso "Filtro fechas con zona horaria (tz-aware)" 200 -url "$BASE`?FECHA_DESDE=2023-11-01T00:00:00Z&FECHA_HASTA=2023-11-30T23:59:59-04:00"

Write-Host "`n[GET] Valores en los bordes de rango" -ForegroundColor Yellow
Test-Caso "EDAD=0 (limite inferior valido)"   200 -url "$BASE`?EDAD=0"
Test-Caso "EDAD=120 (limite superior valido)" 200 -url "$BASE`?EDAD=120"
Test-Caso "EDAD=121 (fuera de rango -> 400)"  400 -url "$BASE`?EDAD=121"
Test-Caso "EDAD=-1 (negativo -> 400)"         400 -url "$BASE`?EDAD=-1"
Test-Caso "LOCAL=0 (cero -> 400 post-fix)"    400 -url "$BASE`?LOCAL=0"
Test-Caso "CODIGO_PRODUCTO=0 (cero -> 400)"   400 -url "$BASE`?CODIGO_PRODUCTO=0"

Write-Host "`n[GET] Valores invalidos -> 400" -ForegroundColor Yellow
Test-Caso "LOCAL=abc (texto)"                400 -url "$BASE`?LOCAL=abc"
Test-Caso "LOCAL=3.5 (float)"                400 -url "$BASE`?LOCAL=3.5"
Test-Caso "EDAD=treinta (texto)"             400 -url "$BASE`?EDAD=treinta"
Test-Caso "CANAL=PIRATA (no permitido)"      400 -url "$BASE`?CANAL=PIRATA"
Test-Caso "GENERO=Extraterrestre"            400 -url "$BASE`?GENERO=Extraterrestre"
Test-Caso "FECHA_DESDE=no-es-fecha"          400 -url "$BASE`?FECHA_DESDE=no-es-fecha"
Test-Caso "GET campo no permitido -> 400"    400 -url "$BASE`?CAMPO_ERRONEO=1"

Write-Host "`n[POST] Consultas validas" -ForegroundColor Yellow
$p1 = '{"consultas":[{"consulta":"CANAL","valor":"POS"}]}'
$p2 = '{"consultas":[{"consulta":"GENERO","valor":"Femenino"},{"consulta":"EDAD","valor":"31"},{"consulta":"CANAL","valor":"POS"}]}'
$p3 = '{"consultas":[{"consulta":"LOCAL","valor":"371"},{"consulta":"CANAL","valor":"POS"}]}'
Test-Caso "POST un filtro (CANAL=POS)"       200 $p1
Test-Caso "POST tres filtros combinados AND" 200 $p2
Test-Caso "POST filtros LOCAL + CANAL"       200 $p3

Write-Host "`n[POST] Errores de validacion -> 400" -ForegroundColor Yellow
$e1 = '{"consultas":[]}'
$e2 = '{"consultas":[{"consulta":"CAMPO_FALSO","valor":"x"}]}'
$e3 = '{"consultas":[{"consulta":"EDAD","valor":31.7}]}'
$e4 = '{"consultas":[{"consulta":"LOCAL","valor":0}]}'
$e5 = '{"consultas":[{"consulta":"EDAD","valor":200}]}'
$e6 = '{"consultas":[{"consulta":"CANAL","valor":"PIRATA"}]}'
$e7 = '{"consultas":[{"consulta":"GENERO","valor":"Marcianos"}]}'
Test-Caso "POST lista vacia -> 400"               400 $e1
Test-Caso "POST campo no permitido -> 400"        400 $e2
Test-Caso "POST EDAD float 31.7 -> 400 (bugfix)" 400 $e3
Test-Caso "POST LOCAL=0 -> 400 (bugfix)"          400 $e4
Test-Caso "POST EDAD=200 fuera de rango -> 400"   400 $e5
Test-Caso "POST CANAL invalido -> 400"            400 $e6
Test-Caso "POST GENERO invalido -> 400"           400 $e7

Write-Host "`n[HTTP] Rutas inexistentes" -ForegroundColor Yellow
Test-Caso "Ruta inexistente -> 404" 404 -url "http://localhost:8000/v1/ruta/falsa"
Test-Caso "Raiz del servidor -> 404" 404 -url "http://localhost:8000/"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
$total = $OK + $FAIL
if ($FAIL -eq 0) {
    Write-Host "   RESULTADO: $OK/$total pruebas pasaron - API lista para entregar!" -ForegroundColor Green
} else {
    Write-Host "   RESULTADO: $OK/$total pruebas pasaron - $FAIL fallaron" -ForegroundColor Red
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
