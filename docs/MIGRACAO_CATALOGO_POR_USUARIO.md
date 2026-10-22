# Migração: catálogos sanitários por produtor

A aplicação executa a migração da antiga restrição global de nome da tabela `vacina` durante a inicialização:
- preserva os registros e IDs existentes;
- mantém itens com `usuario_id = NULL` como catálogo compartilhado;
- permite nomes iguais em catálogos pessoais de produtores diferentes;
- continua impedindo que um produtor duplique um item do próprio catálogo ou do catálogo compartilhado.

No SQLite, a inicialização recria apenas a tabela `vacina` para remover a antiga restrição `UNIQUE(nome)`, copiando seus dados. No MariaDB, remove o índice único antigo. Faça sempre uma cópia de segurança do banco antes de atualizar o sistema.

## Regras de acesso

- Produtor: cadastra, edita e exclui seus próprios lotes, manejos e itens sanitários.
- Produtor: consulta itens compartilhados e os próprios itens; não altera itens de outro produtor.
- Administrador: visualiza e gerencia lotes, manejos e itens sanitários de todos os produtores.
- Item compartilhado: criado pelo administrador e visível a todos.
- Item pessoal: só pode ser usado em manejos do produtor proprietário.
- Ao excluir um lote, seus manejos são excluídos junto. Ao excluir uma vacina/medicamento, os manejos que dependem daquele item também são excluídos, e a situação dos lotes afetados é recalculada.

Os formulários de exclusão incluem token CSRF; a autorização também é validada no servidor, não apenas na interface.
