# Projeto Integrador - Premium Barbearia

Sistema web desenvolvido em Django para gerenciar os agendamentos de uma barbearia. O projeto centraliza o cadastro de clientes, servicos, profissionais, horarios de funcionamento e atendimentos, reduzindo controles manuais e facilitando a organizacao da rotina da equipe.

## Objetivo

O sistema foi criado para tornar o processo de agendamento mais simples, claro e automatizado. O cliente consegue marcar e acompanhar seus horarios, enquanto a administracao da barbearia controla a agenda, os cadastros e o status dos atendimentos em um painel interno.

## Principais funcionalidades

- Cadastro de clientes com nome, e-mail, telefone, observacoes e vinculo com usuario do sistema.
- Cadastro de servicos com descricao, preco, duracao e status ativo/inativo.
- Cadastro de profissionais com especialidade, contato, foto e servicos atendidos.
- Controle de horarios de funcionamento por dia da semana.
- Registro de fechamentos em datas especificas, como feriados ou dias sem atendimento.
- Agendamento online para clientes autenticados.
- Listagem de horarios disponiveis considerando servico, profissional, expediente e agenda ocupada.
- Area "Meus agendamentos" para o cliente acompanhar horarios agendados, concluidos e cancelados.
- Cancelamento de agendamento pelo cliente com motivo obrigatorio.
- Painel administrativo para gerenciar clientes, servicos, profissionais e agendamentos.
- Conclusao de atendimentos pelo administrador.
- Cancelamento administrativo com registro do motivo.
- Recuperacao de senha por e-mail.
- Envio de e-mails automaticos de confirmacao de agendamento e conclusao de atendimento.

## Perfis de acesso

### Cliente

O cliente acessa uma area simplificada, voltada para o agendamento e acompanhamento dos proprios horarios. Ele pode escolher servico, profissional, data e horario disponivel, consultar seus agendamentos e cancelar um horario futuro informando o motivo.

### Administrador

O administrador acessa o painel de gestao da barbearia. Nesse ambiente, e possivel visualizar indicadores, cadastrar e editar informacoes essenciais, acompanhar a agenda, concluir atendimentos e cancelar agendamentos quando necessario.

## Regras de agendamento

O sistema possui validacoes para evitar inconsistencias na agenda:

- Nao permite criar agendamentos em data ou hora passada.
- Nao permite conflito de horario para o mesmo profissional.
- Verifica se o horario escolhido esta dentro do expediente de funcionamento.
- Desconsidera horarios cancelados ao calcular disponibilidade.
- Respeita datas de fechamento cadastradas.
- Calcula o horario final do atendimento com base na duracao do servico.

## Cancelamentos

Os cancelamentos registram data, status e motivo. Quando o cliente cancela um horario, o motivo fica visivel para o administrador na tela de agendamentos. Quando o administrador cancela, o motivo fica visivel para o cliente em "Meus agendamentos".

O cliente so pode cancelar agendamentos ativos e que ainda nao passaram da data e hora marcada.

## Notificacoes por e-mail

O projeto utiliza envio de e-mails para melhorar a comunicacao com o cliente:

- recuperacao de senha;
- confirmacao de novo agendamento;
- aviso de atendimento concluido.

Os e-mails de agendamento e conclusao sao enviados em segundo plano para evitar demora no carregamento das telas.

## Tecnologias utilizadas

- Python
- Django
- PostgreSQL
- Supabase como banco de dados hospedado
- HTML, CSS e JavaScript
- SMTP para envio de e-mails

## Estrutura geral

O projeto possui uma aplicacao principal chamada `core`, onde ficam os modelos, formularios, views, rotas, templates e arquivos estaticos. Os principais modelos do sistema sao:

- `Cliente`
- `Servico`
- `Profissional`
- `HorarioFuncionamento`
- `FechamentoFuncionamento`
- `Agendamento`

Essa estrutura permite separar as responsabilidades do sistema e manter as regras principais concentradas no backend.

## Resultado esperado

Com o sistema, a barbearia ganha uma rotina de atendimento mais organizada, com menos risco de conflito de horarios, melhor controle sobre os profissionais e uma experiencia mais clara para o cliente durante todo o ciclo do agendamento.
