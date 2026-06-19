from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cliente",
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    nome = models.CharField("Nome completo", max_length=120)
    email = models.EmailField("E-mail", blank=True)
    telefone = models.CharField("Telefone", max_length=20)
    observacoes = models.TextField("Observações", blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Servico(models.Model):
    nome = models.CharField("Nome do serviço", max_length=120)
    descricao = models.TextField("Descrição", blank=True)
    preco = models.DecimalField("Preço (R$)", max_digits=8, decimal_places=2)
    duracao_minutos = models.PositiveIntegerField("Duração (minutos)", default=30)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.duracao_minutos} min)"


class Profissional(models.Model):
    nome = models.CharField("Nome", max_length=120)
    especialidade = models.CharField("Especialidade", max_length=120, blank=True)
    telefone = models.CharField("Telefone", max_length=20, blank=True)
    email = models.EmailField("E-mail", blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    # Serviços que o profissional pode executar (opcional)
    servicos = models.ManyToManyField(Servico, blank=True, related_name="profissionais")

    class Meta:
        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Agendamento(models.Model):
    STATUS_AGENDADO = "agendado"
    STATUS_CONCLUIDO = "concluido"
    STATUS_CANCELADO = "cancelado"
    STATUS_CHOICES = [
        (STATUS_AGENDADO, "Agendado"),
        (STATUS_CONCLUIDO, "Concluído"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="agendamentos")
    profissional = models.ForeignKey(Profissional, on_delete=models.PROTECT, related_name="agendamentos")
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="agendamentos")
    inicio = models.DateTimeField("Início")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AGENDADO)
    observacoes = models.TextField("Observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    cancelado_em = models.DateTimeField("Cancelado em", null=True, blank=True)
    motivo_cancelamento = models.CharField("Motivo do cancelamento", max_length=255, blank=True)

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.cliente} - {self.servico} em {self.inicio:%d/%m/%Y %H:%M}"

    @property
    def fim(self):
        """Horário de término calculado a partir da duração do serviço."""
        duracao = self.servico.duracao_minutos if self.servico_id else 0
        return self.inicio + timedelta(minutes=duracao)

    @property
    def ativo(self):
        return self.status != self.STATUS_CANCELADO

    def clean(self):
        """Validação para evitar conflito de horários do mesmo profissional."""
        if not self.inicio or not self.servico_id or not self.profissional_id:
            return

        # Não valida conflito em agendamentos cancelados
        if self.status == self.STATUS_CANCELADO:
            return

        inicio = self.inicio
        fim = self.fim

        if inicio < timezone.now() and not self.pk:
            raise ValidationError({"inicio": "Não é possível agendar em uma data/hora passada."})

        # Busca agendamentos do mesmo profissional que não estejam cancelados
        conflitos = Agendamento.objects.filter(
            profissional=self.profissional,
        ).exclude(status=self.STATUS_CANCELADO)

        if self.pk:
            conflitos = conflitos.exclude(pk=self.pk)

        for outro in conflitos:
            # Sobreposição: inicio < outro.fim AND outro.inicio < fim
            if inicio < outro.fim and outro.inicio < fim:
                raise ValidationError(
                    "Conflito de horário: %(prof)s já possui um agendamento de "
                    "%(ini)s até %(fim)s."
                    % {
                        "prof": self.profissional,
                        "ini": timezone.localtime(outro.inicio).strftime("%d/%m/%Y %H:%M"),
                        "fim": timezone.localtime(outro.fim).strftime("%H:%M"),
                    }
                )

    def cancelar(self, motivo=""):
        self.status = self.STATUS_CANCELADO
        self.cancelado_em = timezone.now()
        self.motivo_cancelamento = motivo
        self.save(update_fields=["status", "cancelado_em", "motivo_cancelamento"])
