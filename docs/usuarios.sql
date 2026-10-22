-- BoviMonitor - contas técnicas do MariaDB
-- Execute como usuário DBA depois de criar o banco e a estrutura.
-- Troque todas as senhas de exemplo por senhas diferentes e fortes antes de executar.
CREATE USER IF NOT EXISTS 'bovimonitor_admin'@'localhost'
  IDENTIFIED BY 'SUBSTITUA_POR_SENHA_FORTE_DE_ADMINISTRACAO';
CREATE USER IF NOT EXISTS 'bovimonitor_app'@'localhost'
  IDENTIFIED BY 'SUBSTITUA_POR_OUTRA_SENHA_FORTE_DA_APLICACAO';

-- Conta administrativa usada apenas para manutenção e aplicação de scripts/migrações.
GRANT ALL PRIVILEGES ON bovimonitor.* TO 'bovimonitor_admin'@'localhost';

-- A aplicação recebe somente as operações de dados necessárias no funcionamento normal.
GRANT SELECT, INSERT, UPDATE, DELETE ON bovimonitor.*
  TO 'bovimonitor_app'@'localhost';

-- Não conceda GRANT OPTION nem acesso global ao usuário da aplicação.
FLUSH PRIVILEGES;

-- Para servidor remoto, crie as contas com o host de origem específico da aplicação,
-- em vez de usar '%' sem necessidade. Guarde as senhas no cofre/variáveis do servidor.
