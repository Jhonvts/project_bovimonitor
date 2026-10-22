"""Modelos relacionais do BoviMonitor."""
from datetime import date

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    telefone = db.Column(db.String(20), nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="usuario")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acesso = db.Column(db.DateTime, nullable=True)
    propriedade = db.relationship("Propriedade", back_populates="usuario", uselist=False,
                                   cascade="all, delete-orphan")
    lotes = db.relationship("Lote", back_populates="usuario", cascade="all, delete-orphan",
                            order_by="Lote.nome")
    vacinas = db.relationship("Vacina", back_populates="usuario", cascade="all, delete-orphan")

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Propriedade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
                           unique=True, nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    localizacao = db.Column(db.String(200), nullable=False)
    area = db.Column(db.Float, nullable=False)
    usuario = db.relationship("Usuario", back_populates="propriedade")


class Lote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    quantidade_cabecas = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="ATIVO")
    usuario = db.relationship("Usuario", back_populates="lotes")
    manejos = db.relationship("ManejoSanitario", back_populates="lote",
                              cascade="all, delete-orphan",
                              order_by="ManejoSanitario.data_aplicacao.desc()")


class Vacina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    # NULL identifica item compartilhado administrado pela equipe; preenchido identifica item privado.
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
                           nullable=True, index=True)
    tipo = db.Column(db.String(20), nullable=False, default="Vacina")
    categoria = db.Column(db.String(40), nullable=False, default="Vacina")
    fabricante = db.Column(db.String(100), nullable=True)
    dias_carencia = db.Column(db.Integer, nullable=False, default=0)
    obrigatoria = db.Column(db.Boolean, nullable=False, default=False)
    usuario = db.relationship("Usuario", back_populates="vacinas")
    manejos = db.relationship(
        "ManejoSanitario", back_populates="vacina",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="ManejoSanitario.data_aplicacao.desc()"
    )


class ManejoSanitario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lote.id", ondelete="CASCADE"), nullable=False)
    vacina_id = db.Column(db.Integer, db.ForeignKey("vacina.id", ondelete="CASCADE"), nullable=False)
    data_aplicacao = db.Column(db.Date, nullable=False, default=date.today)
    data_liberacao = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(300), nullable=True)
    lote = db.relationship("Lote", back_populates="manejos")
    vacina = db.relationship("Vacina", back_populates="manejos")
