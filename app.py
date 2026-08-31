from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("cadastro_lote.html")

@app.route("/cadastro-lote", methods=["GET", "POST"])
def cadastro_lote():
    mensagem = None
    erro = None

    if request.method == "POST":
        nome_lote = request.form.get("nome_lote", "").strip()
        quantidade = request.form.get("quantidade_cabecas", "").strip()
        status = request.form.get("status", "").strip()

        # Validação do nome
        if not nome_lote:
            erro = "O nome do lote é obrigatório."

        # Validação da quantidade
        elif not quantidade.isdigit():
            erro = "A quantidade deve ser um número inteiro."

        elif int(quantidade) <= 0:
            erro = "A quantidade deve ser maior que zero."

        # Validação do status
        elif status not in ["Ativo", "Inativo"]:
            erro = "Selecione um status válido."

        else:
            quantidade = int(quantidade)

            # Exibe os dados no terminal para confirmação
            print("Novo lote cadastrado:")
            print("Nome:", nome_lote)
            print("Quantidade:", quantidade)
            print("Status:", status)

            mensagem = "Lote cadastrado com sucesso!"

    return render_template(
        "cadastro_lote.html",
        mensagem=mensagem,
        erro=erro
    )

if __name__ == "__main__":
    app.run(debug=True)