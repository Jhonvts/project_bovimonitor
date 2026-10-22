import logging
import math
import os
import re
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, CSRFError

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template,
    request, session, url_for
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from config import configure_app
from extensions import db
from models import Lote, ManejoSanitario, Propriedade, Usuario, Vacina


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================
load_dotenv()

app = Flask(__name__)
configure_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

if os.environ.get("TRUST_PROXY", "0") == "1":
    # Ative somente quando houver exatamente um proxy reverso confiável à frente do Flask.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

csrf = CSRFProtect(app)


@app.after_request
def cabecalhos_de_seguranca(resposta):
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("X-Frame-Options", "DENY")
    resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resposta.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if app.config["SESSION_COOKIE_SECURE"]:
        resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return resposta

os.makedirs(app.instance_path, exist_ok=True)

# Configuração da auditoria em arquivo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(app.instance_path, "bovimonitor.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ],
    force=True
)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Entre na sua conta para acessar esta página."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def carregar_usuario(user_id):
    try:
        return db.session.get(Usuario, int(user_id))
    except (TypeError, ValueError):
        return None


def registrar_evento(mensagem):
    usuario_id = (
        current_user.get_id()
        if current_user.is_authenticated
        else "anonimo"
    )
    ip = request.remote_addr or "desconhecido"

    logging.info(
        "usuario_id=%s ip=%s evento=%s",
        usuario_id,
        ip,
        mensagem
    )


def lote_do_usuario(lote_id):
    """Produtores acessam apenas os próprios lotes; administradores podem gerenciar todos."""
    if current_user.perfil == "admin":
        return db.get_or_404(Lote, lote_id)
    return Lote.query.filter_by(id=lote_id, usuario_id=current_user.id).first_or_404()


def manejo_do_usuario(manejo_id):
    """Produtores acessam apenas manejos dos próprios lotes; admin tem acesso global."""
    if current_user.perfil == "admin":
        return db.get_or_404(ManejoSanitario, manejo_id)
    return (
        ManejoSanitario.query.join(Lote)
        .filter(ManejoSanitario.id == manejo_id, Lote.usuario_id == current_user.id)
        .first_or_404()
    )


def admin_required(view):
    """Restringe operações administrativas a contas com perfil de admin."""
    from functools import wraps

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.perfil != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def validar_texto(valor, maximo, obrigatorio=True):
    valor = (valor or "").strip()
    if (obrigatorio and not valor) or len(valor) > maximo:
        return None
    return valor or None


def email_valido(valor):
    return len(valor) <= 120 and bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", valor))


def obter_categoria(form):
    categoria = (form.get("categoria") or form.get("tipo") or "Vacina").strip()
    permitidas = {"Vacina", "Vermífugo", "Antiparasitário", "Antibiótico",
                  "Anti-inflamatório", "Vitamina/Suplemento", "Outro medicamento",
                  "Medicamento"}
    return categoria if categoria in permitidas else None


def vacina_visivel(vacina):
    """Admin consulta todos os catálogos; produtor vê o compartilhado e o próprio."""
    if current_user.perfil == "admin":
        return True
    return vacina.usuario_id is None or vacina.usuario_id == current_user.id


def pode_gerenciar_vacina(vacina):
    """Admin gerencia qualquer item; produtor somente itens do próprio catálogo."""
    return current_user.perfil == "admin" or vacina.usuario_id == current_user.id


def catalogo_visivel_query():
    if current_user.perfil == "admin":
        return Vacina.query
    return Vacina.query.filter(db.or_(Vacina.usuario_id.is_(None),
                                      Vacina.usuario_id == current_user.id))


def consulta_nome_vacina(nome, usuario_id, excluir_id=None):
    """Evita duplicatas no mesmo catálogo e colisões com o catálogo compartilhado."""
    consulta = Vacina.query.filter(db.func.lower(Vacina.nome) == nome.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Vacina.id != excluir_id)
    if usuario_id is None:
        # O catálogo compartilhado precisa evitar colisões com qualquer catálogo pessoal.
        pass
    else:
        consulta = consulta.filter(db.or_(
            Vacina.usuario_id.is_(None), Vacina.usuario_id == usuario_id
        ))
    return consulta.first()


def vacina_permitida_para_lote(vacina, lote):
    """Itens compartilhados servem a todos; itens pessoais só ao rebanho do titular."""
    return bool(vacina and lote and (
        vacina.usuario_id is None or vacina.usuario_id == lote.usuario_id
    ))


def atualizar_status_lote(lote):
    # Consulta o banco para também considerar inclusões/edições/exclusões ainda na sessão.
    em_carencia = ManejoSanitario.query.filter_by(lote_id=lote.id).filter(
        ManejoSanitario.data_liberacao > date.today()
    ).count() > 0
    lote.status = "BLOQUEADO" if em_carencia else "ATIVO"


# ==========================================================
# LOGIN E CADASTRO DE CONTA
# ==========================================================
@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))


@app.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefone = request.form.get("telefone", "").strip()
        senha = request.form.get("senha", "")

        if not validar_texto(nome, 100) or not email_valido(email) or len(senha) < 10 or len(telefone) > 20:
            flash("Preencha nome e e-mail. A senha deve ter pelo menos 10 caracteres.", "danger")
        elif Usuario.query.filter_by(email=email).first():
            flash("Já existe uma conta com esse e-mail.", "danger")
        else:
            usuario = Usuario(nome=nome, email=email, telefone=telefone or None)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            db.session.commit()
            login_user(usuario)
            session.permanent = True
            registrar_evento("criou uma conta")
            flash("Conta criada com sucesso! Complete seu perfil.", "success")
            return redirect(url_for("perfil"))

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.ativo and usuario.verificar_senha(senha):
            login_user(usuario)
            session.permanent = True
            usuario.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            registrar_evento("realizou login")
            return redirect(url_for("dashboard"))

        logging.warning("usuario_id=%s ip=%s evento=login_falhou",
                        usuario.id if usuario else "nao_encontrado",
                        request.remote_addr or "desconhecido")
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
        if not validar_texto(nome, 100) or len(telefone) > 20:
            flash("Informe um nome de até 100 caracteres e um telefone de até 20 caracteres.", "danger")
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
        senha = request.form.get("senha", "")
        if not usuario or not usuario.verificar_senha(senha):
            flash("A senha informada não confere. Nenhuma alteração foi feita.", "danger")
            return render_template("excluir_perfil.html"), 400

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
        if not validar_texto(nome, 120) or not validar_texto(localizacao, 200) or not math.isfinite(area) or not 0 < area <= 1000000:
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
        if not validar_texto(nome, 120) or not validar_texto(localizacao, 200) or not math.isfinite(area) or not 0 < area <= 1000000:
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


@app.route("/propriedade/excluir", methods=["POST"])
@login_required
def excluir_propriedade():
    propriedade = Propriedade.query.filter_by(usuario_id=current_user.id).first_or_404()
    db.session.delete(propriedade)
    db.session.commit()
    registrar_evento("excluiu propriedade rural")
    flash("Propriedade removida. Os lotes e manejos foram preservados.", "success")
    return redirect(url_for("perfil"))


# ==========================================================
# PAINEL
# ==========================================================
@app.route("/dashboard")
@login_required
def dashboard():
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lotes = consulta_lotes.order_by(Lote.nome).all()
    consulta_manejos = ManejoSanitario.query if current_user.perfil == "admin" else ManejoSanitario.query.join(Lote).filter(Lote.usuario_id == current_user.id)
    manejos = consulta_manejos.order_by(ManejoSanitario.data_aplicacao.desc()).limit(8).all()
    bloqueados = sum(
        1 for lote in lotes
        if any(m.data_liberacao > date.today() for m in lote.manejos)
    )
    liberados = len(lotes) - bloqueados
    percentual_bloqueado = round((bloqueados / len(lotes)) * 100) if lotes else 0
    vacinas = catalogo_visivel_query().order_by(Vacina.nome).all()
    cabecas = sum(l.quantidade_cabecas for l in lotes)
    consulta_liberacoes = ManejoSanitario.query
    if current_user.perfil != "admin":
        consulta_liberacoes = consulta_liberacoes.join(Lote).filter(Lote.usuario_id == current_user.id)
    proximas_liberacoes = (consulta_liberacoes
                           .filter(ManejoSanitario.data_liberacao >= date.today())
                           .order_by(ManejoSanitario.data_liberacao).limit(5).all())
    return render_template(
        "dashboard.html", lotes=lotes, vacinas=vacinas,
        manejos=manejos, bloqueados=bloqueados, hoje=date.today(),
        cabecas=cabecas, proximas_liberacoes=proximas_liberacoes,
        liberados=liberados, percentual_bloqueado=percentual_bloqueado
    )


# ==========================================================
# ÁREA ADMINISTRATIVA - suporte em modo somente leitura
# ==========================================================
@app.route("/admin")
@admin_required
def admin_painel():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template(
        "admin_painel.html", total_usuarios=len(usuarios),
        usuarios_ativos=sum(1 for u in usuarios if u.ativo),
        total_lotes=Lote.query.count(), total_manejos=ManejoSanitario.query.count(),
        total_itens=Vacina.query.count()
    )


@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    termo = request.args.get("q", "").strip()[:120]
    consulta = Usuario.query
    if termo:
        busca = f"%{termo}%"
        consulta = consulta.filter(db.or_(Usuario.nome.ilike(busca), Usuario.email.ilike(busca)))
    usuarios = consulta.order_by(Usuario.perfil.desc(), Usuario.nome).all()
    return render_template("admin_usuarios.html", usuarios=usuarios, termo=termo)


@app.route("/admin/usuarios/<int:usuario_id>")
@admin_required
def admin_usuario(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    lotes = Lote.query.filter_by(usuario_id=usuario.id).order_by(Lote.nome).all()
    manejos = (ManejoSanitario.query.join(Lote)
               .filter(Lote.usuario_id == usuario.id)
               .order_by(ManejoSanitario.data_aplicacao.desc()).limit(50).all())
    propriedade = Propriedade.query.filter_by(usuario_id=usuario.id).first()
    return render_template("admin_usuario.html", usuario=usuario, lotes=lotes,
                           manejos=manejos, propriedade=propriedade, hoje=date.today())


@app.route("/admin/usuarios/<int:usuario_id>/status", methods=["POST"])
@admin_required
def admin_alterar_status_usuario(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if usuario.perfil == "admin" or usuario.id == current_user.id:
        abort(403)
    usuario.ativo = not usuario.ativo
    db.session.commit()
    registrar_evento("alterou status da conta usuario_id=%s ativo=%s" % (usuario.id, usuario.ativo))
    flash("Conta reativada." if usuario.ativo else "Conta desativada.", "success")
    return redirect(url_for("admin_usuarios"))


@app.route("/admin/auditoria")
@admin_required
def admin_auditoria():
    caminho = os.path.join(app.instance_path, "bovimonitor.log")
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            eventos = arquivo.readlines()[-150:][::-1]
    except OSError:
        eventos = []
    return render_template("admin_auditoria.html", eventos=eventos)


# ==========================================================
# LOTES - CRUD
# ==========================================================
@app.route("/lotes", methods=["GET", "POST"])
@login_required
def lotes():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        quantidade = request.form.get("quantidade_cabecas", type=int)
        if not validar_texto(nome, 100) or quantidade is None or not 1 <= quantidade <= 100000:
            flash("Informe o nome do lote e uma quantidade maior que zero.", "danger")
        else:
            dono_id = request.form.get("usuario_id", type=int) if current_user.perfil == "admin" else current_user.id
            dono = db.session.get(Usuario, dono_id) if dono_id else None
            if not dono or dono.perfil != "usuario":
                flash("Selecione um produtor válido para o lote.", "danger")
                return redirect(url_for("lotes"))
            lote = Lote(
                usuario_id=dono.id, nome=nome,
                quantidade_cabecas=quantidade, status="ATIVO"
            )
            db.session.add(lote)
            db.session.commit()
            registrar_evento("cadastrou lote id=%s" % lote.id)
            flash("Lote cadastrado com sucesso!", "success")
            return redirect(url_for("lotes"))
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lista = consulta_lotes.order_by(Lote.nome).all()
    usuarios = Usuario.query.filter_by(perfil="usuario", ativo=True).order_by(Usuario.nome).all() if current_user.perfil == "admin" else []
    status_lotes = {
        lote.id: "BLOQUEADO" if any(m.data_liberacao > date.today() for m in lote.manejos) else "ATIVO"
        for lote in lista
    }
    return render_template("lotes.html", lotes=lista, status_lotes=status_lotes, usuarios=usuarios)


@app.route("/lotes/<int:lote_id>/editar", methods=["GET", "POST"])
@login_required
def editar_lote(lote_id):
    lote = lote_do_usuario(lote_id)
    usuarios = Usuario.query.filter_by(perfil="usuario", ativo=True).order_by(Usuario.nome).all() if current_user.perfil == "admin" else []
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        quantidade = request.form.get("quantidade_cabecas", type=int)
        dono_id = request.form.get("usuario_id", type=int) if current_user.perfil == "admin" else lote.usuario_id
        dono = db.session.get(Usuario, dono_id) if dono_id else None
        if not validar_texto(nome, 100) or quantidade is None or not 1 <= quantidade <= 100000 or not dono or dono.perfil != "usuario":
            flash("Confira o nome, a quantidade e o produtor do lote.", "danger")
        else:
            lote.nome = nome
            lote.quantidade_cabecas = quantidade
            lote.usuario_id = dono.id
            db.session.commit()
            registrar_evento("editou lote id=%s" % lote.id)
            flash("Lote atualizado com sucesso!", "success")
            return redirect(url_for("lotes"))
    return render_template("editar_lote.html", lote=lote, usuarios=usuarios)


@app.route("/lotes/<int:lote_id>/excluir", methods=["POST"])
@login_required
def excluir_lote(lote_id):
    lote = lote_do_usuario(lote_id)
    quantidade_manejos = len(lote.manejos)
    db.session.delete(lote)
    db.session.commit()
    registrar_evento("excluiu lote id=%s manejos_removidos=%s" % (lote_id, quantidade_manejos))
    flash("Lote e seus manejos vinculados foram excluídos.", "success")
    return redirect(url_for("lotes"))


# ==========================================================
# CATÁLOGO SANITÁRIO - itens pessoais e catálogo compartilhado do administrador
# ==========================================================
@app.route("/vacinas", methods=["GET", "POST"])
@login_required
def vacinas():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = obter_categoria(request.form)
        fabricante = request.form.get("fabricante", "").strip()
        carencia = request.form.get("dias_carencia", type=int)
        obrigatoria = request.form.get("obrigatoria") == "on"
        if not validar_texto(nome, 100) or len(fabricante) > 100 or carencia is None or carencia < 0 or carencia > 3650 or not categoria:
            flash("Confira o nome, tipo e dias de carência.", "danger")
        elif consulta_nome_vacina(nome, None if current_user.perfil == "admin" else current_user.id):
            flash("Esse nome já está sendo usado no seu catálogo ou no catálogo compartilhado.", "danger")
        else:
            item = Vacina(
                nome=nome, tipo="Vacina" if categoria == "Vacina" else "Medicamento",
                usuario_id=None if current_user.perfil == "admin" else current_user.id,
                categoria=categoria, fabricante=fabricante or None,
                dias_carencia=carencia, obrigatoria=obrigatoria
            )
            db.session.add(item)
            db.session.commit()
            registrar_evento("cadastrou item sanitario id=%s" % item.id)
            flash("Item sanitário cadastrado no seu catálogo." if current_user.perfil != "admin"
                  else "Item sanitário adicionado ao catálogo compartilhado.", "success")
            return redirect(url_for("vacinas"))
    lista = catalogo_visivel_query().order_by(Vacina.nome).all()
    return render_template("vacinas.html", vacinas=lista)


@app.route("/vacinas/<int:vacina_id>/editar", methods=["GET", "POST"])
@login_required
def editar_vacina(vacina_id):
    vacina = db.get_or_404(Vacina, vacina_id)
    if not vacina_visivel(vacina) or not pode_gerenciar_vacina(vacina):
        abort(403)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = obter_categoria(request.form)
        fabricante = request.form.get("fabricante", "").strip()
        carencia = request.form.get("dias_carencia", type=int)
        obrigatoria = request.form.get("obrigatoria") == "on"
        duplicada = consulta_nome_vacina(nome, vacina.usuario_id, excluir_id=vacina.id) if nome else None
        if not validar_texto(nome, 100) or len(fabricante) > 100 or carencia is None or carencia < 0 or carencia > 3650 or not categoria:
            flash("Confira os campos informados.", "danger")
        elif duplicada:
            flash("Já existe outro item com esse nome.", "danger")
        else:
            vacina.nome = nome
            vacina.tipo = "Vacina" if categoria == "Vacina" else "Medicamento"
            vacina.categoria = categoria
            vacina.fabricante = fabricante or None
            vacina.dias_carencia = carencia
            vacina.obrigatoria = obrigatoria
            db.session.commit()
            registrar_evento("editou vacina id=%s" % vacina.id)
            flash("Item atualizado. A carência nova vale para os próximos manejos.", "success")
            return redirect(url_for("vacinas"))
    return render_template("editar_vacina.html", vacina=vacina)


@app.route("/vacinas/<int:vacina_id>/excluir", methods=["POST"])
@login_required
def excluir_vacina(vacina_id):
    vacina = db.get_or_404(Vacina, vacina_id)
    if not vacina_visivel(vacina) or not pode_gerenciar_vacina(vacina):
        abort(403)
    lotes_afetados = {manejo.lote for manejo in vacina.manejos}
    quantidade_manejos = len(vacina.manejos)
    db.session.delete(vacina)
    db.session.flush()
    for lote in lotes_afetados:
        atualizar_status_lote(lote)
    db.session.commit()
    registrar_evento("excluiu vacina id=%s manejos_removidos=%s" % (vacina_id, quantidade_manejos))
    flash("Item removido. Os manejos vinculados a esse item também foram excluídos.", "success")
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
        lote_consulta = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
        lote = lote_consulta.filter_by(id=lote_id).first() if lote_id else None
        vacina = catalogo_visivel_query().filter_by(id=vacina_id).first() if vacina_id else None
        try:
            data_aplicacao = date.fromisoformat(data_texto)
        except (ValueError, TypeError):
            data_aplicacao = None

        if not lote or not vacina or not vacina_permitida_para_lote(vacina, lote) or not data_aplicacao or data_aplicacao > date.today() or data_aplicacao < date(1900, 1, 1) or len(observacao) > 300:
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

    consulta_manejos = ManejoSanitario.query if current_user.perfil == "admin" else ManejoSanitario.query.join(Lote).filter(Lote.usuario_id == current_user.id)
    lista_manejos = consulta_manejos.order_by(ManejoSanitario.data_aplicacao.desc()).all()
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lista_lotes = consulta_lotes.order_by(Lote.nome).all()
    lista_vacinas = catalogo_visivel_query().order_by(Vacina.nome).all()
    return render_template(
        "manejos.html", manejos=lista_manejos, lotes=lista_lotes,
        vacinas=lista_vacinas, hoje=date.today()
    )


@app.route("/manejos/<int:manejo_id>/editar", methods=["GET", "POST"])
@login_required
def editar_manejo(manejo_id):
    manejo = manejo_do_usuario(manejo_id)
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lotes_usuario = consulta_lotes.order_by(Lote.nome).all()
    vacinas_cadastradas = catalogo_visivel_query().order_by(Vacina.nome).all()
    if request.method == "POST":
        lote_id = request.form.get("lote_id", type=int)
        vacina_id = request.form.get("vacina_id", type=int)
        data_texto = request.form.get("data_aplicacao", "")
        observacao = request.form.get("observacao", "").strip()
        lote_consulta = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
        lote = lote_consulta.filter_by(id=lote_id).first() if lote_id else None
        vacina = catalogo_visivel_query().filter_by(id=vacina_id).first() if vacina_id else None
        try:
            data_aplicacao = date.fromisoformat(data_texto)
        except (ValueError, TypeError):
            data_aplicacao = None
        if not lote or not vacina or not vacina_permitida_para_lote(vacina, lote) or not data_aplicacao or data_aplicacao > date.today() or data_aplicacao < date(1900, 1, 1) or len(observacao) > 300:
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
        lotes=lotes_usuario, vacinas=vacinas_cadastradas, hoje=date.today()
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
# API REST - CRUD dos recursos principais
# ==========================================================
def json_item_sanitario(item):
    return {"id": item.id, "nome": item.nome, "categoria": item.categoria or item.tipo,
            "fabricante": item.fabricante, "dias_carencia": item.dias_carencia,
            "obrigatoria": item.obrigatoria}


@app.route("/api/vacinas", methods=["GET", "POST"])
@login_required
def api_vacinas():
    if request.method == "GET":
        return jsonify([json_item_sanitario(v) for v in catalogo_visivel_query().order_by(Vacina.nome).all()])
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    categoria = str(dados.get("categoria", "Vacina")).strip()
    carencia = dados.get("dias_carencia", 0)
    permitido = obter_categoria({"categoria": categoria})
    if not validar_texto(nome, 100) or not permitido or type(carencia) is not int or not 0 <= carencia <= 3650:
        return jsonify({"erro": "Dados inválidos: informe nome, categoria e carência de 0 a 3650 dias."}), 400
    dono_id = None if current_user.perfil == "admin" else current_user.id
    if consulta_nome_vacina(nome, dono_id):
        return jsonify({"erro": "Já existe um item com esse nome no catálogo ou no catálogo compartilhado."}), 409
    item = Vacina(nome=nome, categoria=permitido,
                  usuario_id=None if current_user.perfil == "admin" else current_user.id,
                  tipo="Vacina" if permitido == "Vacina" else "Medicamento",
                  fabricante=str(dados.get("fabricante", "")).strip() or None,
                  dias_carencia=carencia, obrigatoria=bool(dados.get("obrigatoria", False)))
    if item.fabricante and len(item.fabricante) > 100:
        return jsonify({"erro": "Fabricante deve ter no máximo 100 caracteres."}), 400
    db.session.add(item)
    db.session.commit()
    registrar_evento("API cadastrou item sanitario id=%s" % item.id)
    return jsonify(json_item_sanitario(item)), 201


@app.route("/api/vacinas/<int:vacina_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_vacina(vacina_id):
    item = db.get_or_404(Vacina, vacina_id)
    if not vacina_visivel(item):
        abort(404)
    if request.method == "GET":
        return jsonify(json_item_sanitario(item))
    if not pode_gerenciar_vacina(item):
        abort(403)
    if request.method == "DELETE":
        lotes_afetados = {manejo.lote for manejo in item.manejos}
        quantidade_manejos = len(item.manejos)
        db.session.delete(item)
        db.session.flush()
        for lote in lotes_afetados:
            atualizar_status_lote(lote)
        db.session.commit()
        registrar_evento("API excluiu item sanitario id=%s manejos_removidos=%s" % (vacina_id, quantidade_manejos))
        return "", 204
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", item.nome)).strip()
    categoria = obter_categoria({"categoria": dados.get("categoria", item.categoria or item.tipo)})
    carencia = dados.get("dias_carencia", item.dias_carencia)
    if not validar_texto(nome, 100) or not categoria or type(carencia) is not int or not 0 <= carencia <= 3650:
        return jsonify({"erro": "Dados inválidos."}), 400
    duplicado = consulta_nome_vacina(nome, item.usuario_id, excluir_id=item.id)
    if duplicado:
        return jsonify({"erro": "Já existe um item com esse nome."}), 409
    fabricante = str(dados.get("fabricante", item.fabricante or "")).strip()
    if len(fabricante) > 100:
        return jsonify({"erro": "Fabricante deve ter no máximo 100 caracteres."}), 400
    item.nome, item.categoria = nome, categoria
    item.tipo = "Vacina" if categoria == "Vacina" else "Medicamento"
    item.fabricante = fabricante or None
    item.dias_carencia = carencia
    item.obrigatoria = bool(dados.get("obrigatoria", item.obrigatoria))
    db.session.commit()
    registrar_evento("API atualizou item sanitario id=%s" % item.id)
    return jsonify(json_item_sanitario(item))


def json_manejo(m):
    return {"id": m.id, "lote_id": m.lote_id, "lote": m.lote.nome,
            "vacina_id": m.vacina_id, "item": m.vacina.nome,
            "data_aplicacao": m.data_aplicacao.isoformat(),
            "data_liberacao": m.data_liberacao.isoformat(), "observacao": m.observacao}


@app.route("/api/manejos", methods=["GET", "POST"])
@login_required
def api_manejos():
    if request.method == "GET":
        consulta = ManejoSanitario.query if current_user.perfil == "admin" else ManejoSanitario.query.join(Lote).filter(Lote.usuario_id == current_user.id)
        registros = consulta.order_by(ManejoSanitario.data_aplicacao.desc()).all()
        return jsonify([json_manejo(m) for m in registros])
    dados = request.get_json(silent=True) or {}
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lote = consulta_lotes.filter_by(id=dados.get("lote_id")).first()
    item = catalogo_visivel_query().filter_by(id=dados.get("vacina_id")).first()
    try:
        aplicado = date.fromisoformat(str(dados.get("data_aplicacao", "")))
    except ValueError:
        aplicado = None
    observacao = str(dados.get("observacao", "")).strip()
    if not lote or not item or not vacina_permitida_para_lote(item, lote) or not aplicado or aplicado > date.today() or aplicado < date(1900, 1, 1) or len(observacao) > 300:
        return jsonify({"erro": "Lote, item, data válida e observação de até 300 caracteres são obrigatórios."}), 400
    m = ManejoSanitario(lote=lote, vacina=item, data_aplicacao=aplicado,
                        data_liberacao=aplicado + timedelta(days=item.dias_carencia),
                        observacao=observacao or None)
    db.session.add(m)
    db.session.commit()
    atualizar_status_lote(lote)
    db.session.commit()
    registrar_evento("API registrou manejo id=%s" % m.id)
    return jsonify(json_manejo(m)), 201


@app.route("/api/manejos/<int:manejo_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_manejo(manejo_id):
    m = manejo_do_usuario(manejo_id)
    if request.method == "GET":
        return jsonify(json_manejo(m))
    lote_anterior = m.lote
    if request.method == "DELETE":
        db.session.delete(m)
        db.session.flush()
        atualizar_status_lote(lote_anterior)
        db.session.commit()
        registrar_evento("API removeu manejo id=%s" % manejo_id)
        return "", 204
    dados = request.get_json(silent=True) or {}
    consulta_lotes = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
    lote = consulta_lotes.filter_by(id=dados.get("lote_id", m.lote_id)).first()
    item = catalogo_visivel_query().filter_by(
        id=dados.get("vacina_id", m.vacina_id)
    ).first()
    try:
        aplicado = date.fromisoformat(str(dados.get("data_aplicacao", m.data_aplicacao.isoformat())))
    except ValueError:
        aplicado = None
    observacao = str(dados.get("observacao", m.observacao or "")).strip()
    if not lote or not item or not vacina_permitida_para_lote(item, lote) or not aplicado or aplicado > date.today() or aplicado < date(1900, 1, 1) or len(observacao) > 300:
        return jsonify({"erro": "Dados inválidos."}), 400
    m.lote, m.vacina, m.data_aplicacao = lote, item, aplicado
    m.data_liberacao = aplicado + timedelta(days=item.dias_carencia)
    m.observacao = observacao or None
    atualizar_status_lote(lote)
    if lote.id != lote_anterior.id:
        atualizar_status_lote(lote_anterior)
    db.session.commit()
    registrar_evento("API atualizou manejo id=%s" % m.id)
    return jsonify(json_manejo(m))


def json_propriedade(p):
    return {"id": p.id, "nome": p.nome, "localizacao": p.localizacao, "area": p.area}


@app.route("/api/propriedade", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_propriedade():
    p = Propriedade.query.filter_by(usuario_id=current_user.id).first()
    if request.method == "GET":
        return jsonify(json_propriedade(p) if p else {})
    if request.method == "DELETE":
        if p:
            db.session.delete(p)
            db.session.commit()
        registrar_evento("API excluiu propriedade rural")
        return "", 204
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", p.nome if p else "")).strip()
    localizacao = str(dados.get("localizacao", p.localizacao if p else "")).strip()
    try:
        area = float(str(dados.get("area", p.area if p else "")).replace(",", "."))
    except (ValueError, TypeError):
        area = 0
    if not validar_texto(nome, 120) or not validar_texto(localizacao, 200) or not math.isfinite(area) or not 0 < area <= 1000000:
        return jsonify({"erro": "Informe nome, localização e área entre 0 e 1.000.000 hectares."}), 400
    if not p:
        p = Propriedade(usuario_id=current_user.id, nome=nome, localizacao=localizacao, area=area)
        db.session.add(p)
        status = 201
    else:
        p.nome, p.localizacao, p.area = nome, localizacao, area
        status = 200
    db.session.commit()
    registrar_evento("API salvou propriedade rural")
    return jsonify(json_propriedade(p)), status


@app.route("/api/lotes", methods=["GET", "POST"])
@login_required
def api_lotes():
    if request.method == "GET":
        consulta = Lote.query if current_user.perfil == "admin" else Lote.query.filter_by(usuario_id=current_user.id)
        lista = consulta.order_by(Lote.id).all()
        return jsonify([
            {"id": lote.id, "nome": lote.nome,
             "quantidade_cabecas": lote.quantidade_cabecas,
             "status": "BLOQUEADO" if any(m.data_liberacao > date.today() for m in lote.manejos) else "ATIVO"}
            for lote in lista
        ])

    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    quantidade = dados.get("quantidade_cabecas")
    if not validar_texto(nome, 100) or type(quantidade) is not int or not 1 <= quantidade <= 100000:
        return jsonify({"erro": "Informe nome e quantidade_cabecas (inteiro maior que zero)."}), 400
    dono_id = dados.get("usuario_id", current_user.id) if current_user.perfil == "admin" else current_user.id
    dono = db.session.get(Usuario, dono_id) if type(dono_id) is int else None
    if not dono or dono.perfil != "usuario":
        return jsonify({"erro": "Selecione um produtor válido para o lote."}), 400
    lote = Lote(
        usuario_id=dono.id, nome=nome,
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
                        "quantidade_cabecas": lote.quantidade_cabecas,
                        "status": "BLOQUEADO" if any(m.data_liberacao > date.today() for m in lote.manejos) else "ATIVO"})
    if request.method == "PUT":
        dados = request.get_json(silent=True) or {}
        nome = str(dados.get("nome", lote.nome)).strip()
        quantidade = dados.get("quantidade_cabecas", lote.quantidade_cabecas)
        if not validar_texto(nome, 100) or type(quantidade) is not int or not 1 <= quantidade <= 100000:
            return jsonify({"erro": "Dados inválidos."}), 400
        lote.nome = nome
        lote.quantidade_cabecas = quantidade
        db.session.commit()
        registrar_evento("API atualizou lote id=%s" % lote.id)
        return jsonify({"id": lote.id, "nome": lote.nome,
                        "quantidade_cabecas": lote.quantidade_cabecas,
                        "status": "BLOQUEADO" if any(m.data_liberacao > date.today() for m in lote.manejos) else "ATIVO"})
    if lote.manejos:
        manejos_removidos = len(lote.manejos)
    else:
        manejos_removidos = 0
    db.session.delete(lote)
    db.session.commit()
    registrar_evento("API excluiu lote id=%s manejos_removidos=%s" % (lote_id, manejos_removidos))
    return "", 204


# ==========================================================
# ERROS E INICIALIZAÇÃO
# ==========================================================
@app.errorhandler(404)
def nao_encontrado(_):
    return render_template(
        "erro.html", codigo=404,
        mensagem="A página ou registro não foi encontrado."
    ), 404


@app.errorhandler(403)
def proibido(_):
    return render_template("erro.html", codigo=403,
                           mensagem="Você não tem permissão para acessar este recurso."), 403


@app.errorhandler(CSRFError)
def csrf_invalido(_):
    return render_template("erro.html", codigo=400,
                           mensagem="O formulário expirou ou não pôde ser validado. Atualize a página e tente novamente."), 400


@app.errorhandler(429)
def muitas_tentativas(_):
    return render_template("erro.html", codigo=429,
                           mensagem="Muitas tentativas em pouco tempo. Aguarde um minuto antes de tentar novamente."), 429


@app.errorhandler(500)
def erro_interno(_):
    db.session.rollback()
    return render_template("erro.html", codigo=500,
                           mensagem="Ocorreu um erro inesperado. Tente novamente e avise o administrador se persistir."), 500





def migrar_catalogo_por_usuario():
    """Remove a unicidade global antiga do nome, preservando todos os registros."""
    if db.engine.dialect.name == "sqlite":
        conexao = db.engine.raw_connection()
        try:
            cursor = conexao.cursor()
            indices = cursor.execute("PRAGMA index_list('vacina')").fetchall()
            possui_unicidade_global = False
            for indice in indices:
                # PRAGMA index_list: seq, name, unique, origin, partial
                if len(indice) > 2 and indice[2]:
                    colunas = [linha[2] for linha in cursor.execute(
                        "PRAGMA index_info('%s')" % str(indice[1]).replace("'", "''")
                    ).fetchall()]
                    if colunas == ["nome"]:
                        possui_unicidade_global = True
                        break
            if possui_unicidade_global:
                cursor.execute("PRAGMA foreign_keys=OFF")
                cursor.execute("BEGIN IMMEDIATE")
                cursor.execute("""
                    CREATE TABLE vacina_nova (
                        id INTEGER NOT NULL PRIMARY KEY,
                        nome VARCHAR(100) NOT NULL,
                        usuario_id INTEGER NULL REFERENCES usuario(id) ON DELETE CASCADE,
                        tipo VARCHAR(20) NOT NULL DEFAULT 'Vacina',
                        categoria VARCHAR(40) NOT NULL DEFAULT 'Vacina',
                        fabricante VARCHAR(100) NULL,
                        dias_carencia INTEGER NOT NULL DEFAULT 0,
                        obrigatoria BOOLEAN NOT NULL DEFAULT 0
                    )
                """)
                cursor.execute("""
                    INSERT INTO vacina_nova
                    (id, nome, usuario_id, tipo, categoria, fabricante, dias_carencia, obrigatoria)
                    SELECT id, nome, usuario_id, tipo, categoria, fabricante, dias_carencia, obrigatoria
                    FROM vacina
                """)
                cursor.execute("DROP TABLE vacina")
                cursor.execute("ALTER TABLE vacina_nova RENAME TO vacina")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_vacina_usuario_id ON vacina (usuario_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_vacina_nome ON vacina (nome)")
                conexao.commit()
                cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()
    elif db.engine.dialect.name in {"mysql", "mariadb"}:
        for restricao in db.inspect(db.engine).get_unique_constraints("vacina"):
            if restricao.get("column_names") == ["nome"] and restricao.get("name"):
                nome_indice = restricao["name"]
                if re.fullmatch(r"[A-Za-z0-9_]+", nome_indice):
                    db.session.execute(db.text(
                        f"ALTER TABLE vacina DROP INDEX `{nome_indice}`"
                    ))
                    db.session.execute(db.text(
                        "CREATE INDEX idx_vacina_nome ON vacina (nome)"
                    ))
                    break


def inicializar_banco():
    with app.app_context():
        db.create_all()

        # Migração simples e compatível com SQLite/MariaDB para instalações anteriores.
        inspetor = db.inspect(db.engine)
        colunas_usuario = {c["name"] for c in inspetor.get_columns("usuario")}
        colunas_vacina = {c["name"] for c in inspetor.get_columns("vacina")}
        if "usuario_id" not in colunas_vacina:
            if db.engine.dialect.name == "sqlite":
                db.session.execute(db.text(
                    "ALTER TABLE vacina ADD COLUMN usuario_id INTEGER NULL "
                    "REFERENCES usuario(id) ON DELETE CASCADE"
                ))
            else:
                db.session.execute(db.text("ALTER TABLE vacina ADD COLUMN usuario_id INT NULL"))
                db.session.execute(db.text(
                    "ALTER TABLE vacina ADD CONSTRAINT fk_vacina_usuario "
                    "FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE"
                ))
        if "ativo" not in colunas_usuario:
            db.session.execute(db.text("ALTER TABLE usuario ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT 1"))
        if "ultimo_acesso" not in colunas_usuario:
            db.session.execute(db.text("ALTER TABLE usuario ADD COLUMN ultimo_acesso DATETIME NULL"))
        if "categoria" not in colunas_vacina:
            db.session.execute(db.text("ALTER TABLE vacina ADD COLUMN categoria VARCHAR(40) NOT NULL DEFAULT 'Vacina'"))
            db.session.execute(db.text("UPDATE vacina SET categoria = 'Medicamento' WHERE tipo = 'Medicamento'"))
        indices_vacina = {i["name"] for i in db.inspect(db.engine).get_indexes("vacina")}
        if "ix_vacina_usuario_id" not in indices_vacina:
            db.session.execute(db.text(
                "CREATE INDEX ix_vacina_usuario_id ON vacina (usuario_id)"
            ))
        db.session.commit()
        migrar_catalogo_por_usuario()

        admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        senha_admin = os.environ.get("ADMIN_INITIAL_PASSWORD")

        if admin_email and not Usuario.query.filter_by(email=admin_email).first():
            if not senha_admin:
                raise RuntimeError("Configure ADMIN_INITIAL_PASSWORD para criar o administrador inicial.")

            admin = Usuario(
                nome="Administrador",
                email=admin_email,
                perfil="admin"
            )
            admin.definir_senha(senha_admin)
            db.session.add(admin)

        db.session.commit()


_banco_inicializado = False


@app.before_request
def preparar_banco_no_deploy():
    global _banco_inicializado
    if not _banco_inicializado:
        inicializar_banco()
        _banco_inicializado = True
    if current_user.is_authenticated and not current_user.ativo:
        logout_user()
        flash("Esta conta foi desativada. Entre em contato com o administrador.", "danger")
        return redirect(url_for("login"))


# Cria o esquema e a conta administrativa também quando WSGI importa `app`.
inicializar_banco()
_banco_inicializado = True


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
