import calendar
import logging
import threading
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.db import close_old_connections, transaction
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import (
    AgendamentoFiltroForm,
    AgendamentoClienteForm,
    AgendamentoForm,
    CancelamentoForm,
    ClienteForm,
    FechamentoFuncionamentoForm,
    ProfissionalForm,
    ServicoForm,
    SistemaAuthenticationForm,
    ClienteCadastroForm,
    HorarioFuncionamentoFormSet,
)
from .models import (
    Agendamento,
    Cliente,
    FechamentoFuncionamento,
    HorarioFuncionamento,
    Profissional,
    Servico,
)


INTERVALO_GRADE = timedelta(minutes=30)
DIAS_SEMANA_CALENDARIO = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]
MESES_PT = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
logger = logging.getLogger(__name__)


def is_staff(user):
    return user.is_active and user.is_staff


staff_required = user_passes_test(is_staff, login_url="login")


def horarios_padrao():
    inicio = datetime.combine(timezone.localdate(), time(hour=8))
    return [
        (inicio + timedelta(minutes=30 * indice)).strftime("%H:%M")
        for indice in range(22)
    ]


def cliente_do_usuario(user):
    try:
        return user.cliente
    except Cliente.DoesNotExist:
        nome = user.get_full_name().strip() or user.email or "Cliente"
        cliente = None
        if user.email:
            cliente = Cliente.objects.filter(
                usuario__isnull=True,
                email__iexact=user.email,
            ).first()

        if cliente is None:
            cliente = Cliente.objects.create(
                usuario=user,
                nome=nome,
                email=user.email,
                telefone="",
                ativo=True,
            )
        else:
            cliente.usuario = user
            cliente.ativo = True
            if not cliente.nome:  
                cliente.nome = nome
            if not cliente.email and user.email:
                cliente.email = user.email
            cliente.save(update_fields=["usuario", "ativo", "nome", "email"])

        return cliente


def enviar_email_confirmacao_agendamento(agendamento):
    email = agendamento.cliente.email
    if not email:
        return False

    inicio = timezone.localtime(agendamento.inicio)
    fim = timezone.localtime(agendamento.fim)
    observacoes = agendamento.observacoes.strip() if agendamento.observacoes else ""
    linhas = [
        f"Ola, {agendamento.cliente.nome}.",
        "",
        "Seu agendamento foi confirmado na Premium Barbearia.",
        "",
        f"Codigo: #{agendamento.pk}",
        f"Servico: {agendamento.servico.nome}",
        f"Profissional: {agendamento.profissional.nome}",
        f"Data: {inicio:%d/%m/%Y}",
        f"Horario: {inicio:%H:%M} - {fim:%H:%M}",
        f"Valor: R$ {agendamento.servico.preco:.2f}",
    ]
    if observacoes:
        linhas.extend(["", f"Observacoes: {observacoes}"])
    linhas.extend(
        [
            "",
            "Para acompanhar ou cancelar seus horarios, acesse a area Meus agendamentos.",
            "",
            "𝗙𝗲𝗶𝘁𝗼 𝗽𝗼𝗿 𝗜𝗦𝗔𝗔𝗖 𝗠𝗗𝗠 𝗲 𝗚𝗨𝗜𝗟𝗛𝗘𝗥𝗠𝗘 𝗗𝗢 𝗔𝗜𝗥𝗦𝗢𝗙𝗧",
        ]
    )

    try:
        send_mail(
            "Agendamento confirmado - Premium Barbearia",
            "\n".join(linhas),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail do agendamento %s.", agendamento.pk)
        return False
    return True


def enviar_email_confirmacao_agendamento_async(agendamento):
    if not agendamento.cliente.email:
        return False

    def tarefa():
        close_old_connections()
        try:
            agendamento_atualizado = Agendamento.objects.select_related(
                "cliente",
                "profissional",
                "servico",
            ).get(pk=agendamento.pk)
            enviar_email_confirmacao_agendamento(agendamento_atualizado)
        except Agendamento.DoesNotExist:
            logger.warning(
                "Agendamento %s nao encontrado para envio de e-mail.",
                agendamento.pk,
            )
        finally:
            close_old_connections()

    transaction.on_commit(
        lambda: threading.Thread(target=tarefa, daemon=True).start()
    )
    return True


def enviar_email_conclusao_agendamento(agendamento):
    email = agendamento.cliente.email
    if not email:
        return False

    inicio = timezone.localtime(agendamento.inicio)
    fim = timezone.localtime(agendamento.fim)
    linhas = [
        f"Ola, {agendamento.cliente.nome}.",
        "",
        "Seu atendimento na Premium Barbearia foi concluido.",
        "",
        f"Codigo: #{agendamento.pk}",
        f"Servico: {agendamento.servico.nome}",
        f"Profissional: {agendamento.profissional.nome}",
        f"Data: {inicio:%d/%m/%Y}",
        f"Horario: {inicio:%H:%M} - {fim:%H:%M}",
        f"Valor: R$ {agendamento.servico.preco:.2f}",
        "",
        "Obrigado pela preferencia.",
        "",
        "𝗙𝗲𝗶𝘁𝗼 𝗽𝗼𝗿 𝗜𝗦𝗔𝗔𝗖 𝗠𝗗𝗠 𝗲 𝗚𝗨𝗜𝗟𝗛𝗘𝗥𝗠𝗘 𝗗𝗢 𝗔𝗜𝗥𝗦𝗢𝗙𝗧",
    ]

    try:
        send_mail(
            "Atendimento concluido - Premium Barbearia",
            "\n".join(linhas),
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Falha ao enviar e-mail de conclusao do agendamento %s.",
            agendamento.pk,
        )
        return False
    return True


def enviar_email_conclusao_agendamento_async(agendamento):
    if not agendamento.cliente.email:
        return False

    def tarefa():
        close_old_connections()
        try:
            agendamento_atualizado = Agendamento.objects.select_related(
                "cliente",
                "profissional",
                "servico",
            ).get(pk=agendamento.pk)
            enviar_email_conclusao_agendamento(agendamento_atualizado)
        except Agendamento.DoesNotExist:
            logger.warning(
                "Agendamento %s nao encontrado para envio de e-mail de conclusao.",
                agendamento.pk,
            )
        finally:
            close_old_connections()

    transaction.on_commit(
        lambda: threading.Thread(target=tarefa, daemon=True).start()
    )
    return True


def profissionais_disponiveis_para(servico):
    if servico is None:
        return Profissional.objects.none()

    return (
        Profissional.objects.filter(ativo=True, servicos=servico)
        .distinct()
        .order_by("nome")
    )


def intervalo_livre(inicio, fim, agendamentos_ocupados):
    for agendamento in agendamentos_ocupados:
        if inicio < agendamento.fim and agendamento.inicio < fim:
            return False
    return True


def expediente_para_frontend():
    HorarioFuncionamento.garantir_padrao()
    expediente = {
        str(horario.dia_semana): {
            "aberto": horario.aberto,
            "abertura": horario.hora_abertura.strftime("%H:%M"),
            "fechamento": horario.hora_fechamento.strftime("%H:%M"),
        }
        for horario in HorarioFuncionamento.objects.all()
    }
    expediente["fechamentos"] = [
        fechamento.data.isoformat()
        for fechamento in FechamentoFuncionamento.objects.order_by("data")
    ]
    return expediente


def expedientes_por_dia():
    HorarioFuncionamento.garantir_padrao()
    return {
        horario.dia_semana: horario
        for horario in HorarioFuncionamento.objects.all()
    }


def fechamentos_no_periodo(inicio, fim):
    return FechamentoFuncionamento.datas_fechadas(inicio, fim)


def duracoes_servicos_para_frontend():
    return {
        str(servico.pk): servico.duracao_minutos
        for servico in Servico.objects.filter(ativo=True)
    }


def horarios_livres(
    servico,
    profissional,
    data,
    agendamento_id=None,
    expedientes=None,
    fechamentos=None,
):
    if not servico or not profissional or not data:
        return []

    if fechamentos is not None:
        if data in fechamentos:
            return []
    elif FechamentoFuncionamento.fechado_na_data(data):
        return []

    expediente = (
        expedientes.get(data.weekday())
        if expedientes is not None
        else HorarioFuncionamento.expediente_para_data(data)
    )
    if expediente is None:
        return []
    periodo = expediente.periodo_para_data(data)
    if periodo is None:
        return []

    abertura, fechamento = periodo
    duracao = timedelta(minutes=servico.duracao_minutos)
    agora = timezone.now()
    ocupados = (
        Agendamento.objects.select_related("servico")
        .filter(profissional=profissional, inicio__date=data)
        .exclude(status=Agendamento.STATUS_CANCELADO)
    )
    if agendamento_id:
        ocupados = ocupados.exclude(pk=agendamento_id)

    horarios = []
    atual = abertura
    while atual + duracao <= fechamento:
        fim = atual + duracao
        if atual > agora and intervalo_livre(atual, fim, ocupados):
            horarios.append(
                {
                    "value": timezone.localtime(atual).strftime("%H:%M"),
                    "label": timezone.localtime(atual).strftime("%H:%M"),
                }
            )
        atual += INTERVALO_GRADE
    return horarios


def datas_livres(servico, profissional, dias=30):
    hoje = timezone.localdate()
    expedientes = expedientes_por_dia()
    fechamentos = fechamentos_no_periodo(hoje, hoje + timedelta(days=dias))
    datas = []
    for indice in range(dias):
        data = hoje + timedelta(days=indice)
        if horarios_livres(
            servico,
            profissional,
            data,
            expedientes=expedientes,
            fechamentos=fechamentos,
        ):
            datas.append(
                {
                    "value": data.isoformat(),
                    "label": data.strftime("%d/%m/%Y"),
                }
            )
    return datas


def primeiro_dia_mes(data):
    return data.replace(day=1)


def adicionar_meses(data, quantidade):
    mes = data.month - 1 + quantidade
    ano = data.year + mes // 12
    mes = mes % 12 + 1
    return data.replace(year=ano, month=mes, day=1)


def mes_por_parametro(valor):
    if not valor:
        return None

    data = parse_date(f"{valor}-01") if len(valor) == 7 else parse_date(valor)
    return primeiro_dia_mes(data) if data else None


def nome_mes(data):
    return f"{MESES_PT[data.month - 1].capitalize()} de {data.year}"


def calendario_disponibilidade(servico, profissional, mes_base):
    mes_base = primeiro_dia_mes(mes_base or timezone.localdate())
    hoje = timezone.localdate()
    primeiro_dia_semana = (mes_base.weekday() + 1) % 7
    total_dias = calendar.monthrange(mes_base.year, mes_base.month)[1]
    expedientes = expedientes_por_dia()
    primeiro_dia = mes_base
    ultimo_dia = mes_base.replace(day=total_dias)
    fechamentos = fechamentos_no_periodo(primeiro_dia, ultimo_dia)

    dias = [{"empty": True} for _ in range(primeiro_dia_semana)]
    for numero_dia in range(1, total_dias + 1):
        data = mes_base.replace(day=numero_dia)
        disponivel = bool(
            horarios_livres(
                servico,
                profissional,
                data,
                expedientes=expedientes,
                fechamentos=fechamentos,
            )
        )
        dias.append(
            {
                "empty": False,
                "value": data.isoformat(),
                "label": data.strftime("%d/%m/%Y"),
                "dia": numero_dia,
                "disponivel": disponivel,
                "hoje": data == hoje,
                "passado": data < hoje,
            }
        )

    while len(dias) % 7:
        dias.append({"empty": True})

    return dias


def selecionar_por_id(queryset, pk):
    if pk:
        objeto = queryset.filter(pk=pk).first()
        if objeto:
            return objeto
    return queryset.first()


@login_required
def agendar(request):
    cliente = cliente_do_usuario(request.user)

    sucesso_id = request.GET.get("sucesso")
    if request.method == "GET" and sucesso_id:
        if not sucesso_id.isdigit():
            return redirect("agendar")
        agendamento = get_object_or_404(
            Agendamento.objects.select_related(
                "cliente",
                "profissional",
                "servico",
            ),
            pk=sucesso_id,
            cliente=cliente,
        )
        return render(
            request,
            "core/agendamento_sucesso.html",
            {"agendamento": agendamento},
        )

    dados = request.POST if request.method == "POST" else request.GET
    servicos = Servico.objects.filter(ativo=True).order_by("nome")
    servico = selecionar_por_id(servicos, dados.get("servico"))
    profissionais = profissionais_disponiveis_para(servico)
    profissional = selecionar_por_id(
        profissionais,
        dados.get("profissional"),
    )

    data_param = dados.get("data")
    data_informada = parse_date(data_param) if data_param else None
    mes_base = mes_por_parametro(dados.get("mes"))
    if data_informada:
        mes_base = primeiro_dia_mes(data_informada)
    if mes_base is None:
        mes_base = primeiro_dia_mes(timezone.localdate())

    calendario = calendario_disponibilidade(servico, profissional, mes_base)
    datas = [dia for dia in calendario if not dia.get("empty") and dia["disponivel"]]
    datas_values = {item["value"] for item in datas}
    data_informada_disponivel = (
        data_informada and data_informada.isoformat() in datas_values
    )
    if data_informada_disponivel:
        data_selecionada = data_informada
    else:
        data_selecionada = parse_date(datas[0]["value"]) if datas else None

    horarios = horarios_livres(servico, profissional, data_selecionada)
    horario_selecionado = request.POST.get("horario") or (
        horarios[0]["value"] if horarios else ""
    )

    form = AgendamentoClienteForm(cliente=cliente)
    if request.method == "POST":
        post_data = request.POST.copy()
        if servico:
            post_data["servico"] = str(servico.pk)
        if profissional:
            post_data["profissional"] = str(profissional.pk)
        horarios_post = (
            horarios_livres(servico, profissional, data_informada)
            if data_informada_disponivel
            else []
        )
        if data_informada_disponivel and request.POST.get("horario"):
            post_data["inicio"] = f"{data_informada.isoformat()}T{request.POST['horario']}"

        form = AgendamentoClienteForm(post_data, cliente=cliente)
        horario_valido = request.POST.get("horario") in {
            item["value"] for item in horarios_post
        }
        if form.is_valid() and horario_valido:
            agendamento = form.save()
            if enviar_email_confirmacao_agendamento_async(agendamento):
                messages.success(request, "Enviaremos os detalhes do agendamento por e-mail.")
            else:
                messages.warning(
                    request,
                    "Agendamento confirmado, mas o cliente não possui e-mail cadastrado.",
                )
            return redirect(f'{reverse("agendar")}?sucesso={agendamento.pk}')
        if not horario_valido:
            form.add_error(
                "inicio",
                "O horário está fora do expediente ou indisponível para essa data.",
            )
        messages.error(request, "Revise os dados do agendamento.")

    mes_atual_sistema = primeiro_dia_mes(timezone.localdate())
    mes_anterior = adicionar_meses(mes_base, -1) if mes_base > mes_atual_sistema else None
    mes_proximo = adicionar_meses(mes_base, 1)

    return render(
        request,
        "core/agendar.html",
        {
            "calendario": calendario,
            "cliente": cliente,
            "data_selecionada_value": data_selecionada.isoformat()
            if data_selecionada
            else "",
            "datas": datas,
            "data_selecionada": data_selecionada,
            "dias_semana": DIAS_SEMANA_CALENDARIO,
            "form": form,
            "horario_selecionado": horario_selecionado,
            "horarios": horarios,
            "horarios_validos": [item["value"] for item in horarios],
            "mes_anterior": mes_anterior.strftime("%Y-%m") if mes_anterior else "",
            "mes_atual": mes_base.strftime("%Y-%m"),
            "mes_label": nome_mes(mes_base),
            "mes_proximo": mes_proximo.strftime("%Y-%m"),
            "profissionais": profissionais,
            "profissional_selecionado": profissional,
            "servico_selecionado": servico,
            "servicos": servicos,
        },
    )


@login_required
def meus_agendamentos(request):
    cliente = cliente_do_usuario(request.user)
    agora = timezone.now()
    todos = Agendamento.objects.select_related(
        "profissional",
        "servico",
    ).filter(cliente=cliente)

    total_proximos = todos.filter(
        status=Agendamento.STATUS_AGENDADO,
        inicio__gte=agora,
    ).count()
    total_concluidos = todos.filter(
        status=Agendamento.STATUS_CONCLUIDO,
    ).count()
    total_cancelados = todos.filter(
        status=Agendamento.STATUS_CANCELADO,
    ).count()

    filtro_status = request.GET.get("status", "todos")
    if filtro_status == "proximos":
        agendamentos = todos.filter(
            status=Agendamento.STATUS_AGENDADO,
            inicio__gte=agora,
        ).order_by("inicio")
    elif filtro_status == "concluidos":
        agendamentos = todos.filter(
            status=Agendamento.STATUS_CONCLUIDO,
        ).order_by("-inicio")
    elif filtro_status == "cancelados":
        agendamentos = todos.filter(
            status=Agendamento.STATUS_CANCELADO,
        ).order_by("-inicio")
    else:
        filtro_status = "todos"
        agendamentos = todos.order_by("-inicio")

    return render(
        request,
        "core/meus_agendamentos.html",
        {
            "agendamentos": agendamentos,
            "agora": agora,
            "cliente": cliente,
            "filtro_status": filtro_status,
            "total_cancelados": total_cancelados,
            "total_concluidos": total_concluidos,
            "total_proximos": total_proximos,
        },
    )


@login_required
def cancelar_meu_agendamento(request, pk):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    cliente = cliente_do_usuario(request.user)
    agendamento = get_object_or_404(
        Agendamento,
        pk=pk,
        cliente=cliente,
    )

    if agendamento.status != Agendamento.STATUS_AGENDADO:
        messages.info(request, "Somente agendamentos ativos podem ser cancelados.")
        return redirect("meus_agendamentos")

    if agendamento.inicio <= timezone.now():
        messages.error(
            request,
            "Não é possível cancelar um agendamento que já passou da data e hora marcadas.",
        )
        return redirect("meus_agendamentos")

    form = CancelamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        agendamento.cancelar(form.cleaned_data["motivo"])
        messages.warning(request, "Agendamento cancelado com sucesso.")
        return redirect("meus_agendamentos")

    return render(
        request,
        "core/meu_agendamento_cancelar.html",
        {"form": form, "agendamento": agendamento},
    )


class SistemaLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = SistemaAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        user = self.request.user

        staff_only_paths = (
            reverse("dashboard"),
            reverse("agendamento_list"),
            reverse("horario_funcionamento"),
            reverse("servico_list"),
            reverse("profissional_list"),
        )
        if redirect_to and (
            user.is_staff or not redirect_to.startswith(staff_only_paths)
        ):
            return redirect_to

        if user.is_staff:
            return reverse_lazy("dashboard")
        return reverse_lazy("agendar")


def cliente_cadastro(request):
    allow_staff_fields = request.user.is_authenticated and request.user.is_staff
    form = ClienteCadastroForm(
        request.POST or None,
        allow_staff_fields=allow_staff_fields,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cliente cadastrado com sucesso.")
        if allow_staff_fields:
            return redirect("dashboard")
        return redirect("login")

    return render(
        request,
        "core/cliente_cadastro.html",
        {"form": form, "allow_staff_fields": allow_staff_fields},
    )


@login_required
@staff_required
def dashboard(request):
    hoje = timezone.localdate()
    data_param = request.GET.get("data")
    data_selecionada = parse_date(data_param) if data_param else hoje
    if data_selecionada is None:
        data_selecionada = hoje

    data_anterior = data_selecionada - timedelta(days=1)
    data_proxima = data_selecionada + timedelta(days=1)
    if data_selecionada == hoje:
        data_referencia = "hoje"
    elif data_selecionada == hoje - timedelta(days=1):
        data_referencia = "ontem"
    elif data_selecionada == hoje + timedelta(days=1):
        data_referencia = "amanhã"
    else:
        data_referencia = data_selecionada.strftime("%d/%m/%Y")

    agendamentos_hoje = (
        Agendamento.objects.select_related("cliente", "servico", "profissional")
        .filter(inicio__date=data_selecionada)
        .exclude(status=Agendamento.STATUS_CANCELADO)
        .order_by("inicio")
    )
    ranking_profissionais = list(
        Profissional.objects.annotate(
            qtd=Count(
                "agendamentos",
                filter=~Q(agendamentos__status=Agendamento.STATUS_CANCELADO),
            )
        )
        .order_by("-qtd", "nome")[:5]
    )
    maior_quantidade = ranking_profissionais[0].qtd if ranking_profissionais else 0
    for profissional in ranking_profissionais:
        profissional.percentual_grafico = (
            max(8, round(profissional.qtd * 100 / maior_quantidade))
            if profissional.qtd and maior_quantidade
            else 0
        )

    ranking_servicos = list(
        Servico.objects.annotate(
            qtd=Count(
                "agendamentos",
                filter=~Q(agendamentos__status=Agendamento.STATUS_CANCELADO),
            )
        )
        .filter(qtd__gt=0)
        .order_by("-qtd", "nome")[:5]
    )
    total_ranking_servicos = sum(servico.qtd for servico in ranking_servicos)
    cores_grafico = ["#7c3aed", "#3b82f6", "#22c55e", "#f59e0b", "#ec4899"]
    fatias_grafico = []
    inicio_fatia = 0
    for indice, servico in enumerate(ranking_servicos):
        percentual = servico.qtd * 100 / total_ranking_servicos
        fim_fatia = (
            100
            if indice == len(ranking_servicos) - 1
            else inicio_fatia + percentual
        )
        servico.cor_grafico = cores_grafico[indice]
        servico.percentual_grafico = round(percentual, 1)
        fatias_grafico.append(
            f"{servico.cor_grafico} {inicio_fatia:.2f}% {fim_fatia:.2f}%"
        )
        inicio_fatia = fim_fatia

    contexto = {
        "total_clientes": Cliente.objects.filter(ativo=True).count(),
        "total_servicos": Servico.objects.filter(ativo=True).count(),
        "total_profissionais": Profissional.objects.filter(ativo=True).count(),
        "total_agendados": Agendamento.objects.filter(
            status=Agendamento.STATUS_AGENDADO
        ).count(),
        "agendamentos_hoje": agendamentos_hoje,
        "data_anterior": data_anterior.isoformat(),
        "data_proxima": data_proxima.isoformat(),
        "data_referencia": data_referencia,
        "data_selecionada": data_selecionada,
        "data_selecionada_iso": data_selecionada.isoformat(),
        "qtd_hoje": agendamentos_hoje.count(),
        "faturamento_previsto": agendamentos_hoje.aggregate(
            total=Sum("servico__preco")
        )["total"]
        or 0,
        "ranking_profissionais": ranking_profissionais,
        "ranking_servicos": ranking_servicos,
        "total_ranking_servicos": total_ranking_servicos,
        "grafico_servicos_css": f"conic-gradient({', '.join(fatias_grafico)})",
    }
    return render(request, "core/dashboard.html", contexto)


@login_required
def cliente_list(request):
    busca = request.GET.get("q", "").strip()
    clientes = Cliente.objects.all()
    if busca:
        clientes = clientes.filter(
            Q(nome__icontains=busca) | Q(telefone__icontains=busca) | Q(email__icontains=busca)
        )
    return render(request, "core/clientes.html", {"clientes": clientes, "busca": busca})


@login_required
def cliente_form(request, pk=None):
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None
    form = ClienteForm(
        request.POST or None,
        instance=cliente,
        allow_staff_fields=True,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cliente salvo com sucesso.")
        return redirect("cliente_list")
    return render(request, "core/cliente_form.html", {"form": form, "cliente": cliente})


@login_required
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        conta = cliente.usuario if cliente.usuario_id else None
        try:
            with transaction.atomic():
                cliente.delete()
                if conta:
                    conta.delete()
        except ProtectedError:
            messages.error(
                request,
                "Não é possível excluir este cliente porque existem agendamentos vinculados. "
                "Inative o cliente para bloquear o acesso sem perder o histórico.",
            )
        else:
            messages.success(request, "Cliente removido.")
        return redirect("cliente_list")
    return render(
        request,
        "core/confirmar_exclusao.html",
        {"obj": cliente, "tipo": "cliente", "cancel_url": "cliente_list"},
    )


@login_required
@staff_required
def servico_list(request):
    servicos = Servico.objects.all()
    return render(request, "core/servicos.html", {"servicos": servicos})


@login_required
@staff_required
def servico_form(request, pk=None):
    servico = get_object_or_404(Servico, pk=pk) if pk else None
    form = ServicoForm(request.POST or None, instance=servico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço salvo com sucesso.")
        return redirect("servico_list")
    return render(request, "core/servico_form.html", {"form": form, "servico": servico})


@login_required
@staff_required
def servico_delete(request, pk):
    servico = get_object_or_404(Servico, pk=pk)
    if request.method == "POST":
        removido = False
        try:
            servico.delete()
            removido = True
        except ProtectedError:
            messages.error(
                request,
                "Não é possível excluir este serviço porque existem agendamentos vinculados. "
                "Inative o serviço para manter o histórico.",
            )
        if removido:
            messages.success(request, "Serviço removido.")
        return redirect("servico_list")
    return render(
        request,
        "core/confirmar_exclusao.html",
        {"obj": servico, "tipo": "serviço", "cancel_url": "servico_list"},
    )


@login_required
@staff_required
def profissional_list(request):
    profissionais = Profissional.objects.all()
    return render(
        request, "core/profissionais.html", {"profissionais": profissionais}
    )


@login_required
@staff_required
def profissional_form(request, pk=None):
    profissional = get_object_or_404(Profissional, pk=pk) if pk else None
    form = ProfissionalForm(
        request.POST or None,
        request.FILES or None,
        instance=profissional,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profissional salvo com sucesso.")
        return redirect("profissional_list")
    return render(
        request,
        "core/profissional_form.html",
        {"form": form, "profissional": profissional},
    )


@login_required
@staff_required
def profissional_delete(request, pk):
    profissional = get_object_or_404(Profissional, pk=pk)
    if request.method == "POST":
        removido = False
        try:
            profissional.delete()
            removido = True
        except ProtectedError:
            messages.error(
                request,
                "Não é possível excluir este profissional porque existem agendamentos vinculados. "
                "Inative o profissional para manter o histórico.",
            )
        if removido:
            messages.success(request, "Profissional removido.")
        return redirect("profissional_list")
    return render(
        request,
        "core/confirmar_exclusao.html",
        {"obj": profissional, "tipo": "profissional", "cancel_url": "profissional_list"},
    )


@login_required
@staff_required
def horario_funcionamento(request):
    HorarioFuncionamento.garantir_padrao()
    queryset = HorarioFuncionamento.objects.all()
    acao = (
        request.POST.get("action", "save_hours")
        if request.method == "POST"
        else None
    )
    formset = HorarioFuncionamentoFormSet(
        request.POST if acao == "save_hours" else None,
        queryset=queryset,
    )
    fechamento_form = FechamentoFuncionamentoForm(
        request.POST if acao == "add_closure" else None,
    )

    if request.method == "POST":
        if acao == "add_closure":
            if fechamento_form.is_valid():
                fechamento_form.save()
                messages.success(request, "Dia fechado cadastrado com sucesso.")
                return redirect("horario_funcionamento")
        elif acao == "delete_closure":
            fechamento = get_object_or_404(
                FechamentoFuncionamento,
                pk=request.POST.get("fechamento_id"),
            )
            fechamento.delete()
            messages.success(request, "Dia fechado removido.")
            return redirect("horario_funcionamento")
        elif formset.is_valid():
            formset.save()
            messages.success(request, "Horários de funcionamento salvos com sucesso.")
            return redirect("horario_funcionamento")

    return render(
        request,
        "core/horarios_funcionamento.html",
        {
            "fechamento_form": fechamento_form,
            "fechamentos": FechamentoFuncionamento.objects.order_by("data"),
            "formset": formset,
        },
    )


@login_required
@staff_required
def agendamento_list(request):
    filtro = AgendamentoFiltroForm(request.GET or None)
    agendamentos = Agendamento.objects.select_related(
        "cliente", "profissional", "servico"
    )

    if filtro.is_valid():
        data = filtro.cleaned_data.get("data")
        cliente = filtro.cleaned_data.get("cliente")
        profissional = filtro.cleaned_data.get("profissional")
        status = filtro.cleaned_data.get("status")
        if data:
            agendamentos = agendamentos.filter(inicio__date=data)
        if cliente:
            agendamentos = agendamentos.filter(cliente=cliente)
        if profissional:
            agendamentos = agendamentos.filter(profissional=profissional)
        if status:
            agendamentos = agendamentos.filter(status=status)

    clientes = Cliente.objects.order_by("nome")
    profissionais = Profissional.objects.order_by("nome")

    return render(
        request,
        "core/agendamentos.html",
        {
            "agendamentos": agendamentos.order_by("-inicio"),
            "clientes": clientes,
            "filtro": filtro,
            "profissionais": profissionais,
            "status_choices": Agendamento.STATUS_CHOICES,
        },
    )


@login_required
def agendamento_form(request, pk=None):
    agendamento = get_object_or_404(Agendamento, pk=pk) if pk else None
    if agendamento and not agendamento.pode_ser_alterado:
        messages.info(
            request,
            "Agendamentos concluídos ou cancelados não podem ser editados.",
        )
        return redirect("agendamento_list")

    form = AgendamentoForm(request.POST or None, instance=agendamento)
    if request.method == "POST" and form.is_valid():
        novo_agendamento = agendamento is None
        agendamento_salvo = form.save()
        if novo_agendamento:
            if enviar_email_confirmacao_agendamento_async(agendamento_salvo):
                messages.success(request, "E-mail de confirmação será enviado ao cliente.")
            else:
                messages.warning(
                    request,
                    "Agendamento salvo, mas o cliente não possui e-mail cadastrado.",
                )
        messages.success(request, "Agendamento salvo com sucesso.")
        return redirect("agendamento_list")
    return render(
        request,
        "core/agendamento_form.html",
        {
            "form": form,
            "agendamento": agendamento,
            "expediente_frontend": expediente_para_frontend(),
            "duracoes_servicos": duracoes_servicos_para_frontend(),
        },
    )


@login_required
def agendamento_cancelar(request, pk):
    agendamento = get_object_or_404(
        Agendamento.objects.select_related("cliente", "profissional", "servico"),
        pk=pk,
    )
    if not agendamento.pode_ser_alterado:
        messages.info(
            request,
            "Agendamentos concluídos ou cancelados não podem ser cancelados.",
        )
        return redirect("agendamento_list")

    form = CancelamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        agendamento.cancelar(motivo=form.cleaned_data.get("motivo", ""))
        messages.warning(request, "Agendamento cancelado.")
        return redirect("agendamento_list")
    return render(
        request,
        "core/agendamento_cancelar.html",
        {"form": form, "agendamento": agendamento},
    )


@login_required
@staff_required
def agendamento_concluir(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    agendamento = get_object_or_404(
        Agendamento.objects.select_related("cliente", "profissional", "servico"),
        pk=pk,
    )
    if agendamento.status == Agendamento.STATUS_AGENDADO:
        agendamento.concluir()
        if enviar_email_conclusao_agendamento_async(agendamento):
            messages.success(
                request,
                "Atendimento marcado como concluído. E-mail será enviado ao cliente.",
            )
        else:
            messages.warning(
                request,
                "Atendimento marcado como concluído, mas o cliente não possui e-mail cadastrado.",
            )
    else:
        messages.info(request, "Somente atendimentos agendados podem ser concluídos.")
    return redirect("agendamento_list")

