# Segurança da Informação — BoviMonitor

Este documento descreve o que a aplicação implementa e como demonstrar os controles para a avaliação. As telas e logs aqui mencionados são evidências para a apresentação; não inclua senhas reais ou dados pessoais nos prints.

## 1. Identificação e autenticação

- Flask-Login protege as páginas privadas e mantém a identidade na sessão.
- Senhas são guardadas somente como hash do Werkzeug. O cadastro exige 10 caracteres.
- Login malsucedido, inclusive conta desativada, não revela se o e-mail existe.
- Limites: até 5 POST de login por minuto e até 5 tentativas de cadastro por hora por endereço IP.
- Contas desativadas não conseguem iniciar sessão e sessões ativas são encerradas na próxima requisição.

**Risco reduzido:** acesso sem credencial, descoberta de contas e tentativa automatizada de senha.

**Demonstração:** faça uma tentativa de login incorreta e confira o evento no log; repita o POST de login mais de cinco vezes em um minuto para observar a página 429. Não use senha real para a demonstração.

## 2. Sessões

As sessões permanentes expiram após 30 minutos. Os cookies têm `HttpOnly` e `SameSite=Lax`. Em HTTPS, configure `SESSION_COOKIE_SECURE=1`; essa opção também habilita HSTS. Logout é realizado por POST protegido por CSRF. Em proxy reverso, configure `TRUST_PROXY=1` somente quando houver exatamente um proxy confiável.

**Risco reduzido:** roubo ou reutilização prolongada de cookie e falsificação do IP usado pelo limitador quando os cabeçalhos de proxy estão configurados corretamente.

**Demonstração:** inspecione o cookie no navegador e os cabeçalhos de resposta; mostre o logout por formulário POST. Em desenvolvimento HTTP, `Secure` fica desligado para permitir login local.

## 3. Autorização e menor privilégio

- Lotes, manejos e propriedades são consultados pelo `usuario_id` da sessão.
- O administrador cria, edita e exclui itens do catálogo compartilhado. Cada produtor pode criar e gerenciar seus itens pessoais, que só ficam visíveis para a própria conta. Todos podem consultar os itens compartilhados.
- Exclusão e edição de lotes e manejos são limitadas aos dados pertencentes ao produtor autenticado. A exclusão de um lote remove também seus manejos vinculados, após confirmação na interface.
- Administradores consultam lotes e manejos de outros usuários em modo somente leitura. A tela não assume a identidade do produtor e não permite editar dados particulares.
- Apenas administradores podem abrir o painel de contas e auditoria. O administrador não pode desativar a própria conta.
- O usuário MariaDB da aplicação (script `docs/usuarios.sql`) recebe somente SELECT, INSERT, UPDATE e DELETE no banco. Criação de tabelas/rotinas é tarefa do DBA.

**Risco reduzido:** leitura ou alteração cruzada de dados e permissões excessivas no banco.

**Demonstração:** com duas contas de produtor, tente abrir um lote da outra conta; cadastre um item pessoal e confirme que a segunda conta não o vê; tente alterar um item compartilhado como produtor e observe 403; abra o painel como administrador e mostre que os dados dos produtores são apenas consulta.

## 4. Proteção CSRF

Flask-WTF `CSRFProtect` valida formulários POST e operações da API. Formulários incluem token oculto; chamadas JSON devem enviar o token no cabeçalho `X-CSRFToken`, junto com o cookie da sessão. Token inválido ou expirado recebe uma página amigável com HTTP 400.

**Risco reduzido:** sites externos induzirem o navegador autenticado a enviar uma operação em nome do usuário.

**Demonstração:** envie POST a uma rota protegida sem token; a aplicação rejeita a requisição. Em API, faça a chamada com cookie da sessão e token, e depois repita sem o cabeçalho.

## 5. Validação e integridade

O servidor verifica tamanho dos textos, quantidade de cabeças, área, categoria, carência e datas. A data de manejo não pode ser futura. Um item sanitário usado em histórico não pode ser apagado. A exclusão de lote remove seus manejos vinculados. Mudanças futuras no catálogo não recalculam registros antigos. Os nomes de itens permanecem únicos no banco.

**Risco reduzido:** dados inválidos, erro do banco por campo longo e alteração acidental da interpretação do histórico.

## 6. Auditoria

`logging` grava data/hora, nível, ID da conta, IP e ação em `instance/bovimonitor.log`. O log inclui logins bem-sucedidos e falhos, cadastro, alterações e exclusões. A área administrativa exibe os últimos 150 eventos. O MariaDB tem ainda triggers para inserir, atualizar e excluir lotes e uma tabela `auditoria_lotes`.

**Risco reduzido:** falta de rastreabilidade de ações relevantes.

**Demonstração:** efetue login correto e incorreto, registre um manejo e altere um lote; confira a tela Administração > Auditoria e o arquivo no diretório `instance`. Para demonstrar banco, execute `CALL listar_lotes(ID_DO_USUARIO);` e consulte `auditoria_lotes` após inserir/alterar lote.

**Limite:** o log local não é inviolável. Uma pessoa com acesso ao servidor pode alterá-lo; produção deve encaminhar eventos a um serviço central.

## 7. Cabeçalhos e erros

As respostas incluem `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Permissions-Policy`. HTTP 403, 404, 429, CSRF 400 e erro 500 recebem páginas da aplicação. Erros internos são registrados pelo logger do Flask.

## 8. Configuração e chaves

`.env.example` contém apenas valores fictícios. `.env`, bancos e logs locais estão no `.gitignore`. O `SECRET_KEY` é obrigatório e deve ser aleatório; use um valor diferente para cada ambiente. `ADMIN_INITIAL_PASSWORD` cria o primeiro administrador e não atualiza senhas de contas existentes.

## 9. Roteiro de apresentação (2–3 minutos)

1. Mostre `docs/SEGURANCA.md` e explique autenticação, autorização e auditoria.
2. Entre como produtor, registre um manejo e mostre a data de liberação.
3. Tente ação sem CSRF e mostre que falha; demonstre o catálogo pessoal do produtor e o bloqueio de edição do catálogo compartilhado.
4. Entre como administrador, consulte a conta do produtor sem trocar de identidade.
5. Mostre a auditoria e, se houver MariaDB, os privilégios do usuário de aplicação com `SHOW GRANTS`.
