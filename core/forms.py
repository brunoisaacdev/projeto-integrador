from uuid import uuid4

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.models import Q

from .auth_utils import normalizar_telefone, contas_por_identificador
from .models import (
    Agendamento,
    Cliente,
    FechamentoFuncionamento,
    HorarioFuncionamento,
    Profissional,
    Servico,
)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class ClienteForm(BootstrapModelForm):
    password = forms.CharField(
        label="Senha",
        min_length=6,
        strip=False,
        widget=forms.PasswordInput,
        help_text="Use no mínimo 6 caracteres.",
    )
    is_staff = forms.BooleanField(
        label="Administrador",
        required=False,
        initial=False,
        help_text="Marcado: acesso completo. Desmarcado: somente agendamento.",
    )

    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "ativo"]

    def __init__(self, *args, allow_staff_fields=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["telefone"].required = True

        if self.instance.usuario_id:
            self.fields["is_staff"].initial = self.instance.usuario.is_staff
            self.fields["password"].required = False
            self.fields["password"].help_text = (
                "Deixe em branco para manter a senha atual ou informe ao menos 6 caracteres."
            )
        else:
            self.fields["password"].required = True

        if not allow_staff_fields:
            self.fields.pop("is_staff", None)
            self.fields.pop("ativo", None)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        clientes = Cliente.objects.filter(email__iexact=email)
        contas = get_user_model()._default_manager.filter(email__iexact=email)
        if self.instance.pk:
            clientes = clientes.exclude(pk=self.instance.pk)
        if self.instance.usuario_id:
            contas = contas.exclude(pk=self.instance.usuario_id)

        if clientes.exists() or contas.exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este e-mail.")
        return email

    def clean_telefone(self):
        telefone = self.cleaned_data["telefone"].strip()
        telefone_normalizado = normalizar_telefone(telefone)
        if not telefone_normalizado:
            raise forms.ValidationError("Informe um telefone válido.")

        for cliente in Cliente.objects.exclude(pk=self.instance.pk):
            if normalizar_telefone(cliente.telefone) == telefone_normalizado:
                raise forms.ValidationError(
                    "Já existe uma conta cadastrada com este telefone."
                )
        return telefone

    def _novo_username_interno(self):
        User = get_user_model()
        while True:
            username = f"cliente_{uuid4().hex}"
            if not User._default_manager.filter(username=username).exists():
                return username

    @transaction.atomic
    def save(self, commit=True):
        cliente = super().save(commit=False)
        usuario = cliente.usuario if cliente.usuario_id else None
        senha = self.cleaned_data.get("password")
        is_staff = self.cleaned_data.get("is_staff", False)
        ativo = self.cleaned_data.get("ativo", True)

        if usuario is None:
            usuario = get_user_model()(username=self._novo_username_interno())

        partes_nome = cliente.nome.strip().split(maxsplit=1)
        usuario.first_name = partes_nome[0] if partes_nome else ""
        usuario.last_name = partes_nome[1] if len(partes_nome) > 1 else ""
        usuario.email = cliente.email
        usuario.is_staff = is_staff
        usuario.is_active = ativo
        if senha:
            usuario.set_password(senha)

        if commit:
            usuario.save()
            cliente.usuario = usuario
            cliente.ativo = ativo
            cliente.save()

        return cliente


class ServicoForm(BootstrapModelForm):
    class Meta:
        model = Servico
        fields = ["nome", "descricao", "preco", "duracao_minutos", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class ProfissionalForm(BootstrapModelForm):
    servicos = forms.ModelMultipleChoiceField(
        label="Serviços realizados",
        queryset=Servico.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={"required": "Selecione ao menos um serviço."},
    )

    class Meta:
        model = Profissional
        fields = ["nome", "especialidade", "telefone", "email", "foto", "servicos", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        servicos = Servico.objects.filter(ativo=True)
        if self.instance.pk:
            servicos = Servico.objects.filter(
                Q(ativo=True) | Q(profissionais=self.instance)
            )
        self.fields["servicos"].queryset = servicos.distinct().order_by("nome")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            return email

        duplicados = Profissional.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise forms.ValidationError("Já existe um profissional cadastrado com este e-mail.")
        return email

    def clean_telefone(self):
        telefone = self.cleaned_data.get("telefone", "").strip()
        telefone_normalizado = normalizar_telefone(telefone)
        if not telefone_normalizado:
            return telefone

        for profissional in Profissional.objects.exclude(pk=self.instance.pk):
            if normalizar_telefone(profissional.telefone) == telefone_normalizado:
                raise forms.ValidationError(
                    "Já existe um profissional cadastrado com este telefone."
                )
        return telefone


class HorarioFuncionamentoForm(BootstrapModelForm):
    class Meta:
        model = HorarioFuncionamento
        fields = ["aberto", "hora_abertura", "hora_fechamento"]
        widgets = {
            "hora_abertura": forms.TimeInput(
                attrs={"type": "time"},
                format="%H:%M",
            ),
            "hora_fechamento": forms.TimeInput(
                attrs={"type": "time"},
                format="%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hora_abertura"].input_formats = ["%H:%M"]
        self.fields["hora_fechamento"].input_formats = ["%H:%M"]

    def clean(self):
        cleaned = super().clean()
        aberto = cleaned.get("aberto")
        abertura = cleaned.get("hora_abertura")
        fechamento = cleaned.get("hora_fechamento")
        if aberto and abertura and fechamento and abertura >= fechamento:
            raise forms.ValidationError(
                "O horário de fechamento deve ser posterior ao horário de abertura."
            )
        return cleaned


HorarioFuncionamentoFormSet = forms.modelformset_factory(
    HorarioFuncionamento,
    form=HorarioFuncionamentoForm,
    extra=0,
    can_delete=False,
)


class FechamentoFuncionamentoForm(BootstrapModelForm):
    class Meta:
        model = FechamentoFuncionamento
        fields = ["data", "motivo"]
        error_messages = {
            "data": {
                "unique": "Esta data já foi cadastrada como dia fechado.",
            },
        }
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data"].input_formats = ["%Y-%m-%d"]


class AgendamentoForm(BootstrapModelForm):
    class Meta:
        model = Agendamento
        fields = ["cliente", "profissional", "servico", "inicio", "observacoes"]
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["profissional"].queryset = Profissional.objects.filter(ativo=True)
        self.fields["servico"].queryset = Servico.objects.filter(ativo=True)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        instance.cliente = cleaned.get("cliente")
        instance.profissional = cleaned.get("profissional")
        instance.servico = cleaned.get("servico")
        instance.inicio = cleaned.get("inicio")
        instance.clean()
        return cleaned


class AgendamentoClienteForm(BootstrapModelForm):
    class Meta:
        model = Agendamento
        fields = ["profissional", "servico", "inicio", "observacoes"]
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, cliente=None, **kwargs):
        self.cliente = cliente
        super().__init__(*args, **kwargs)
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["profissional"].queryset = Profissional.objects.filter(ativo=True)
        self.fields["servico"].queryset = Servico.objects.filter(ativo=True)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        instance.cliente = self.cliente
        instance.profissional = cleaned.get("profissional")
        instance.servico = cleaned.get("servico")
        instance.inicio = cleaned.get("inicio")
        instance.clean()
        return cleaned

    def save(self, commit=True):
        agendamento = super().save(commit=False)
        agendamento.cliente = self.cliente
        if commit:
            agendamento.save()
        return agendamento


class CancelamentoForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo do cancelamento",
        max_length=255,
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Informe o motivo do cancelamento",
            }
        ),
    )


class AgendamentoFiltroForm(forms.Form):
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=False,
        empty_label="Todos os clientes",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    profissional = forms.ModelChoiceField(
        queryset=Profissional.objects.all(),
        required=False,
        empty_label="Todos os profissionais",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=[("", "Todos os status")] + Agendamento.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class ClienteCadastroForm(ClienteForm):
    def __init__(self, *args, allow_staff_fields=False, **kwargs):
        super().__init__(
            *args,
            allow_staff_fields=allow_staff_fields,
            **kwargs,
        )


class SistemaAuthenticationForm(forms.Form):
    identificador = forms.CharField(
        label="E-mail ou telefone",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "E-mail ou telefone",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        "invalid_login": (
            "E-mail, telefone ou senha inválidos. Verifique os dados informados."
        ),
        "inactive": "Este cliente está inativo. Entre em contato com o administrador.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identificador = cleaned_data.get("identificador")
        password = cleaned_data.get("password")

        if identificador and password:
            self.user_cache = authenticate(
                self.request,
                username=identificador,
                password=password,
            )

            if self.user_cache is None:
                for conta in contas_por_identificador(identificador):
                    if not conta.is_active and conta.check_password(password):
                        raise forms.ValidationError(
                            self.error_messages["inactive"],
                            code="inactive",
                        )
                raise forms.ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                )

        return cleaned_data

    def get_user(self):
        return self.user_cache
