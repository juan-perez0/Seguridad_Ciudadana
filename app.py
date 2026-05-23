from flask import Flask, render_template

app = Flask(__name__)

# PEGA TU LINK DE POWER BI AQUÍ
POWERBI_URL = "https://app.powerbi.com/view?r=eyJrIjoiMWMwMWY0NGMtMmEwNS00ZjJlLTlhMzUtMTFkMDkyYmIxZTE3IiwidCI6IjA3ZGE2N2EwLTFmNDMtNGU4Yy05NzdmLTVmODhiNjQ3MGVlNiIsImMiOjR9"

@app.route("/")
def index():
    return render_template("index.html", powerbi_url=POWERBI_URL)

# Página análisis general
@app.route("/analisis")
def analisis():
    return render_template("mineria.html")

#  PySpark
@app.route("/pyspark")
def pyspark():
    return render_template("pyspark.html")

if __name__ == "__main__":
    app.run(debug=True)