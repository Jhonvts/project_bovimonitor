import logging
import math
import os
from datetime import date, timedelta
from functools import wraps
from dotenv import load_dotenv

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "A variável SECRET_KEY não está configurada."
    )

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///bovimonitor.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

os.makedirs(app.instance_path, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Entre na sua conta para acessar esta página."
login_manager.login_message_category = "warning"

# isso nao é de Deus nao
# ==========================================================
# MODELOS DO BANCO
# ==========================================================
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    telefone = db.Column(db.String(20), nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="usuario")

    propriedade = db.relationship(
        "Propriedade", back_populates="usuario", uselist=False,
        cascade="all, delete-orphan"
    )
    lotes = db.relationship(
        "Lote", back_populates="usuario", cascade="all, delete-orphan",
        order_by="Lote.nome"
    )

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Propriedade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    nome = db.Column(db.String(120), nullable=False)
    localizacao = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float, nullable=False)
    usuario = db.relationship("Usuario", back_populates="propriedade")


class Lote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    nome = db.Column(db.String(100), nullable=False)
    quantidade_cabecas = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="ATIVO")
    usuario = db.relationship("Usuario", back_populates="lotes")
    manejos = db.relationship(
        "ManejoSanitario", back_populates="lote", cascade="all, delete-orphan",
        order_by="ManejoSanitario.data_aplicacao.desc()"
    )


class Vacina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    tipo = db.Column(db.String(20), nullable=False, default="Vacina")
    fabricante = db.Column(db.String(100), nullable=True)
    dias_carencia = db.Column(db.Integer, nullable=False, default=0)
    obrigatoria = db.Column(db.Boolean, nullable=False, default=False)
    manejos = db.relationship("ManejoSanitario", back_populates="vacina")


class ManejoSanitario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lote.id"), nullable=False)
    vacina_id = db.Column(db.Integer, db.ForeignKey("vacina.id"), nullable=False)
    data_aplicacao = db.Column(db.Date, nullable=False, default=date.today)
    data_liberacao = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(300), nullable=True)
    lote = db.relationship("Lote", back_populates="manejos")
    vacina = db.relationship("Vacina", back_populates="manejos")


@login_manager.user_loader
def carregar_usuario(user_id):
    try:
        return db.session.get(Usuario, int(user_id))
    except (TypeError, ValueError):
        return None


def registrar_evento(mensagem):
    usuario_id = current_user.get_id() if current_user.is_authenticated else "anonimo"
    logging.info("usuario_id=%s %s", usuario_id, mensagem)


def lote_do_usuario(lote_id):
    """Busca um lote pertencente à sessão atual; não expõe lotes de outras contas."""
    return Lote.query.filter_by(id=lote_id, usuario_id=current_user.id).first_or_404()


def manejo_do_usuario(manejo_id):
    return (
        ManejoSanitario.query.join(Lote)
        .filter(ManejoSanitario.id == manejo_id, Lote.usuario_id == current_user.id)
        .first_or_404()
    )


def atualizar_status_lote(lote):
    # Consulta o banco para também considerar inclusões/edições/exclusões ainda na sessão.
    em_carencia = ManejoSanitario.query.filter_by(lote_id=lote.id).filter(
        ManejoSanitario.data_liberacao > date.today()
    ).count() > 0
    lote.status = "BLOQUEADO" if em_carencia else "ATIVO"


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.perfil != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


# ==========================================================
# LOGIN E CADASTRO DE CONTA
# ==========================================================
@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        senha = request.form.get("senha", "")

        if not nome or not email or len(senha) < 8:
            flash("Preencha nome e e-mail. A senha deve ter pelo menos 8 caracteres.", "danger")
        elif Usuario.query.filter_by(email=email).first():
            flash("Já existe uma conta com esse e-mail.", "danger")
        else:
            usuario = Usuario(nome=nome, email=email, telefone=telefone or None)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            db.session.commit()
            login_user(usuario)
            registrar_evento("criou uma conta")
            flash("Conta criada com sucesso! Complete seu perfil.", "success")
            return redirect(url_for("perfil"))

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.verificar_senha(senha):
            login_user(usuario)
            registrar_evento("realizou login")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html")


@app.route("/sair", methods=["POST"])
@login_required
def sair():
    registrar_evento("realizou logout")
    logout_user()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("login"))


# ==========================================================
# PERFIL E PROPRIEDADE RURAL
# ==========================================================
@app.route("/perfil")
@login_required
def perfil():
    propriedade = Propriedade.query.filter_by(usuario_id=current_user.id).first()
    return render_template("perfil.html", usuario=current_user, propriedade=propriedade)


@app.route("/perfil/editar", methods=["GET", "POST"])
@login_required
def editar_perfil():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        if not nome:
            flash("O nome não pode ficar vazio.", "danger")
        else:
            current_user.nome = nome
            current_user.telefone = telefone or None
            db.session.commit()
            registrar_evento("atualizou o perfil")
            flash("Perfil atualizado com sucesso!", "success")
            return redirect(url_for("perfil"))
    return render_template("editar_perfil.html", usuario=current_user)



@app.route("/perfil/excluir", methods=["GET", "POST"])
@login_required
def excluir_perfil():
    # Impede que o administrador exclua a própria conta.
    if current_user.perfil == "admin":
        flash("O administrador não pode excluir o próprio perfil.", "danger")
        return redirect(url_for("perfil"))

    if request.method == "POST":
        usuario = db.session.get(Usuario, current_user.id)

        registrar_evento("solicitou exclusão da conta")
        logout_user()

        db.session.delete(usuario)
        db.session.commit()

        flash("Conta e dados vinculados foram excluídos.", "info")
        return redirect(url_for("login"))

    return render_template("excluir_perfil.html")



@app.route("/propriedade/cadastro", methods=["GET", "POST"])
@login_required
def cadastrar_propriedade():
    existente = Propriedade.query.filter_by(usuario_id=current_user.id).first()
    if existente:
        flash("Você já possui uma propriedade cadastrada.", "warning")
        return redirect(url_for("perfil"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        localizacao = request.form.get("localizacao", "").strip()
        area_texto = request.form.get("area", "").strip().replace(",", ".")
        try:
            area = float(area_texto)
        except (ValueError, TypeError):
            area = 0
        if not nome or not localizacao or not math.isfinite(area) or area <= 0:
            flash("Informe nome, localização e uma área maior que zero.", "danger")
        else:
            propriedade = Propriedade(
                usuario_id=current_user.id, nome=nome,
                localizacao=localizacao, area=area
            )
            db.session.add(propriedade)
            db.session.commit()
            registrar_evento("cadastrou propriedade rural")
            flash("Propriedade cadastrada com sucesso!", "success")
            return redirect(url_for("perfil"))
    return render_template("cadastro_propriedade.html")


@app.route("/propriedade/editar", methods=["GET", "POST"])
@login_required
def editar_propriedade():
    propriedade = Propriedade.query.filter_by(usuario_id=current_user.id).first_or_404()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        localizacao = request.form.get("localizacao", "").strip()
        area_texto = request.form.get("area", "").strip().replace(",", ".")
        try:
            area = float(area_texto)
        except (ValueError, TypeError):
            area = 0
        if not nome or not localizacao or not math.isfinite(area) or area <= 0:
            flash("Informe nome, localização e uma área maior que zero.", "danger")
        else:
            propriedade.nome = nome
            propriedade.localizacao = localizacao
            propriedade.area = area
            db.session.commit()
            registrar_evento("atualizou propriedade rural")
            flash("Propriedade atualizada com sucesso!", "success")
            return redirect(url_for("perfil"))
    return render_template("editar_propriedade.html", propriedade=propriedade)


# ==========================================================
# PAINEL
# ==========================================================
@app.route("/dashboard")
@login_required
def dashboard():
    lotes = Lote.query.filter_by(usuario_id=current_user.id).order_by(Lote.nome).all()
    manejos = (
        ManejoSanitario.query.join(Lote)
        .filter(Lote.usuario_id == current_user.id)
        .order_by(ManejoSanitario.data_aplicacao.desc()).limit(8).all()
    )
    bloqueados = sum(
        1 for lote in lotes
        if any(m.data_liberacao > date.today() for m in lote.manejos)
    )
    vacinas = Vacina.query.order_by(Vacina.nome).all()
    return render_template(
        "dashboard.html", lotes=lotes, vacinas=vacinas,
        manejos=manejos, bloqueados=bloqueados, hoje=date.today()
    )


# ==========================================================
# LOTES - CRUD
# ==========================================================
@app.route("/lotes", methods=["GET", "POST"])
@login_required
def lotes():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        quantidade = request.form.get("quantidade_cabecas", type=int)
        if not nome or quantidade is None or quantidade < 1:
            flash("Informe o nome do lote e uma quantidade maior que zero.", "danger")
        else:
            lote = Lote(
                usuario_id=current_user.id, nome=nome,
                quantidade_cabecas=quantidade, status="ATIVO"
            )
            db.session.add(lote)
            db.session.commit()
            registrar_evento("cadastrou lote id=%s" % lote.id)
            flash("Lote cadastrado com sucesso!", "success")
            return redirect(url_for("lotes"))
    lista = Lote.query.filter_by(usuario_id=current_user.id).order_by(Lote.nome).all()
    for lote in lista:
        atualizar_status_lote(lote)
    db.session.commit()
    return render_template("lotes.html", lotes=lista)


@app.route("/lotes/<int:lote_id>/editar", methods=["GET", "POST"])
@login_required
def editar_lote(lote_id):
    lote = lote_do_usuario(lote_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        quantidade = request.form.get("quantidade_cabecas", type=int)
        if not nome or quantidade is None or quantidade < 1:
            flash("Confira o nome e a quantidade de cabeças.", "danger")
        else:
            lote.nome = nome
            lote.quantidade_cabecas = quantidade
            db.session.commit()
            registrar_evento("editou lote id=%s" % lote.id)
            flash("Lote atualizado com sucesso!", "success")
            return redirect(url_for("lotes"))
    return render_template("editar_lote.html", lote=lote)


@app.route("/lotes/<int:lote_id>/excluir", methods=["POST"])
@login_required
def excluir_lote(lote_id):
    lote = lote_do_usuario(lote_id)
    if lote.manejos:
        flash("Este lote possui histórico sanitário. Remova ou preserve os registros antes de excluí-lo.", "warning")
    else:
        db.session.delete(lote)
        db.session.commit()
        registrar_evento("excluiu lote id=%s" % lote_id)
        flash("Lote excluído.", "success")
    return redirect(url_for("lotes"))


# ==========================================================
# VACINAS E MEDICAMENTOS - CRUD
# Catálogo compartilhado entre usuários deste protótipo.
# ==========================================================
@app.route("/vacinas", methods=["GET", "POST"])
@login_required
def vacinas():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo = request.form.get("tipo", "Vacina").strip()
        fabricante = request.form.get("fabricante", "").strip()
        carencia = request.form.get("dias_carencia", type=int)
        obrigatoria = request.form.get("obrigatoria") == "on"
        if not nome or carencia is None or carencia < 0 or tipo not in {"Vacina", "Medicamento"}:
            flash("Confira o nome, tipo e dias de carência.", "danger")
        elif Vacina.query.filter(db.func.lower(Vacina.nome) == nome.lower()).first():
            flash("Já existe uma vacina/medicamento com esse nome.", "danger")
        else:
            item = Vacina(
                nome=nome, tipo=tipo, fabricante=fabricante or None,
                dias_carencia=carencia, obrigatoria=obrigatoria
            )
            db.session.add(item)
            db.session.commit()
            registrar_evento("cadastrou vacina/medicamento")
            flash("Vacina/medicamento cadastrado.", "success")
            return redirect(url_for("vacinas"))
    lista = Vacina.query.order_by(Vacina.nome).all()
    return render_template("vacinas.html", vacinas=lista)


@app.route("/vacinas/<int:vacina_id>/editar", methods=["GET", "POST"])
@login_required
def editar_vacina(vacina_id):
    vacina = db.get_or_404(Vacina, vacina_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        tipo = request.form.get("tipo", "Vacina").strip()
        fabricante = request.form.get("fabricante", "").strip()
        carencia = request.form.get("dias_carencia", type=int)
        obrigatoria = request.form.get("obrigatoria") == "on"
        duplicada = Vacina.query.filter(
            db.func.lower(Vacina.nome) == nome.lower(), Vacina.id != vacina.id
        ).first() if nome else None
        if not nome or carencia is None or carencia < 0 or tipo not in {"Vacina", "Medicamento"}:
            flash("Confira os campos informados.", "danger")
        elif duplicada:
            flash("Já existe outro item com esse nome.", "danger")
        else:
            vacina.nome = nome
            vacina.tipo = tipo
            vacina.fabricante = fabricante or None
            vacina.dias_carencia = carencia
            vacina.obrigatoria = obrigatoria
            # Recalcula a data de liberação do histórico deste item quando a carência muda.
            for manejo in vacina.manejos:
                manejo.data_liberacao = manejo.data_aplicacao + timedelta(days=carencia)
                atualizar_status_lote(manejo.lote)
            db.session.commit()
            registrar_evento("editou vacina id=%s" % vacina.id)
            flash("Item atualizado e datas de liberação recalculadas.", "success")
            return redirect(url_for("vacinas"))
    return render_template("editar_vacina.html", vacina=vacina)


@app.route("/vacinas/<int:vacina_id>/excluir", methods=["POST"])
@login_required
def excluir_vacina(vacina_id):
    vacina = db.get_or_404(Vacina, vacina_id)
    if vacina.manejos:
        flash("Este item possui histórico sanitário e não pode ser excluído.", "warning")
    else:
        db.session.delete(vacina)
        db.session.commit()
        registrar_evento("excluiu vacina id=%s" % vacina_id)
        flash("Item excluído.", "success")
    return redirect(url_for("vacinas"))


# ==========================================================
# MANEJO SANITÁRIO - CRUD
# ==========================================================
@app.route("/manejos", methods=["GET", "POST"])
@login_required
def manejos():
    if request.method == "POST":
        lote_id = request.form.get("lote_id", type=int)
        vacina_id = request.form.get("vacina_id", type=int)
        data_texto = request.form.get("data_aplicacao", "")
        observacao = request.form.get("observacao", "").strip()
        lote = Lote.query.filter_by(id=lote_id, usuario_id=current_user.id).first() if lote_id else None
        vacina = db.session.get(Vacina, vacina_id) if vacina_id else None
        try:
            data_aplicacao = date.fromisoformat(data_texto)
        except (ValueError, TypeError):
            data_aplicacao = None

        if not lote or not vacina or not data_aplicacao:
            flash("Selecione um lote, um item e uma data válida.", "danger")
        else:
            manejo = ManejoSanitario(
                lote=lote, vacina=vacina, data_aplicacao=data_aplicacao,
                data_liberacao=data_aplicacao + timedelta(days=vacina.dias_carencia),
                observacao=observacao or None
            )
            db.session.add(manejo)
            db.session.flush()
            atualizar_status_lote(lote)
            db.session.commit()
            registrar_evento("registrou manejo id=%s" % manejo.id)
            flash("Manejo registrado com a data de liberação calculada.", "success")
            return redirect(url_for("manejos"))

    lista_manejos = (
        ManejoSanitario.query.join(Lote).filter(Lote.usuario_id == current_user.id)
        .order_by(ManejoSanitario.data_aplicacao.desc()).all()
    )
    lista_lotes = Lote.query.filter_by(usuario_id=current_user.id).order_by(Lote.nome).all()
    lista_vacinas = Vacina.query.order_by(Vacina.nome).all()
    return render_template(
        "manejos.html", manejos=lista_manejos, lotes=lista_lotes,
        vacinas=lista_vacinas, hoje=date.today()
    )


@app.route("/manejos/<int:manejo_id>/editar", methods=["GET", "POST"])
@login_required
def editar_manejo(manejo_id):
    manejo = manejo_do_usuario(manejo_id)
    lotes_usuario = Lote.query.filter_by(usuario_id=current_user.id).order_by(Lote.nome).all()
    vacinas_cadastradas = Vacina.query.order_by(Vacina.nome).all()
    if request.method == "POST":
        lote_id = request.form.get("lote_id", type=int)
        vacina_id = request.form.get("vacina_id", type=int)
        data_texto = request.form.get("data_aplicacao", "")
        observacao = request.form.get("observacao", "").strip()
        lote = Lote.query.filter_by(id=lote_id, usuario_id=current_user.id).first() if lote_id else None
        vacina = db.session.get(Vacina, vacina_id) if vacina_id else None
        try:
            data_aplicacao = date.fromisoformat(data_texto)
        except (ValueError, TypeError):
            data_aplicacao = None
        if not lote or not vacina or not data_aplicacao:
            flash("Confira o lote, o item e a data informados.", "danger")
        else:
            lote_anterior = manejo.lote
            manejo.lote = lote
            manejo.vacina = vacina
            manejo.data_aplicacao = data_aplicacao
            manejo.data_liberacao = data_aplicacao + timedelta(days=vacina.dias_carencia)
            manejo.observacao = observacao or None
            atualizar_status_lote(lote)
            if lote_anterior.id != lote.id:
                atualizar_status_lote(lote_anterior)
            db.session.commit()
            registrar_evento("editou manejo id=%s" % manejo.id)
            flash("Manejo atualizado com sucesso.", "success")
            return redirect(url_for("manejos"))
    return render_template(
        "editar_manejo.html", manejo=manejo,
        lotes=lotes_usuario, vacinas=vacinas_cadastradas
    )


@app.route("/manejos/<int:manejo_id>/excluir", methods=["POST"])
@login_required
def excluir_manejo(manejo_id):
    manejo = manejo_do_usuario(manejo_id)
    lote = manejo.lote
    db.session.delete(manejo)
    db.session.flush()
    atualizar_status_lote(lote)
    db.session.commit()
    registrar_evento("excluiu manejo id=%s" % manejo_id)
    flash("Registro removido do histórico.", "success")
    return redirect(url_for("manejos"))


# ==========================================================
# API REST DE LOTES: GET, POST, PUT, DELETE
# ==========================================================
@app.route("/api/lotes", methods=["GET", "POST"])
@login_required
def api_lotes():
    if request.method == "GET":
        lista = Lote.query.filter_by(usuario_id=current_user.id).order_by(Lote.id).all()
        return jsonify([
            {"id": lote.id, "nome": lote.nome,
             "quantidade_cabecas": lote.quantidade_cabecas, "status": lote.status}
            for lote in lista
        ])

    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    quantidade = dados.get("quantidade_cabecas")
    if not nome or type(quantidade) is not int or quantidade < 1:
        return jsonify({"erro": "Informe nome e quantidade_cabecas (inteiro maior que zero)."}), 400
    lote = Lote(
        usuario_id=current_user.id, nome=nome,
        quantidade_cabecas=quantidade, status="ATIVO"
    )
    db.session.add(lote)
    db.session.commit()
    registrar_evento("API criou lote id=%s" % lote.id)
    return jsonify({"id": lote.id, "nome": lote.nome,
                    "quantidade_cabecas": lote.quantidade_cabecas, "status": lote.status}), 201


@app.route("/api/lotes/<int:lote_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_lote(lote_id):
    lote = lote_do_usuario(lote_id)
    if request.method == "GET":
        return jsonify({"id": lote.id, "nome": lote.nome,
                        "quantidade_cabecas": lote.quantidade_cabecas, "status": lote.status})
    if request.method == "PUT":
        dados = request.get_json(silent=True) or {}
        nome = str(dados.get("nome", lote.nome)).strip()
        quantidade = dados.get("quantidade_cabecas", lote.quantidade_cabecas)
        if not nome or type(quantidade) is not int or quantidade < 1:
            return jsonify({"erro": "Dados inválidos."}), 400
        lote.nome = nome
        lote.quantidade_cabecas = quantidade
        db.session.commit()
        registrar_evento("API atualizou lote id=%s" % lote.id)
        return jsonify({"id": lote.id, "nome": lote.nome,
                        "quantidade_cabecas": lote.quantidade_cabecas, "status": lote.status})
    if lote.manejos:
        return jsonify({"erro": "Lote possui histórico sanitário e não pode ser excluído."}), 409
    db.session.delete(lote)
    db.session.commit()
    registrar_evento("API excluiu lote id=%s" % lote_id)
    return "", 204


# ==========================================================
# ERROS E INICIALIZAÇÃO
# ==========================================================
@app.errorhandler(403)
def proibido(_):
    return render_template(
        "erro.html", codigo=403,
        mensagem="Você não tem permissão para acessar este recurso."
    ), 403


@app.errorhandler(404)
def nao_encontrado(_):
    return render_template(
        "erro.html", codigo=404,
        mensagem="A página ou registro não foi encontrado."
    ), 404


def inicializar_banco():
    with app.app_context():
        db.create_all()

        if not Usuario.query.filter_by(email="admin@gmail.com").first():
            admin = Usuario(
                nome="Administrador",
                email="admin@gmail.com",
                perfil="admin"
            )

            senha_admin = os.environ.get("ADMIN_INITIAL_PASSWORD")

            if not senha_admin:
                raise RuntimeError(
                    "Configure ADMIN_INITIAL_PASSWORD no arquivo .env"
                )

            admin.definir_senha(senha_admin)
            db.session.add(admin)

        db.session.commit()


if __name__ == "__main__":
    inicializar_banco()
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
