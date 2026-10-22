-- BoviMonitor - Modelo físico para MariaDB 10.6+
-- Banco vazio: executar antes de objetos_programaveis.sql e usuários.sql.
-- Senhas e usuários de banco são configurados separadamente em usuarios.sql.
CREATE DATABASE IF NOT EXISTS bovimonitor
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bovimonitor;

CREATE TABLE IF NOT EXISTS usuario (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL,
  telefone VARCHAR(20) NULL,
  senha_hash VARCHAR(255) NOT NULL,
  perfil VARCHAR(20) NOT NULL DEFAULT 'usuario',
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  ultimo_acesso DATETIME NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_usuario_email UNIQUE (email)
) ENGINE=InnoDB COMMENT='Contas de produtores e administradores da aplicação';

CREATE TABLE IF NOT EXISTS propriedade (
  id INT NOT NULL AUTO_INCREMENT,
  usuario_id INT NOT NULL,
  nome VARCHAR(120) NOT NULL,
  localizacao VARCHAR(200) NOT NULL,
  area FLOAT NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT uq_propriedade_usuario UNIQUE (usuario_id),
  CONSTRAINT fk_propriedade_usuario FOREIGN KEY (usuario_id)
    REFERENCES usuario (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Uma propriedade rural vinculada a cada conta';

CREATE TABLE IF NOT EXISTS lote (
  id INT NOT NULL AUTO_INCREMENT,
  usuario_id INT NOT NULL,
  nome VARCHAR(100) NOT NULL,
  quantidade_cabecas INT NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'ATIVO',
  PRIMARY KEY (id),
  KEY idx_lote_usuario (usuario_id),
  CONSTRAINT fk_lote_usuario FOREIGN KEY (usuario_id)
    REFERENCES usuario (id) ON DELETE CASCADE,
  CONSTRAINT ck_lote_quantidade CHECK (quantidade_cabecas > 0)
) ENGINE=InnoDB COMMENT='Grupo de animais cadastrado pelo produtor';

CREATE TABLE IF NOT EXISTS vacina (
  id INT NOT NULL AUTO_INCREMENT,
  usuario_id INT NULL,
  nome VARCHAR(100) NOT NULL,
  tipo VARCHAR(20) NOT NULL DEFAULT 'Vacina',
  categoria VARCHAR(40) NOT NULL DEFAULT 'Vacina',
  fabricante VARCHAR(100) NULL,
  dias_carencia INT NOT NULL DEFAULT 0,
  obrigatoria BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (id),
  KEY idx_vacina_usuario (usuario_id),
  KEY idx_vacina_nome (nome),
  CONSTRAINT ck_vacina_carencia CHECK (dias_carencia >= 0),
  CONSTRAINT fk_vacina_usuario FOREIGN KEY (usuario_id)
    REFERENCES usuario (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Itens sanitários compartilhados (usuario_id NULL) ou privados por produtor';

CREATE TABLE IF NOT EXISTS manejo_sanitario (
  id INT NOT NULL AUTO_INCREMENT,
  lote_id INT NOT NULL,
  vacina_id INT NOT NULL,
  data_aplicacao DATE NOT NULL,
  data_liberacao DATE NOT NULL,
  observacao VARCHAR(300) NULL,
  PRIMARY KEY (id),
  KEY idx_manejo_lote_data (lote_id, data_aplicacao),
  KEY idx_manejo_vacina (vacina_id),
  CONSTRAINT fk_manejo_lote FOREIGN KEY (lote_id)
    REFERENCES lote (id) ON DELETE CASCADE,
  CONSTRAINT fk_manejo_vacina FOREIGN KEY (vacina_id) REFERENCES vacina (id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Histórico sanitário com datas de aplicação e liberação';

-- Sem FK de lote intencionalmente: a trilha de auditoria precisa sobreviver à remoção do lote.
CREATE TABLE IF NOT EXISTS auditoria_lotes (
  id BIGINT NOT NULL AUTO_INCREMENT,
  lote_id INT NULL,
  usuario_id INT NULL,
  nome_lote VARCHAR(100) NOT NULL,
  acao VARCHAR(20) NOT NULL,
  data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_auditoria_lotes_data (data_registro)
) ENGINE=InnoDB COMMENT='Cópia dos eventos de criação, atualização e exclusão de lotes';
