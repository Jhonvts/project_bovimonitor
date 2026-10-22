-- BoviMonitor - objetos programáveis para MariaDB 10.6+
-- Pré-requisito: aplicar docs/modelo_fisico.sql no banco bovimonitor.
-- Esta procedure demonstra consulta isolada por usuário e status calculado no momento da consulta.
USE bovimonitor;

DROP PROCEDURE IF EXISTS listar_lotes;
DELIMITER //
CREATE PROCEDURE listar_lotes(IN p_usuario_id INT)
SQL SECURITY INVOKER
COMMENT 'Lista somente os lotes do produtor e calcula a carência usando a data atual.'
BEGIN
  SELECT l.id, l.nome, l.quantidade_cabecas,
         CASE WHEN EXISTS (
           SELECT 1 FROM manejo_sanitario m
           WHERE m.lote_id = l.id AND m.data_liberacao > CURRENT_DATE()
         ) THEN 'BLOQUEADO' ELSE 'ATIVO' END AS status
  FROM lote l
  WHERE l.usuario_id = p_usuario_id
  ORDER BY l.nome;
END //

DROP TRIGGER IF EXISTS trg_lote_insert_auditoria //
CREATE TRIGGER trg_lote_insert_auditoria
AFTER INSERT ON lote
FOR EACH ROW
BEGIN
  INSERT INTO auditoria_lotes (lote_id, usuario_id, nome_lote, acao)
  VALUES (NEW.id, NEW.usuario_id, NEW.nome, 'INSERT');
END //

DROP TRIGGER IF EXISTS trg_lote_update_auditoria //
CREATE TRIGGER trg_lote_update_auditoria
AFTER UPDATE ON lote
FOR EACH ROW
BEGIN
  INSERT INTO auditoria_lotes (lote_id, usuario_id, nome_lote, acao)
  VALUES (NEW.id, NEW.usuario_id, NEW.nome, 'UPDATE');
END //

DROP TRIGGER IF EXISTS trg_lote_delete_auditoria //
CREATE TRIGGER trg_lote_delete_auditoria
AFTER DELETE ON lote
FOR EACH ROW
BEGIN
  INSERT INTO auditoria_lotes (lote_id, usuario_id, nome_lote, acao)
  VALUES (OLD.id, OLD.usuario_id, OLD.nome, 'DELETE');
END //
DELIMITER ;

-- Demonstração no cliente MariaDB, substituindo o ID por um produtor existente:
-- CALL listar_lotes(2);
-- SELECT acao, lote_id, nome_lote, data_registro FROM auditoria_lotes ORDER BY id DESC;
