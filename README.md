| 🐂 BoviMonitor: Sistema de Controle Sanitário e Manejo de Rebanhos. O BoviMonitor é um sistema desenvolvido para auxiliar pecuaristas e responsáveis pelo manejo de rebanhos no registro, acompanhamento e organização das vacinações e procedimentos sanitários realizados nos lotes de gado. A proposta do projeto é facilitar o controle das informações relacionadas ao manejo, evitando esquecimentos e tornando mais simples o acompanhamento de datas de aplicação, tipos de vacina ou medicamento, lotes envolvidos e períodos de carência.

| 🎯 Objetivo: O principal objetivo do BoviMonitor é oferecer uma ferramenta que facilite o gerenciamento sanitário do rebanho, permitindo que o usuário tenha maior controle sobre:

- Cadastro e acompanhamento dos lotes;
- Registro de vacinas e medicamentos;
- Data de aplicação dos procedimentos;
- Controle dos dias de carência;
- Identificação de lotes temporariamente bloqueados para venda;
- Histórico de manejos sanitários;
- Acompanhamento de vacinas obrigatórias;
- Consulta de informações e relatórios do rebanho.

| 👥 Público-alvo: O sistema é voltado principalmente para pecuaristas, que precisam acompanhar a situação sanitária de seus animais, capatazes e gerentes de fazenda, responsáveis pelo registro dos procedimentos realizados no curral e responsáveis pelo controle e organização do manejo do rebanho.

| ⚙️ Funcionamento: O fluxo principal do sistema começa com a seleção de um lote e o registro do procedimento sanitário realizado. Após informar a vacina ou medicamento e a data da aplicação, o sistema verifica as informações relacionadas ao período de carência. Quando houver período de carência, a data de liberação é calculada automaticamente com base na data da aplicação e na quantidade de dias definida para o medicamento. Durante esse período, o lote pode ser sinalizado como bloqueado para venda. O sistema também permite o acompanhamento de vacinas obrigatórias, atualizando o calendário sanitário quando uma aplicação é registrada.


| 🗃️ Estrutura do Banco de Dados: O modelo de dados do BoviMonitor é composto principalmente por três entidades:

| 🐄 Lote: Armazena informações relacionadas aos lotes de animais.

- id;
- nome;
- quantidade_cabecas;
- status;

| 💉 Vacina: Armazena informações sobre vacinas e medicamentos utilizados no manejo.

- id;
- nome;
- fabricante;
- dias_carencia;
- obrigatoria.

|📋 Manejo Sanitário: Registra a aplicação de vacinas ou medicamentos em cada lote.

- id;
- lote_id;
- vacina_id;
- data_aplicacao;
- data_liberacao.

A relação entre essas entidades permite identificar qual vacina foi aplicada em determinado lote e em qual data, além de possibilitar o controle do período de carência.

| 👨‍💻 Contribuidores

| Integrantes:            
| Jhonatas Tavares (@Jhonvts) -                  
| Manoela de Deus (@manoela2008) -  
| Sophie Sugano (@sophiiesm) -                       
| Isabelly Rodrigues (@isabellyRodrgs) -              

