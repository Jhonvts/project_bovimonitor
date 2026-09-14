from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# Lista que armazena os lotes
lotes = []

# --------------------------------------------------
# PÁGINA INICIAL
# --------------------------------------------------

@app.route("/")
def index():
    total_lotes = len(lotes)
    total_cabecas = sum(lote["quantidade"] for lote in lotes)

    return render_template(
        "index.html",
        lotes=lotes,
        total_lotes=total_lotes,
        total_cabecas=total_cabecas
    )


# --------------------------------------------------
# CADASTRAR LOTE
# --------------------------------------------------

@app.route("/cadastro-lote", methods=["GET", "POST"])
def cadastro_lote():

    if request.method == "POST":

        nome = request.form["nome"]
        quantidade = int(request.form["quantidade"])

        novo_lote = {
            "id": len(lotes) + 1,
            "nome": nome,
            "quantidade": quantidade,
            "vacina": "",
            "ultima_vacinacao": "",
            "proxima_vacinacao": ""
        }

        lotes.append(novo_lote)

        return redirect(url_for("index"))

    return render_template("cadastro_lote.html")


# --------------------------------------------------
# EDITAR QUANTIDADE DO LOTE
# --------------------------------------------------

@app.route("/editar-lote/<int:id>", methods=["GET", "POST"])
def editar_lote(id):

    lote = next((l for l in lotes if l["id"] == id), None)

    if lote is None:
        return "Lote não encontrado", 404

    if request.method == "POST":

        lote["nome"] = request.form["nome"]
        lote["quantidade"] = int(request.form["quantidade"])

        return redirect(url_for("index"))

    return render_template("editar_lote.html", lote=lote)


# --------------------------------------------------
# REGISTRAR VACINAÇÃO
# --------------------------------------------------

@app.route("/vacinacao/<int:id>", methods=["GET", "POST"])
def vacinacao(id):

    lote = next((l for l in lotes if l["id"] == id), None)

    if lote is None:
        return "Lote não encontrado", 404

    if request.method == "POST":

        lote["vacina"] = request.form["vacina"]
        lote["ultima_vacinacao"] = request.form["ultima_vacinacao"]
        lote["proxima_vacinacao"] = request.form["proxima_vacinacao"]

        return redirect(url_for("index"))

    return render_template("vacinacao.html", lote=lote)


# --------------------------------------------------
# FUNÇÃO PARA VERIFICAR STATUS DA VACINAÇÃO
# --------------------------------------------------

def verificar_status(data):

    if not data:
        return "Sem registro"

    hoje = datetime.now().date()
    data_vacinacao = datetime.strptime(data, "%Y-%m-%d").date()

    diferenca = (data_vacinacao - hoje).days

    if diferenca < 0:
        return "Atrasada"

    elif diferenca <= 30:
        return "Próxima"

    else:
        return "Em dia"


# --------------------------------------------------
# EXECUTAR SISTEMA
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)