# BoviMonitor

Sistema escolar para organizar lotes de bovinos, aplicações sanitárias e períodos de carência. O painel mostra a situação atual dos lotes; o histórico guarda a data de liberação calculada quando o manejo é registrado.

## O que o sistema oferece

- Cadastro, login e edição de perfil com senha armazenada em hash.
- Propriedade rural, lotes e históricos sanitários separados por usuário.
- Catálogo compartilhado administrado pelo admin e catálogo pessoal de itens sanitários gerenciado por cada produtor.
- Carência calculada no registro do manejo; alterações futuras no catálogo não mudam o histórico já registrado.
- Painel do produtor com lotes, cabeças, liberações próximas e manejos recentes.
- Área administrativa com totais, busca de usuários, gerenciamento global de lotes, manejos e itens sanitários, ativação/desativação de contas e auditoria local.
- Proteção CSRF, sessão com prazo de 30 minutos, cookies HttpOnly/SameSite, limite de tentativas, cabeçalhos de segurança e registro de eventos.
- API JSON para lotes, vacinas, manejos e propriedade, com GET/POST/PUT/DELETE conforme o recurso.

## Executar no Windows

Requer Python 3.10 ou superior. O ambiente recomendado para a demonstração é Python 3.11 ou 3.12.

1. Abra o PowerShell na pasta do projeto.
2. Crie e ative um ambiente virtual:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instale os pacotes:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Crie seu arquivo de configuração local e gere uma chave secreta:

   ```powershell
   Copy-Item .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

5. Edite `.env`. Troque `SECRET_KEY`, `ADMIN_EMAIL` e `ADMIN_INITIAL_PASSWORD` por valores próprios. Não envie `.env` ao Git. A senha inicial precisa ter no mínimo 10 caracteres.
6. Inicie:

   ```powershell
   python app.py
   ```

7. Acesse `http://127.0.0.1:5000`. Banco e administrador inicial são preparados quando o módulo da aplicação é carregado, inclusive pelo WSGI no deploy. A conta inicial só é criada se o e-mail configurado ainda não existir; mudar a senha no `.env` não troca a senha de uma conta existente.

O SQLite local é criado em `instance/bovimonitor.db`; os logs ficam em `instance/bovimonitor.log`. Faça cópia de segurança antes de apagar esses arquivos.

## Banco de dados

SQLite é a opção padrão para desenvolvimento e apresentação. A aplicação também aceita MariaDB com o driver PyMySQL. Para preparar uma instalação MariaDB:

1. Como DBA, aplique `docs/modelo_fisico.sql`.
2. Aplique `docs/objetos_programaveis.sql` para criar a procedure e os gatilhos.
3. Edite as senhas de exemplo em `docs/usuarios.sql` e execute-o como DBA.
4. Configure `DATABASE_URL` no `.env`, por exemplo:

   ```text
   DATABASE_URL=mysql+pymysql://bovimonitor_app:SENHA_URL_ENCODED@localhost/bovimonitor?charset=utf8mb4
   ```

   Caracteres especiais da senha devem ser codificados para URL. O usuário `bovimonitor_app` tem apenas SELECT, INSERT, UPDATE e DELETE. A criação da estrutura e a instalação de gatilhos devem ser feitas pelo DBA antes de iniciar a aplicação com esse usuário.

`docs/dump_bovimonitor_mariadb.sql` contém apenas a estrutura, sem usuários/dados de demonstração. Não use dumps com dados pessoais como banco da apresentação.

## Administrador e privacidade

O administrador vê a lista de contas e pode consultar e gerenciar lotes, manejos e itens sanitários de todos os produtores, sem autenticar como o produtor nem revelar sua senha. A conta pode ser desativada ou reativada; o administrador não pode desativar a si mesmo nem outra conta administrativa. Exclusão de usuário não está disponível no painel para preservar o histórico.

O catálogo tem duas camadas: a administração mantém itens compartilhados, disponíveis a todos; cada produtor também pode cadastrar e gerenciar seus próprios itens, visíveis apenas para ele. Assim, produtores não alteram o catálogo comum nem os itens pessoais de outras contas. Ao editar a carência, os manejos antigos mantêm a liberação já calculada; a nova regra vale para as próximas aplicações. Os nomes podem se repetir entre catálogos pessoais de produtores diferentes; cada produtor não pode duplicar um nome que já esteja no próprio catálogo ou no catálogo compartilhado. O administrador evita colisões no catálogo compartilhado.

Cada produtor pode excluir seus próprios manejos e lotes. Ao excluir um lote, o sistema pede confirmação e remove também os manejos vinculados. Registros de outras contas não podem ser consultados nem excluídos pelo produtor.

## Segurança e demonstração para a professora

Veja `docs/SEGURANCA.md` para risco mitigado e roteiro de demonstração. Casos fáceis de mostrar:

- Tentar abrir ou editar um lote usando outra conta: o registro não é encontrado.
- Enviar formulário sem token CSRF: o sistema rejeita com erro 400 amigável.
- Fazer seis tentativas de login em um minuto: o limitador retorna 429.
- Entrar como produtor, cadastrar um item sanitário pessoal e conferir que outro produtor não o enxerga; tentar editar item compartilhado retorna 403.
- Fazer login correto, falho e registrar manejo; consultar o painel administrativo de auditoria ou o arquivo de log.
- Consultar os usuários MariaDB: `SHOW GRANTS FOR 'bovimonitor_app'@'localhost';`.

Logs locais não substituem um serviço centralizado e administradores com acesso ao servidor podem ler o arquivo. Use HTTPS em deploy e configure `SESSION_COOKIE_SECURE=1`. Ative `TRUST_PROXY=1` somente se houver exatamente um proxy reverso confiável à frente do Flask.

## API

Todas as rotas exigem sessão autenticada. Métodos que alteram dados também exigem token CSRF no cabeçalho `X-CSRFToken`; obtenha o valor de `csrf_token()` em um formulário autenticado. A API respeita a mesma separação: produtor cria/edita/remove os próprios itens, e o administrador mantém os itens compartilhados. A API é voltada para demonstração com cliente que mantém os cookies da sessão.

Exemplo com Python e `requests` instalado: faça login em uma sessão e envie o token junto com JSON. A requisição à página protegida fornece um token CSRF válido para essa sessão.

```python
import re
import requests

base = "http://127.0.0.1:5000"
s = requests.Session()
html = s.get(f"{base}/login").text
token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
s.post(f"{base}/login", data={
    "csrf_token": token,
    "email": "produtor@exemplo.com",
    "senha": "SENHA_DA_CONTA",
})
html = s.get(f"{base}/lotes").text
token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
resposta = s.post(
    f"{base}/api/lotes",
    json={"nome": "Lote de demonstração", "quantidade_cabecas": 25},
    headers={"X-CSRFToken": token},
)
print(resposta.status_code, resposta.json())
```

| Recurso | Rotas | Métodos |
|---|---|---|
| Lotes | `/api/lotes`, `/api/lotes/<id>` | GET, POST, PUT, DELETE |
| Vacinas/medicamentos | `/api/vacinas`, `/api/vacinas/<id>` | GET, POST, PUT, DELETE |
| Manejos | `/api/manejos`, `/api/manejos/<id>` | GET, POST, PUT, DELETE |
| Propriedade | `/api/propriedade` | GET, POST, PUT, DELETE |

Excluir uma vacina/medicamento também remove os manejos vinculados a esse item e recalcula a situação dos lotes afetados. A exclusão de lote remove seus manejos vinculados. Erros de validação retornam JSON com status `400`; permissão negada retorna `403`.

## Estrutura

```text
app.py                       rotas e inicialização da aplicação
config.py                    configuração de ambiente e sessão
extensions.py                extensões Flask compartilhadas
models.py                    entidades e relacionamentos do banco
templates/                   interface Jinja
static/css/style.css         interface verde e azul responsiva
docs/modelo_fisico.sql       esquema MariaDB comentado
docs/usuarios.sql            contas técnicas e privilégios do banco
docs/objetos_programaveis.sql procedure e gatilhos
docs/SEGURANCA.md            mecanismos e demonstrações\ndocs/MIGRACAO_CATALOGO_POR_USUARIO.md  migração e regras do catálogo
diagramas/                   modelos e fluxos PlantUML
```

## Limites desta versão

O log administrativo é local ao servidor. A aplicação é um protótipo acadêmico: antes de usar dados reais, configure HTTPS, backups, política de retenção e auditoria fora do processo da aplicação. O administrador cadastra itens compartilhados e pode gerenciar itens pessoais de qualquer produtor; cada produtor gerencia apenas o próprio catálogo e seus lotes e manejos.
