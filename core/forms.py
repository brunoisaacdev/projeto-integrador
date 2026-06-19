from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Agendamento, Cliente, Profissional, Servico


class BootstrapModelForm(forms.ModelForm):
    """Aplica classes Bootstrap automaticamente em todos os campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class ClienteForm(BootstrapModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "email", "telefone", "observacoes", "ativo"]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class ServicoForm(BootstrapModelForm):
    class Meta:
        model = Servico
        fields = ["nome", "descricao", "preco", "duracao_minutos", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }


class ProfissionalForm(BootstrapModelForm):
    class Meta:
        model = Profissional
        fields = ["nome", "especialidade", "telefone", "email", "servicos", "ativo"]
        widgets = {
            "servicos": forms.SelectMultiple(attrs={"size": 5}),
        }


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
        # Apenas registros ativos aparecem nas seleções
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["profissional"].queryset = Profissional.objects.filter(ativo=True)
        self.fields["servico"].queryset = Servico.objects.filter(ativo=True)

    def clean(self):
        cleaned = super().clean()
        # Dispara a validação de conflito definida no model
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
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )


class AgendamentoFiltroForm(forms.Form):
    """Filtro por data, cliente ou profissional."""

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


class UsuarioCadastroForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150, required=False)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail", required=False)
    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    is_staff = forms.BooleanField(
        label="Acesso administrativo",
        required=False,
        help_text="Permite acessar dashboard, serviços e profissionais.",
    )
    is_active = forms.BooleanField(label="Usuário ativo", required=False, initial=True)

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
            "is_staff",
            "is_active",
        ]

    def __init__(self, *args, allow_staff_fields=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_staff_fields:
            self.fields.pop("is_staff", None)
            self.fields.pop("is_active", None)

        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            else:
                widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            nome = user.get_full_name().strip() or user.username
            Cliente.objects.get_or_create(
                usuario=user,
                defaults={
                    "nome": nome,
                    "email": user.email,
                    "telefone": self.cleaned_data.get("telefone", ""),
                },
            )
        return user
