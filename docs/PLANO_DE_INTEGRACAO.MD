# Plano seguro de integração do BoviMonitor

1. Manter intacta a versão atual do repositório e trabalhar numa branch de integração autorizada pelo professor.
2. Guardar o estado atual com `git status` e confirmar que nenhuma alteração importante está sem commit.
3. Copiar primeiro `templates/base.html` e `static/css/style.css`; validar o cabeçalho e o caminho do CSS.
4. Integrar os modelos/rotas de `app.py` como uma unidade, pois os endpoints, campos e templates precisam usar os mesmos nomes.
5. Copiar os templates do diretório `templates/` desta versão. Os antigos devem ser arquivados ou removidos somente depois de confirmar que nenhuma rota ainda os renderiza.
6. Instalar requisitos e testar cadastro, login, perfil, propriedade, CRUD de lotes, vacinas e manejos, e API.
7. Revisar o esquema do banco: o novo código usa `instance/bovimonitor_integrado.db`; não aponte para o banco antigo sem planejar migração.
8. Pedir revisão do grupo antes de integrar as branches finais em `main`.

## Mapeamento de templates

| Versão antiga | Template canônico | Observação |
|---|---|---|
| `inicio.html` | `dashboard.html` | Painel principal e atalhos |
| `registroLotes.html` | `lotes.html` | Cadastro/listagem de lotes |
| `editarLotes.html` | `editar_lote.html` | Edição de lote |
| `cadastroManejoeVacinas.html` | `vacinas.html` | Cadastro/listagem do catálogo |
| `historico_deVacinas.html` | `manejos.html` | Histórico de aplicações |
| `editar_manejo.html` antigo | `editar_vacina.html` | O arquivo antigo editava vacina apesar do nome |
| `resumo_Vacinas.html` | `dashboard.html` | Resumo principal |
| `perfil.html` | `perfil.html` | Perfil ampliado com propriedade |
| `editar_perfil.html` | `editar_perfil.html` | Edição de conta |
| `excluirPerfil.html` | `excluir_perfil.html` | Confirmação de exclusão de conta |

**Atenção:** nomes iguais não garantem compatibilidade. O `app.py`, os modelos, os campos dos formulários, as rotas e os templates devem ser integrados e testados juntos.
