CREATE DATABASE IF NOT EXISTS bovimonitor;

USE bovimonitor;


-- =========================================
-- TABELA DE LOTES
-- =========================================

CREATE TABLE lotes (
    id INT AUTO_INCREMENT PRIMARY KEY,

    nome VARCHAR(100) NOT NULL,

    quantidade_cabecas INT NOT NULL,

    status ENUM('ATIVO', 'BLOQUEADO') DEFAULT 'ATIVO',

    data_cadastro DATE DEFAULT (CURRENT_DATE),

    CONSTRAINT chk_quantidade
        CHECK (quantidade_cabecas >= 0)
);


-- =========================================
-- TABELA DE VACINAS E MEDICAMENTOS
-- =========================================

CREATE TABLE vacinas (
    id INT AUTO_INCREMENT PRIMARY KEY,

    nome VARCHAR(100) NOT NULL,

    tipo ENUM('Vacina', 'Medicamento') NOT NULL,

    dias_carencia INT NOT NULL DEFAULT 0,

    obrigatoria BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT chk_carencia
        CHECK (dias_carencia >= 0)
);


-- =========================================
-- TABELA DE MANEJOS SANITÁRIOS
-- =========================================

CREATE TABLE manejos_sanitarios (
    id INT AUTO_INCREMENT PRIMARY KEY,

    lote_id INT NOT NULL,

    vacina_id INT NOT NULL,

    data_aplicacao DATE NOT NULL,

    data_liberacao DATE NOT NULL,

    observacao TEXT,

    FOREIGN KEY (lote_id)
        REFERENCES lotes(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    FOREIGN KEY (vacina_id)
        REFERENCES vacinas(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);


-- =========================================
-- CONSULTA DOS MANEJOS
-- Mostra lote, vacina e data de liberação
-- =========================================

SELECT
    m.id,
    l.nome AS lote,
    v.nome AS vacina,
    v.tipo,
    m.data_aplicacao,
    v.dias_carencia,
    m.data_liberacao
FROM manejos_sanitarios m
INNER JOIN lotes l
    ON m.lote_id = l.id
INNER JOIN vacinas v
    ON m.vacina_id = v.id;


-- =========================================
-- VERIFICAR LOTES EM PERÍODO DE CARÊNCIA
-- =========================================

SELECT
    l.id,
    l.nome AS lote,
    l.quantidade_cabecas,
    v.nome AS vacina,
    m.data_aplicacao,
    m.data_liberacao
FROM manejos_sanitarios m
INNER JOIN lotes l
    ON m.lote_id = l.id
INNER JOIN vacinas v
    ON m.vacina_id = v.id
WHERE CURDATE() < m.data_liberacao;


-- =========================================
-- VERIFICAR VACINAS OBRIGATÓRIAS
-- =========================================

SELECT
    id,
    nome,
    tipo,
    dias_carencia
FROM vacinas
WHERE obrigatoria = TRUE;


-- =========================================
-- RESUMO DAS VACINAS E MEDICAMENTOS
-- =========================================

SELECT
    tipo,
    COUNT(*) AS quantidade
FROM vacinas
GROUP BY tipo;


-- =========================================
-- RESUMO DE VACINAS OBRIGATÓRIAS
-- =========================================

SELECT
    COUNT(*) AS total_vacinas_obrigatorias
FROM vacinas
WHERE obrigatoria = TRUE;