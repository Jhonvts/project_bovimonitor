
-- BoviMonitor - Objetos programáveis do banco MariaDB

DELIMITER //

-- Procedure para consultar os lotes
CREATE PROCEDURE listar_lotes()
BEGIN
    SELECT id, nome, quantidade_cabecas, status
    FROM lote
    ORDER BY nome;
END //

-- Gatilho para registrar novos lotes na auditoria
CREATE TRIGGER trg_novo_lote
AFTER INSERT ON lote
FOR EACH ROW
BEGIN
    INSERT INTO auditoria_lotes (lote_id, nome_lote)
    VALUES (NEW.id, NEW.nome);
END //

DELIMITER ;
