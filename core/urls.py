from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", views.SistemaLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("clientes/cadastro/", views.cliente_cadastro, name="cliente_cadastro"),
    path("agendar/", views.agendar, name="agendar"),
    path("meus-agendamentos/", views.meus_agendamentos, name="meus_agendamentos"),

    path("", views.dashboard, name="dashboard"),

    path("clientes/", views.cliente_list, name="cliente_list"),
    path("clientes/novo/", views.cliente_form, name="cliente_novo"),
    path("clientes/<int:pk>/editar/", views.cliente_form, name="cliente_editar"),
    path("clientes/<int:pk>/excluir/", views.cliente_delete, name="cliente_excluir"),

    path("servicos/", views.servico_list, name="servico_list"),
    path("servicos/novo/", views.servico_form, name="servico_novo"),
    path("servicos/<int:pk>/editar/", views.servico_form, name="servico_editar"),
    path("servicos/<int:pk>/excluir/", views.servico_delete, name="servico_excluir"),

    path("profissionais/", views.profissional_list, name="profissional_list"),
    path("profissionais/novo/", views.profissional_form, name="profissional_novo"),
    path("profissionais/<int:pk>/editar/", views.profissional_form, name="profissional_editar"),
    path("profissionais/<int:pk>/excluir/", views.profissional_delete, name="profissional_excluir"),

    path("horarios-funcionamento/", views.horario_funcionamento, name="horario_funcionamento"),

    path("agendamentos/", views.agendamento_list, name="agendamento_list"),
    path("agendamentos/novo/", views.agendamento_form, name="agendamento_novo"),
    path("agendamentos/<int:pk>/editar/", views.agendamento_form, name="agendamento_editar"),
    path("agendamentos/<int:pk>/concluir/", views.agendamento_concluir, name="agendamento_concluir"),
    path("agendamentos/<int:pk>/cancelar/", views.agendamento_cancelar, name="agendamento_cancelar"),
]
