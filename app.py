from flask import Flask, render_template

app = Flask(__name__)

POWERBI_URL = "https://app.powerbi.com/view?r=eyJrIjoiZjJmNzU2MGQtZjI0Ni00YmE1LTgxODItMzEwNDg3M2ZkMmQ3IiwidCI6IjA3ZGE2N2EwLTFmNDMtNGU4Yy05NzdmLTVmODhiNjQ3MGVlNiIsImMiOjR9"


@app.route("/")
def index():
    return render_template("index.html", powerbi_url=POWERBI_URL)


@app.route("/mineria")
def mineria():
    return render_template("mineria.html")


if __name__ == "__main__":
    app.run(debug=True)