
# 🐂 BoviMonitor: Sistema de Controle Sanitário e Manejo de Rebanhos

O BoviMonitor é um sistema desenvolvido para auxiliar pecuaristas e responsáveis pelo manejo de rebanhos no registro, acompanhamento e organização das vacinações e procedimentos sanitários realizados nos lotes de gado.

## 🎯 Objetivo

Facilitar o gerenciamento sanitário do rebanho, permitindo:

- Cadastro e acompanhamento dos lotes;
- Registro de vacinas e medicamentos;
- Controle das datas de aplicação e dos períodos de carência;
- Identificação de lotes temporariamente bloqueados para venda;
- Histórico de manejos sanitários;
- Acompanhamento de vacinas obrigatórias;
- Consulta de informações e relatórios do rebanho.

## 👥 Público-alvo

O sistema é voltado para pecuaristas, capatazes, gerentes de fazenda e responsáveis pelo controle sanitário e pela organização do manejo do rebanho.


## ⚙️ Funcionamento

O usuário seleciona um lote e registra o procedimento sanitário realizado, informando a vacina ou o medicamento e a data de aplicação. Com base nos dias de carência cadastrados, o sistema calcula a data de liberação e pode indicar que o lote está temporariamente bloqueado para venda.

## 🗃️ Estrutura do banco de dados

As principais entidades do sistema incluem:

- **Lote:** identificação, nome, quantidade de cabeças e status.
- **Vacina:** nome, fabricante, dias de carência e indicação de obrigatoriedade.
- **Manejo Sanitário:** lote relacionado, vacina ou medicamento, data de aplicação e data de liberação.

O projeto também contém arquivos SQL e diagramas para documentar a estrutura do banco de dados.

## ✅ Funcionalidades implementadas na versão backend

- Cadastro e login com hash de senha e gerenciamento de sessão.
- Consulta e edição de perfil.
- Exclusão de conta, conforme as regras implementadas no sistema.
- Cadastro e edição de propriedades rurais.
- Cadastro, edição e gerenciamento de lotes.
- Cadastro e gerenciamento de vacinas e medicamentos.
- Registro e edição de manejos sanitários.
- Cálculo da data de liberação conforme o período de carência.
- Indicação de bloqueio temporário por carência.
- API de lotes com métodos GET, POST, PUT e DELETE.
- Registro local de eventos.
- Templates Jinja com herança de `base.html` e CSS responsivo.

## 📁 Estrutura dos templates ativos

```text
templates/
  base.html
  cadastro.html
  cadastro_propriedade.html
  dashboard.html
  editar_lote.html
  editar_manejo.html
  editar_perfil.html
  editar_propriedade.html
  editar_vacina.html
  erro.html
  excluir_perfil.html
  login.html
  lotes.html
  manejos.html
  perfil.html
  vacinas.html
```

Os templates antigos foram substituídos funcionalmente pelas páginas atuais, conforme a organização da branch `backend`.


## Requisitos de execução

- Python 3.10 ou superior, com suporte a `hashlib.scrypt`.
- Dependências Python instaladas conforme `requirements.txt`.
- Variáveis de ambiente configuradas conforme o arquivo `.env.example`.

**Ambiente de desenvolvimento:** Python 3.13.x no Windows.

A compatibilidade deve ser validada no ambiente de implantação, especialmente
o suporte ao algoritmo de hash de senhas utilizado pelo Werkzeug.


## 👨‍💻 Integrantes do projeto

- Jhonatas Tavares (@Jhonvts) — templates e organização do Kanban.
- Manoela de Deus (@manoela2008) — templates e gráficos.
- Sophie Sugano (@sophiiesm) — backend.
- Isabelly Rodrigues (@isabellyRodrgs) — frontend/CSS.

## 📌 Pendências de validação

- Revisão da integração entre as branches e dos commits individuais.
- Revisão de segurança, incluindo proteção CSRF e permissões.
- Validação do banco de dados, usuários, privilégios, funções, procedures e triggers.
- Testes de integração.
- Deploy no PythonAnywhere.
- Finalização da documentação e do pitch deck.

O BoviMonitor é um projeto acadêmico em desenvolvimento e precisa de testes e revisão antes de ser utilizado com dados reais.
