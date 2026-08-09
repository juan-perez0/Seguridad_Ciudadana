import pytest

from app import app as flask_app, convertir_numero, formatear_numero, obtener_valor


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        yield client


@pytest.mark.parametrize("route", ["/", "/mineria", "/pyspark"])
def test_routes_return_200(client, route):
    response = client.get(route)
    assert response.status_code == 200


def test_pyspark_page_contains_kpi_section(client):
    response = client.get("/pyspark")
    assert b"M\xc3\xa9tricas generales del procesamiento" in response.data


def test_convertir_numero_parses_plain_decimal():
    assert convertir_numero("2114711.9") == 2114711.9
    assert convertir_numero("0.0617") == 0.0617


def test_convertir_numero_falls_back_to_latin_format():
    assert convertir_numero("1.234,56") == 1234.56


def test_convertir_numero_handles_missing_values():
    assert convertir_numero("") == 0.0
    assert convertir_numero(None) == 0.0
    assert convertir_numero("no-numerico") == 0.0


def test_formatear_numero_does_not_inflate_plain_decimals():
    assert formatear_numero("2114711.9") == "2.114.711,90"
    assert formatear_numero("0.0617") == "0,06"


def test_formatear_numero_keeps_non_numeric_values_unchanged():
    assert formatear_numero("KMeans") == "KMeans"
    assert formatear_numero("local[4]") == "local[4]"


def test_obtener_valor_prefers_first_non_empty_column():
    fila = {"TOTAL_CASOS": "10", "TOTAL_CASOS_PROCESADOS": ""}
    assert obtener_valor(fila, "TOTAL_CASOS_PROCESADOS", "TOTAL_CASOS") == "10"


def test_obtener_valor_returns_default_when_missing():
    assert obtener_valor({}, "COLUMNA_INEXISTENTE") == "0"
