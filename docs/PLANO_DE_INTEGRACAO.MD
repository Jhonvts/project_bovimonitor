# Integração e apresentação do BoviMonitor

## Antes de demonstrar

1. Instale os requisitos e configure `.env` conforme o README.
2. Inicie a aplicação com `python app.py`; o carregamento cria o esquema local e o administrador inicial.
3. Cadastre uma conta de produtor e adicione lote, vacina/medicamento e manejo.
4. Entre como administrador e mostre o painel, a consulta de usuário e a auditoria.
5. Demonstre CSRF ausente, autorização de catálogo e bloqueio temporário por carência.

## Arquivos por responsabilidade

- `config.py`: segredo, banco, sessão e opções de ambiente.
- `extensions.py`: objeto SQLAlchemy compartilhado.
- `models.py`: entidades e relacionamentos.
- `app.py`: inicialização, autenticação, páginas, administração e API.
- `templates/` e `static/`: interface Jinja e CSS responsivo.
- `docs/`: scripts SQL, regras de segurança e roteiro da apresentação.

## Banco MariaDB para apresentação

1. Aplicar `docs/modelo_fisico.sql` com conta DBA.
2. Aplicar `docs/objetos_programaveis.sql`.
3. Trocar as senhas fictícias e executar `docs/usuarios.sql`.
4. Configurar `DATABASE_URL` para `bovimonitor_app` e iniciar a aplicação.
5. Criar a conta de administrador da aplicação com `ADMIN_EMAIL` e `ADMIN_INITIAL_PASSWORD` no `.env`.

Não importe dumps com usuários ou hashes de teste. O arquivo `docs/dump_bovimonitor_mariadb.sql` é somente esquema e não contém dados.

## Limite arquitetural atual

Os modelos e a configuração foram separados. As rotas permanecem em `app.py` para manter o protótipo escolar simples de executar; uma etapa futura pode dividir autenticação, administração e API em Blueprints sem alterar os modelos ou os templates.
