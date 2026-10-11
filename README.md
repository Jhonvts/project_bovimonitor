## Grupo do projeto original

- Jhonatas Tavares — templates e organização do Kanban
- Manoela de Deus — templates e gráficos
- Sophie Sugano — backend
- Isabelly Rodrigues — frontend/CSS

Os quatro arquivos PlantUML enviados no repositório original foram preservados em `diagramas/`. O README original da branch backend foi guardado em `docs/README_branch_backend_original.md` para referência.

## Funcionalidades incluídas

- Cadastro/login com hash de senha e gerenciamento de sessão.
- Perfil: consultar/editar nome e telefone e excluir conta.
- Propriedade rural: cadastrar e editar nome, localização e área.
- CRUD de lotes, com isolamento dos lotes por usuário.
- CRUD de vacinas/medicamentos e cálculo da carência.
- CRUD de manejos com cálculo de data de liberação.
- Indicação de bloqueio temporário por carência.
- API de lotes com métodos GET, POST, PUT e DELETE.
- Log de eventos locais.
- Templates Jinja com herança de `base.html` e CSS responsivo.

## Templates ativos nesta versão

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

Os templates antigos `inicio.html`, `registroLotes.html`, `historico_deVacinas.html`, `editarLotes.html`, `cadastroManejoeVacinas.html` e `resumo_Vacinas.html` são substituídos funcionalmente pelas páginas do conjunto acima. Não os apague da branch original sem revisar e registrar a integração com a equipe.

## Requisitos ainda a validar para a entrega da disciplina

- Integração com as branches e revisão dos commits individuais.
- Segurança adicional, por exemplo proteção CSRF e revisão das permissões do catálogo compartilhado.
- Banco exigido na disciplina: usuários com privilégios mínimos, função/procedure, trigger, dump e modelos lógico/físico.
- Testes de integração, deploy no PythonAnywhere, documentação e pitch deck.

Esta é uma base de desenvolvimento acadêmica e precisa de revisão e testes antes de ser usada com dados reais.
