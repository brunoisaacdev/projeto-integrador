from django.contrib import admin

from .models import Agendamento, Cliente, HorarioFuncionamento, Profissional, Servico


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "email", "ativo", "criado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "email", "telefone")


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco", "duracao_minutos", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ("nome", "especialidade", "telefone", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "especialidade")
    filter_horizontal = ("servicos",)


@admin.register(HorarioFuncionamento)
class HorarioFuncionamentoAdmin(admin.ModelAdmin):
    list_display = ("get_dia_semana_display", "aberto", "hora_abertura", "hora_fechamento")
    list_editable = ("aberto", "hora_abertura", "hora_fechamento")
    ordering = ("dia_semana",)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "profissional", "servico", "inicio", "status")
    list_filter = ("status", "profissional", "inicio")
    search_fields = ("cliente__nome", "profissional__nome")
    date_hierarchy = "inicio"
