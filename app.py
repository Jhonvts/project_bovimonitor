from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)


# ==========================================================
#                    CONFIGURAÇÃO
# ==========================================================

app.config["SECRET_KEY"] = "bovimonitor_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bovimonitor.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)


# ==========================================================
#                  CONFIGURAÇÃO DO LOGIN
# ==========================================================

login_manager = LoginManager(app)

login_manager.login_view = "login"

login_manager.login_message = "Faça login para acessar essa página."


# ==========================================================
#                       USUÁRIO
# ==========================================================

class Usuario(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    telefone = db.Column(
        db.String(20),
        nullable=False
    )

    senha = db.Column(
        db.String(255),
        nullable=False
    )

    perfil = db.Column(
        db.String(20),
        nullable=False,
        default="usuario"
    )


# ==========================================================
#                         LOTE
# ==========================================================

class Lote(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    quantidade_cabecas = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ATIVO"
    )


# ==========================================================
#                  VACINA / MEDICAMENTO
# ==========================================================

class Vacina(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nome = db.Column(
        db.String(100),
        nullable=False
    )

    tipo = db.Column(
        db.String(20),
        nullable=False
    )

    dias_carencia = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    obrigatoria = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )


# ==========================================================
#                   MANEJO SANITÁRIO
# ==========================================================

class ManejoSanitario(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    lote_id = db.Column(
        db.Integer,
        db.ForeignKey("lote.id"),
        nullable=False
    )

    vacina_id = db.Column(
        db.Integer,
        db.ForeignKey("vacina.id"),
        nullable=False
    )

    data_aplicacao = db.Column(
        db.Date,
        nullable=False
    )

    data_liberacao = db.Column(
        db.Date,
        nullable=False
    )

    observacao = db.Column(
        db.Text
    )


# ==========================================================
#                  GERENCIADOR DE LOGIN
# ==========================================================

@login_manager.user_loader
def carregar_usuario(user_id):

    return db.session.get(
        Usuario,
        int(user_id)
    )


# ==========================================================
#                    PÁGINA INICIAL
# ==========================================================

@app.route("/")
def index():

    return redirect(
        url_for("login")
    )


# ==========================================================
#                       CADASTRO
# ==========================================================

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form["nome"]

        email = request.form["email"]

        telefone = request.form["telefone"]

        senha = request.form["senha"]


        usuario_existente = Usuario.query.filter_by(
            email=email
        ).first()


        if usuario_existente:

            flash(
                "Este e-mail já está cadastrado."
            )

            return redirect(
                url_for("cadastro")
            )


        senha_hash = generate_password_hash(
            senha
        )


        novo_usuario = Usuario(

            nome=nome,

            email=email,

            telefone=telefone,

            senha=senha_hash

        )


        db.session.add(
            novo_usuario
        )

        db.session.commit()


        flash(
            "Cadastro realizado com sucesso!"
        )

        return redirect(
            url_for("resumo_Vacinas")
        )


    return render_template(
        "cadastro.html"
    )


# ==========================================================
#                         LOGIN
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]

        senha = request.form["senha"]


        usuario = Usuario.query.filter_by(
            email=email
        ).first()


        if usuario and check_password_hash(
            usuario.senha,
            senha
        ):

            login_user(usuario)

            return redirect(
                url_for("perfil")
            )


        flash(
            "E-mail ou senha incorretos!"
        )


    return render_template(
        "login.html"
    )


# ==========================================================
#                         LOGOUT
# ==========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "Você saiu da sua conta."
    )

    return redirect(
        url_for("login")
    )


# ==========================================================
#                         PERFIL
# ==========================================================

@app.route("/perfil")
@login_required
def perfil():

    return render_template(
        "perfil.html",
        usuario=current_user
    )


# ==========================================================
#                    EDITAR PERFIL
# ==========================================================

@app.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def editar_perfil():

    if request.method == "POST":

        current_user.nome = request.form["nome"]

        current_user.telefone = request.form["telefone"]

        db.session.commit()


        flash(
            "Perfil atualizado com sucesso!"
        )


        return redirect(
            url_for("perfil")
        )


    return render_template(
        "editar_perfil.html",
        usuario=current_user
    )


# ==========================================================
#                         LOTES
# ==========================================================

@app.route(
    "/lotes",
    methods=["GET", "POST"]
)
@login_required
def lotes():

    if request.method == "POST":

        nome = request.form["nome"]

        quantidade = request.form["quantidade"]


        novo_lote = Lote(

            usuario_id=current_user.id,

            nome=nome,

            quantidade_cabecas=quantidade,

            status="ATIVO"

        )


        db.session.add(
            novo_lote
        )

        db.session.commit()


        flash(
            "Lote cadastrado com sucesso!"
        )


        return redirect(
            url_for("lotes")
        )


    lista_lotes = Lote.query.filter_by(
        usuario_id=current_user.id
    ).all()


    return render_template(
        "registroLotes.html",
        lotes=lista_lotes
    )


# ==========================================================
#                      EDITAR LOTE
# ==========================================================

@app.route(
    "/lotes/<int:id>/editar",
    methods=["GET", "POST"]
)
@login_required
def editar_lote(id):

    lote = Lote.query.get_or_404(id)


    if lote.usuario_id != current_user.id:

        flash(
            "Você não pode editar este lote."
        )

        return redirect(
            url_for("lotes")
        )


    if request.method == "POST":

        lote.nome = request.form["nome"]

        lote.quantidade_cabecas = request.form["quantidade"]

        lote.status = request.form["status"]


        db.session.commit()


        flash(
            "Lote atualizado com sucesso!"
        )


        return redirect(
            url_for("lotes")
        )


    return render_template(
        "editarLotes.html",
        lote=lote
    )


# ==========================================================
#                     EXCLUIR LOTE
# ==========================================================

@app.route(
    "/lotes/<int:id>/excluir",
    methods=["POST"]
)
@login_required
def excluir_lote(id):

    lote = Lote.query.get_or_404(id)


    if lote.usuario_id != current_user.id:

        flash(
            "Você não pode excluir este lote."
        )

        return redirect(
            url_for("lotes")
        )


    db.session.delete(
        lote
    )

    db.session.commit()


    flash(
        "Lote excluído com sucesso!"
    )


    return redirect(
        url_for("lotes")
    )


# ==========================================================
#                CADASTRAR VACINA / MEDICAMENTO
# ==========================================================

@app.route(
    "/vacinas/cadastro",
    methods=["GET", "POST"]
)
@login_required
def cadastro_vacina():

    if request.method == "POST":

        nome = request.form["nome"]

        tipo = request.form["tipo"]

        dias_carencia = request.form["dias_carencia"]

        obrigatoria = request.form["obrigatoria"]


        if obrigatoria == "sim":

            obrigatoria = True

        else:

            obrigatoria = False


        nova_vacina = Vacina(

            nome=nome,

            tipo=tipo,

            dias_carencia=dias_carencia,

            obrigatoria=obrigatoria

        )


        db.session.add(
            nova_vacina
        )

        db.session.commit()


        flash(
            "Vacina ou medicamento cadastrado com sucesso!"
        )


        return redirect(
            url_for("historico_vacinas")
        )


    return render_template(
        "historico_deVacinas.html",
        vacinas=lista_vacinas
    )


# ==========================================================
#                   HISTÓRICO DE VACINAS
# ==========================================================

@app.route("/vacinas")
@login_required
def historico_vacinas():

    lista_vacinas = Vacina.query.all()


    return render_template(
        "historico_deVacinas.html",
        vacinas=lista_vacinas
    )


# ==========================================================
#                    EDITAR VACINA
# ==========================================================

@app.route(
    "/vacinas/<int:id>/editar",
    methods=["GET", "POST"]
)
@login_required
def editar_vacina(id):

    vacina = Vacina.query.get_or_404(id)


    if request.method == "POST":

        vacina.nome = request.form["nome"]

        vacina.tipo = request.form["tipo"]

        vacina.dias_carencia = request.form["dias_carencia"]


        if request.form["obrigatoria"] == "sim":

            vacina.obrigatoria = True

        else:

            vacina.obrigatoria = False


        db.session.commit()


        flash(
            "Vacina atualizada com sucesso!"
        )


        return redirect(
            url_for("historico_vacinas")
        )


    return render_template(
        "editar_manejo.html",
        vacina=vacina
    )


# ==========================================================
#                   EXCLUIR VACINA
# ==========================================================

@app.route(
    "/vacinas/<int:id>/excluir",
    methods=["POST"]
)
@login_required
def deletar_vacina(id):

    vacina = Vacina.query.get_or_404(id)


    db.session.delete(
        vacina
    )

    db.session.commit()


    flash(
        "Vacina excluída com sucesso!"
    )


    return redirect(
        url_for("historico_vacinas")
    )


# ==========================================================
#                     RESUMO DE VACINAS
# ==========================================================

@app.route("/vacinas/resumo")
@login_required
def resumo_vacinas():

    total_vacinas = Vacina.query.filter_by(
        tipo="Vacina"
    ).count()


    total_medicamentos = Vacina.query.filter_by(
        tipo="Medicamento"
    ).count()


    vacinas_obrigatorias = Vacina.query.filter_by(
        obrigatoria=True
    ).count()


    vacinas_com_carencia = Vacina.query.filter(
        Vacina.dias_carencia > 0
    ).count()


    metrics = {

        "total_vacinas": total_vacinas,

        "total_medicamentos": total_medicamentos,

        "vacinas_obrigatorias": vacinas_obrigatorias,

        "vacinas_com_carencia": vacinas_com_carencia

    }


    return render_template(
        "resumo_Vacinas.html",
        metrics=metrics
    )


# ==========================================================
#                  CRIAÇÃO DO BANCO
# ==========================================================

with app.app_context():

    db.create_all()


# ==========================================================
#                       EXECUÇÃO
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)