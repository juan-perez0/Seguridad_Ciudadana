import os
from flask import Flask, render_template
import csv
from pathlib import Path
from collections import Counter

app = Flask(__name__)

DEFAULT_POWERBI_URL = "https://app.powerbi.com/view?r=eyJrIjoiZjJmNzU2MGQtZjI0Ni00YmE1LTgxODItMzEwNDg3M2ZkMmQ3IiwidCI6IjA3ZGE2N2EwLTFmNDMtNGU4Yy05NzdmLTVmODhiNjQ3MGVlNiIsImMiOjR9"
POWERBI_URL = os.environ.get("POWERBI_URL", DEFAULT_POWERBI_URL)


def leer_csv(nombre_archivo, limite=None):
    ruta = Path(app.root_path) / "data" / nombre_archivo

    if not ruta.exists():
        return []

    with open(ruta, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        filas = list(lector)

    if limite:
        return filas[:limite]

    return filas


def obtener_valor(fila, *columnas):
    for columna in columnas:
        if columna in fila and fila[columna] not in [None, ""]:
            return fila[columna]
    return "0"


def convertir_numero(valor):
    if valor in (None, ""):
        return 0.0

    texto = str(valor).strip()

    try:
        return float(texto)
    except ValueError:
        pass

    try:
        return float(texto.replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def formatear_numero(valor):
    texto = str(valor).strip()

    try:
        numero = float(texto)
    except ValueError:
        try:
            numero = float(texto.replace(".", "").replace(",", "."))
        except ValueError:
            return valor

    if numero.is_integer():
        return f"{int(numero):,}".replace(",", ".")
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def construir_graficas(municipios, anios, clusters, tiempos):
    top_municipios = municipios[:10]

    chart_municipios = {
        "labels": [fila.get("MUNICIPIO", "") for fila in top_municipios],
        "values": [
            convertir_numero(obtener_valor(fila, "TOTAL_CASOS_PROCESADOS", "TOTAL_CASOS"))
            for fila in top_municipios
        ]
    }

    chart_anios = {
        "labels": [fila.get("YEAR", "") for fila in anios],
        "values": [
            convertir_numero(obtener_valor(fila, "TOTAL_PROCESADO", "TOTAL"))
            for fila in anios
        ]
    }

    conteo_clusters = Counter([
        fila.get("PERFIL_CLUSTER", fila.get("prediction", "Sin clasificar"))
        for fila in clusters
    ])

    chart_clusters = {
        "labels": list(conteo_clusters.keys()),
        "values": list(conteo_clusters.values())
    }

    chart_tiempos = {
        "labels": [fila.get("ESCENARIO", "") for fila in tiempos],
        "pandas": [convertir_numero(fila.get("TIEMPO_PANDAS", 0)) for fila in tiempos],
        "spark": [convertir_numero(fila.get("TIEMPO_SPARK", 0)) for fila in tiempos],
        "total": [convertir_numero(fila.get("TIEMPO_TOTAL", 0)) for fila in tiempos]
    }

    return {
        "municipios": chart_municipios,
        "anios": chart_anios,
        "clusters": chart_clusters,
        "tiempos": chart_tiempos
    }


app.jinja_env.filters["numero"] = formatear_numero


@app.route("/")
def index():
    return render_template("index.html", powerbi_url=POWERBI_URL)


@app.route("/mineria")
def mineria():
    return render_template("mineria.html")


@app.route("/pyspark")
def pyspark():
    municipios = leer_csv("municipios_pyspark.csv", 10)
    anios = leer_csv("anios_pyspark.csv")
    promedios = leer_csv("promedios_pyspark.csv", 10)
    clusters = leer_csv("clusters_pyspark.csv", 20)
    tiempos = leer_csv("tiempos_pyspark.csv")
    metricas = leer_csv("metricas_pyspark.csv")

    graficas = construir_graficas(municipios, anios, clusters, tiempos)

    return render_template(
        "pyspark.html",
        municipios=municipios,
        anios=anios,
        promedios=promedios,
        clusters=clusters,
        tiempos=tiempos,
        metricas=metricas,
        graficas=graficas
    )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)