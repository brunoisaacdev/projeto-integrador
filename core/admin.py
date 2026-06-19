from django.contrib import admin

from .models import Agendamento, Cliente, Profissional, Servico


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


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "profissional", "servico", "inicio", "status")
    list_filter = ("status", "profissional", "inicio")
    search_fields = ("cliente__nome", "profissional__nome")
    date_hierarchy = "inicio"
