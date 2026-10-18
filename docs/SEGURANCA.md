# Segurança da Informação — BoviMonitor

## 1. Autenticação e proteção de senhas

O sistema utiliza Flask-Login para gerenciar a autenticação dos usuários e o Werkzeug para armazenar senhas em formato de hash, evitando o armazenamento de senhas em texto puro.

**Risco mitigado:** exposição direta das senhas armazenadas no banco de dados.

**Demonstração:** cadastrar um usuário e verificar se a senha é armazenada como hash.

## 2. Controle de acesso

As rotas protegidas exigem autenticação. O sistema também utiliza verificações de propriedade para impedir que usuários acessem ou alterem lotes e manejos pertencentes a outras contas.

**Risco mitigado:** acesso ou alteração não autorizada de registros de outros produtores.

**Demonstração:** entrar com duas contas diferentes e verificar se uma delas consegue acessar os registros privados da outra.

## 3. Auditoria de eventos

O sistema foi configurado para registrar eventos em arquivo de log, incluindo informações de usuário, endereço IP e descrição da ação. As tentativas de login malsucedidas também devem ser verificadas durante os testes.

**Risco mitigado:** dificuldade de identificar e investigar atividades relevantes no sistema.

**Demonstração:** realizar um login correto, uma tentativa malsucedida e uma ação registrada; conferir os eventos no arquivo de log.

## 4. Gerenciamento de sessão

A aplicação configura duração para sessões permanentes e utiliza as opções de segurança dos cookies `HttpOnly` e `SameSite`. A opção `Secure` deve ser habilitada quando a aplicação estiver sendo servida por HTTPS.

**Risco mitigado:** exposição desnecessária de cookies e manutenção de sessões por tempo excessivo.

## 5. Pendências de segurança

- Implementar e testar proteção CSRF nos formulários e nas operações que alteram dados.
- Implementar limitação de tentativas de login.
- Revisar as permissões do catálogo de vacinas e medicamentos, respeitando a propriedade dos registros.
- Testar os mecanismos de segurança e registrar evidências para a apresentação.

Este documento deve ser atualizado conforme as funcionalidades forem implementadas e testadas.