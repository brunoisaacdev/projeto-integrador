from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
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
    foto = models.FileField(
        "Foto",
        upload_to="profissionais/",
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])
        ],
    )
    ativo = models.BooleanField("Ativo", default=True)
    # Serviços que o profissional pode executar (opcional)
    servicos = models.ManyToManyField(Servico, blank=True, related_name="profissionais")

    class Meta:
        verbose_name = "Profissional"
        verbose_name_plural = "Profissionais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class HorarioFuncionamento(models.Model):
    SEGUNDA = 0
    TERCA = 1
    QUARTA = 2
    QUINTA = 3
    SEXTA = 4
    SABADO = 5
    DOMINGO = 6
    DIAS_SEMANA = [
        (SEGUNDA, "Segunda-feira"),
        (TERCA, "Terça-feira"),
        (QUARTA, "Quarta-feira"),
        (QUINTA, "Quinta-feira"),
        (SEXTA, "Sexta-feira"),
        (SABADO, "Sábado"),
        (DOMINGO, "Domingo"),
    ]

    dia_semana = models.PositiveSmallIntegerField(
        "Dia da semana",
        choices=DIAS_SEMANA,
        unique=True,
    )
    aberto = models.BooleanField("Atende neste dia", default=True)
    hora_abertura = models.TimeField("Abertura", default=time(hour=9))
    hora_fechamento = models.TimeField("Fechamento", default=time(hour=19))
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Horário de funcionamento"
        verbose_name_plural = "Horários de funcionamento"
        ordering = ["dia_semana"]

    def __str__(self):
        if not self.aberto:
            return f"{self.get_dia_semana_display()} - fechado"
        return (
            f"{self.get_dia_semana_display()} - "
            f"{self.hora_abertura:%H:%M} às {self.hora_fechamento:%H:%M}"
        )

    @classmethod
    def padroes(cls):
        return [
            {
                "dia_semana": dia,
                "aberto": True,
                "hora_abertura": time(hour=9),
                "hora_fechamento": time(hour=19),
            }
            for dia, _nome in cls.DIAS_SEMANA
        ]

    @classmethod
    def garantir_padrao(cls):
        existentes = set(cls.objects.values_list("dia_semana", flat=True))
        for dados in cls.padroes():
            if dados["dia_semana"] not in existentes:
                cls.objects.create(**dados)

    @classmethod
    def para_data(cls, data):
        dia_semana = data.weekday()
        try:
            return cls.objects.get(dia_semana=dia_semana)
        except cls.DoesNotExist:
            padrao = cls.padroes()[dia_semana]
            return cls.objects.create(**padrao)

    @classmethod
    def expediente_para_data(cls, data):
        if FechamentoFuncionamento.fechado_na_data(data):
            return None
        return cls.para_data(data)

    def clean(self):
        if (
            self.aberto
            and self.hora_abertura
            and self.hora_fechamento
            and self.hora_abertura >= self.hora_fechamento
        ):
            raise ValidationError(
                {
                    "hora_fechamento": (
                        "O horário de fechamento deve ser posterior ao horário "
                        "de abertura."
                    )
                }
            )

    def periodo_para_data(self, data):
        if not self.aberto:
            return None

        tz = timezone.get_current_timezone()
        abertura = timezone.make_aware(
            datetime.combine(data, self.hora_abertura),
            tz,
        )
        fechamento = timezone.make_aware(
            datetime.combine(data, self.hora_fechamento),
            tz,
        )
        return abertura, fechamento

    def contem_periodo(self, inicio, fim):
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.get_current_timezone())

        data_local = timezone.localtime(inicio).date()
        periodo = self.periodo_para_data(data_local)
        if periodo is None:
            return False

        abertura, fechamento = periodo
        return abertura <= inicio and fim <= fechamento


class FechamentoFuncionamento(models.Model):
    data = models.DateField("Data", unique=True)
    motivo = models.CharField("Motivo", max_length=120, blank=True, default="Feriado")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fechamento de funcionamento"
        verbose_name_plural = "Fechamentos de funcionamento"
        ordering = ["data"]

    def __str__(self):
        motivo = self.motivo or "Fechado"
        return f"{self.data:%d/%m/%Y} - {motivo}"

    @classmethod
    def fechado_na_data(cls, data):
        return cls.objects.filter(data=data).exists()

    @classmethod
    def datas_fechadas(cls, inicio=None, fim=None):
        fechamentos = cls.objects.all()
        if inicio:
            fechamentos = fechamentos.filter(data__gte=inicio)
        if fim:
            fechamentos = fechamentos.filter(data__lte=fim)
        return set(fechamentos.values_list("data", flat=True))


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

    @property
    def pode_ser_alterado(self):
        return self.status == self.STATUS_AGENDADO

    def clean(self):
        """Valida expediente da empresa e conflitos do mesmo profissional."""
        if not self.inicio or not self.servico_id or not self.profissional_id:
            return

        if self.status == self.STATUS_CANCELADO:
            return

        inicio = self.inicio
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
            self.inicio = inicio
        fim = self.fim

        if inicio < timezone.now() and not self.pk:
            raise ValidationError({"inicio": "Não é possível agendar em uma data/hora passada."})

        data_inicio = timezone.localtime(inicio).date()
        expediente = HorarioFuncionamento.expediente_para_data(data_inicio)
        if expediente is None or not expediente.contem_periodo(inicio, fim):
            raise ValidationError(
                {
                    "inicio": (
                        "O horário está fora do expediente de funcionamento da "
                        "empresa."
                    )
                }
            )

        conflitos = Agendamento.objects.filter(
            profissional=self.profissional,
        ).exclude(status=self.STATUS_CANCELADO)

        if self.pk:
            conflitos = conflitos.exclude(pk=self.pk)

        for outro in conflitos:
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

    def concluir(self):
        self.status = self.STATUS_CONCLUIDO
        self.save(update_fields=["status"])
