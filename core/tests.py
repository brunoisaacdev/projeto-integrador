import shutil
import tempfile
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Agendamento, Cliente, HorarioFuncionamento, Profissional, Servico


TEST_MEDIA_ROOT = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CorePageSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="admin",
            password="admin123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.user)

        self.cliente = Cliente.objects.create(
            usuario=self.user,
            nome="Joao Mendes",
            email="joao@example.com",
            telefone="11999999999",
        )
        self.servico = Servico.objects.create(
            nome="Corte",
            preco="50.00",
            duracao_minutos=30,
        )
        self.profissional = Profissional.objects.create(
            nome="Carlos",
            especialidade="Cortes classicos",
        )
        self.profissional.servicos.add(self.servico)
        self.agendamento = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.now() + timedelta(days=1),
        )

    def future_date_for_weekday(self, weekday, minimum_days=10):
        data = timezone.localdate() + timedelta(days=minimum_days)
        while data.weekday() != weekday:
            data += timedelta(days=1)
        return data

    def test_login_page_renders(self):
        self.client.logout()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("cliente_cadastro"))

    def test_cliente_cadastro_creates_regular_user_and_cliente(self):
        self.client.logout()

        response = self.client.post(
            reverse("cliente_cadastro"),
            {
                "nome": "Maria Recepcao",
                "email": "recepcao@example.com",
                "telefone": "11888888888",
                "password": "123456",
            },
        )

        self.assertRedirects(response, reverse("login"))
        User = get_user_model()
        user = User.objects.get(email="recepcao@example.com")
        self.assertTrue(user.username.startswith("cliente_"))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.cliente.nome, "Maria Recepcao")
        self.assertEqual(user.cliente.telefone, "11888888888")
        self.assertTrue(user.check_password("123456"))

    def test_admin_can_create_active_admin_user_with_checkboxes(self):
        response = self.client.get(reverse("cliente_cadastro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_staff"')
        self.assertContains(response, 'name="ativo"')
        self.assertNotContains(response, 'name="username"')

        response = self.client.post(
            reverse("cliente_cadastro"),
            {
                "nome": "Novo Admin",
                "email": "novo.admin@example.com",
                "telefone": "11777777777",
                "password": "123456",
                "is_staff": "on",
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        User = get_user_model()
        novo_admin = User.objects.get(email="novo.admin@example.com")
        self.assertTrue(novo_admin.is_staff)
        self.assertTrue(novo_admin.is_active)

    def test_new_client_admin_checkbox_starts_unchecked(self):
        response = self.client.get(reverse("cliente_novo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="nome"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="telefone"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="ativo"')
        self.assertContains(response, 'name="is_staff"')
        self.assertNotContains(response, 'name="username"')
        self.assertNotContains(response, 'name="observacoes"')
        self.assertFalse(response.context["form"]["is_staff"].value())

    def test_admin_client_form_creates_linked_login_account(self):
        response = self.client.post(
            reverse("cliente_novo"),
            {
                "nome": "Cliente Novo",
                "email": "cliente.novo@example.com",
                "telefone": "11922223333",
                "password": "123456",
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        cliente = Cliente.objects.get(email="cliente.novo@example.com")
        self.assertIsNotNone(cliente.usuario)
        self.assertTrue(cliente.usuario.check_password("123456"))
        self.assertFalse(cliente.usuario.is_staff)

    def test_client_admin_checkbox_updates_user_access(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="cliente_acesso",
            password="cliente123",
            is_staff=False,
        )
        cliente = Cliente.objects.create(
            usuario=usuario,
            nome="Cliente Acesso",
            email="acesso@example.com",
            telefone="11555555555",
        )

        response = self.client.get(reverse("cliente_editar", args=[cliente.pk]))
        self.assertFalse(response.context["form"]["is_staff"].value())

        response = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]),
            {
                "nome": cliente.nome,
                "email": cliente.email,
                "telefone": cliente.telefone,
                "ativo": "on",
                "is_staff": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_staff)

        response = self.client.get(reverse("cliente_editar", args=[cliente.pk]))
        self.assertTrue(response.context["form"]["is_staff"].value())

        response = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]),
            {
                "nome": cliente.nome,
                "email": cliente.email,
                "telefone": cliente.telefone,
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_staff)

    def test_editing_client_without_password_keeps_current_password(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="senha_preservada",
            password="senha123",
            email="senha@example.com",
        )
        cliente = Cliente.objects.create(
            usuario=usuario,
            nome="Senha Preservada",
            email="senha@example.com",
            telefone="11933334444",
        )

        response = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]),
            {
                "nome": "Nome Alterado",
                "email": cliente.email,
                "telefone": cliente.telefone,
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password("senha123"))

    def test_editing_client_rejects_duplicate_phone(self):
        Cliente.objects.create(
            nome="Telefone Antigo",
            email="outro@example.com",
            telefone=self.cliente.telefone,
        )

        response = self.client.post(
            reverse("cliente_editar", args=[self.cliente.pk]),
            {
                "nome": "Joao Atualizado",
                "email": self.cliente.email,
                "telefone": self.cliente.telefone,
                "ativo": "on",
                "is_staff": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "telefone",
            "Já existe uma conta cadastrada com este telefone.",
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nome, "Joao Mendes")

    def test_client_form_rejects_duplicate_email(self):
        Cliente.objects.create(
            nome="Email Antigo",
            email="duplicado@example.com",
            telefone="11977777777",
        )

        response = self.client.post(
            reverse("cliente_editar", args=[self.cliente.pk]),
            {
                "nome": "Joao Atualizado",
                "email": "duplicado@example.com",
                "telefone": self.cliente.telefone,
                "ativo": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Já existe uma conta cadastrada com este e-mail.",
        )

    def test_editing_client_updates_data_password_and_login_identifiers(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="usuario_antigo",
            password="cliente123",
            first_name="Nome",
            last_name="Antigo",
            email="antigo@example.com",
        )
        cliente = Cliente.objects.create(
            usuario=usuario,
            nome="Nome Antigo",
            email="antigo@example.com",
            telefone="11555555555",
        )

        response = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]),
            {
                "nome": "Nome Atualizado",
                "email": "novo@example.com",
                "telefone": "11444444444",
                "password": "654321",
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        cliente.refresh_from_db()
        usuario.refresh_from_db()
        self.assertEqual(cliente.nome, "Nome Atualizado")
        self.assertEqual(cliente.email, "novo@example.com")
        self.assertEqual(cliente.telefone, "11444444444")
        self.assertEqual(usuario.username, "usuario_antigo")
        self.assertEqual(usuario.first_name, "Nome")
        self.assertEqual(usuario.last_name, "Atualizado")
        self.assertEqual(usuario.email, "novo@example.com")
        self.assertTrue(usuario.check_password("654321"))

        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"identificador": "antigo@example.com", "password": "cliente123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        response = self.client.post(
            reverse("login"),
            {"identificador": "novo@example.com", "password": "654321"},
        )
        self.assertRedirects(response, reverse("agendar"))

        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"identificador": "(11) 44444-4444", "password": "654321"},
        )
        self.assertRedirects(response, reverse("agendar"))

    def test_inactivating_client_disables_login_and_shows_notice(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="cliente_ativo",
            password="cliente123",
            is_active=True,
        )
        cliente = Cliente.objects.create(
            usuario=usuario,
            nome="Cliente Ativo",
            email="cliente@example.com",
            telefone="11333333333",
            ativo=True,
        )

        response = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]),
            {
                "nome": cliente.nome,
                "email": cliente.email,
                "telefone": cliente.telefone,
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

        self.client.logout()
        response = self.client.post(
            reverse("login"),
            {"identificador": "cliente@example.com", "password": "cliente123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este cliente está inativo")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_registration_rejects_short_password_and_invalid_email(self):
        self.client.logout()

        response = self.client.post(
            reverse("cliente_cadastro"),
            {
                "nome": "Cliente Teste",
                "email": "email-invalido",
                "telefone": "11911112222",
                "password": "12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "Informe um endereço de email válido.")
        self.assertFormError(
            response.context["form"],
            "password",
            "Certifique-se de que o valor tenha no mínimo 6 caracteres (ele possui 5).",
        )

    def test_login_does_not_accept_internal_username(self):
        self.client.logout()

        response = self.client.post(
            reverse("login"),
            {"identificador": "admin", "password": "admin123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_user_accesses_only_login_and_registration(self):
        self.client.logout()

        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("cliente_cadastro")).status_code, 200)

        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("dashboard")}',
            fetch_redirect_response=False,
        )

    def test_active_non_admin_accesses_only_booking_page(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="cliente",
            password="cliente123",
            is_active=True,
            is_staff=False,
        )
        Cliente.objects.create(
            usuario=usuario,
            nome="Cliente comum",
            telefone="11666666666",
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse("agendar"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.user.pk, usuario.pk)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.wsgi_request.user.pk, usuario.pk)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertTrue(response.wsgi_request.user.is_active)
        self.assertFalse(response.wsgi_request.user.is_staff)
        self.assertRedirects(
            response,
            reverse("agendar"),
            fetch_redirect_response=False,
        )

        response = self.client.get(reverse("meus_agendamentos"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("cliente_novo"))
        self.assertRedirects(
            response,
            reverse("agendar"),
            fetch_redirect_response=False,
        )

    def test_inactive_user_is_treated_as_anonymous(self):
        User = get_user_model()
        usuario = User.objects.create_user(
            username="inativo",
            password="inativo123",
            is_active=False,
        )
        self.client.force_login(usuario)

        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("cliente_cadastro")).status_code, 200)

        response = self.client.get(reverse("agendar"))
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("agendar")}',
            fetch_redirect_response=False,
        )

    def test_agendamento_page_shows_filters_rows_and_agendar_button(self):
        response = self.client.get(reverse("agendamento_list"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="cliente"')
        self.assertContains(response, 'name="profissional"')
        self.assertContains(response, 'name="status"')
        self.assertContains(response, reverse("agendar"))
        self.assertContains(response, 'class="layout"')
        self.assertContains(response, 'class="sidebar"')
        self.assertIn("Joao Mendes", html)
        self.assertIn("Corte", html)
        self.assertIn("Carlos", html)
        self.assertContains(
            response,
            reverse("agendamento_concluir", args=[self.agendamento.pk]),
        )

    def test_staff_can_mark_appointment_as_completed(self):
        response = self.client.post(
            reverse("agendamento_concluir", args=[self.agendamento.pk])
        )

        self.assertRedirects(response, reverse("agendamento_list"))
        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Agendamento.STATUS_CONCLUIDO)

        response = self.client.get(
            reverse("agendamento_concluir", args=[self.agendamento.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_completed_appointment_cannot_be_edited_or_cancelled(self):
        inicio_original = self.agendamento.inicio
        self.agendamento.concluir()

        response = self.client.get(
            reverse("agendamento_editar", args=[self.agendamento.pk])
        )
        self.assertRedirects(response, reverse("agendamento_list"))

        response = self.client.post(
            reverse("agendamento_editar", args=[self.agendamento.pk]),
            {
                "cliente": self.cliente.pk,
                "profissional": self.profissional.pk,
                "servico": self.servico.pk,
                "inicio": (inicio_original + timedelta(days=1)).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "observacoes": "Tentativa de edicao apos conclusao.",
            },
        )
        self.assertRedirects(response, reverse("agendamento_list"))

        response = self.client.post(
            reverse("agendamento_cancelar", args=[self.agendamento.pk]),
            {"motivo": "Tentativa de cancelamento apos conclusao."},
        )
        self.assertRedirects(response, reverse("agendamento_list"))

        self.agendamento.refresh_from_db()
        self.assertEqual(self.agendamento.status, Agendamento.STATUS_CONCLUIDO)
        self.assertEqual(self.agendamento.inicio, inicio_original)
        self.assertEqual(self.agendamento.observacoes, "")
        self.assertEqual(self.agendamento.motivo_cancelamento, "")

        response = self.client.get(reverse("agendamento_list"))
        self.assertNotContains(
            response,
            reverse("agendamento_editar", args=[self.agendamento.pk]),
        )
        self.assertNotContains(
            response,
            reverse("agendamento_cancelar", args=[self.agendamento.pk]),
        )
        self.assertNotContains(
            response,
            reverse("agendamento_concluir", args=[self.agendamento.pk]),
        )

    def test_professional_form_saves_selected_services(self):
        barba = Servico.objects.create(
            nome="Barba",
            preco="35.00",
            duracao_minutos=30,
        )

        response = self.client.post(
            reverse("profissional_editar", args=[self.profissional.pk]),
            {
                "nome": self.profissional.nome,
                "especialidade": self.profissional.especialidade,
                "telefone": "11955556666",
                "email": "carlos@example.com",
                "servicos": [self.servico.pk, barba.pk],
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("profissional_list"))
        self.assertEqual(
            set(self.profissional.servicos.values_list("pk", flat=True)),
            {self.servico.pk, barba.pk},
        )

    def test_professional_form_rejects_duplicate_email(self):
        Profissional.objects.create(
            nome="Outro Profissional",
            email="carlos@example.com",
            telefone="11911110000",
        )

        response = self.client.post(
            reverse("profissional_editar", args=[self.profissional.pk]),
            {
                "nome": self.profissional.nome,
                "especialidade": self.profissional.especialidade,
                "telefone": "11955556666",
                "email": "carlos@example.com",
                "servicos": [self.servico.pk],
                "ativo": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "Já existe um profissional cadastrado com este e-mail.",
        )

    def test_professional_form_rejects_duplicate_phone(self):
        Profissional.objects.create(
            nome="Outro Profissional",
            email="outro.profissional@example.com",
            telefone="(11) 95555-6666",
        )

        response = self.client.post(
            reverse("profissional_editar", args=[self.profissional.pk]),
            {
                "nome": self.profissional.nome,
                "especialidade": self.profissional.especialidade,
                "telefone": "11955556666",
                "email": "carlos@example.com",
                "servicos": [self.servico.pk],
                "ativo": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "telefone",
            "Já existe um profissional cadastrado com este telefone.",
        )

    def test_professional_form_uploads_photo(self):
        foto = SimpleUploadedFile(
            "carlos.jpg",
            b"fake image content",
            content_type="image/jpeg",
        )

        response = self.client.post(
            reverse("profissional_editar", args=[self.profissional.pk]),
            {
                "nome": self.profissional.nome,
                "especialidade": self.profissional.especialidade,
                "telefone": "11955556666",
                "email": "carlos@example.com",
                "foto": foto,
                "servicos": [self.servico.pk],
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("profissional_list"))
        self.profissional.refresh_from_db()
        self.assertTrue(self.profissional.foto.name.startswith("profissionais/"))
        self.assertTrue(self.profissional.foto.name.endswith(".jpg"))

    def test_agendar_page_shows_professional_photo_when_available(self):
        self.profissional.foto = "profissionais/carlos.jpg"
        self.profissional.save(update_fields=["foto"])

        response = self.client.get(
            reverse("agendar"),
            {"servico": self.servico.pk, "profissional": self.profissional.pk},
        )

        self.assertContains(response, "/media/profissionais/carlos.jpg")
        self.assertContains(response, 'class="professional-avatar-image"')
        self.assertContains(response, 'width="56"')
        self.assertContains(response, 'height="56"')
        self.assertContains(response, 'alt="Foto de Carlos"')

    def test_dashboard_shows_only_todays_non_cancelled_appointments(self):
        hoje = timezone.localdate()
        self.agendamento.inicio = timezone.make_aware(
            datetime.combine(hoje, time(hour=12))
        )
        self.agendamento.save(update_fields=["inicio"])

        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.make_aware(datetime.combine(hoje, time(hour=13))),
            status=Agendamento.STATUS_CANCELADO,
        )
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.make_aware(
                datetime.combine(hoje + timedelta(days=1), time(hour=12))
            ),
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["agendamentos_hoje"]),
            [self.agendamento],
        )
        self.assertEqual(response.context["qtd_hoje"], 1)
        self.assertContains(response, "12:00")
        ranking = response.context["ranking_profissionais"]
        self.assertEqual(ranking[0], self.profissional)
        self.assertEqual(ranking[0].qtd, 2)
        self.assertEqual(ranking[0].percentual_grafico, 100)
        self.assertContains(response, 'class="professionals-chart"')
        self.assertContains(response, "width: 100%")
        self.assertContains(response, "2 agendamentos")
        ranking_servicos = response.context["ranking_servicos"]
        self.assertEqual(ranking_servicos[0], self.servico)
        self.assertEqual(ranking_servicos[0].qtd, 2)
        self.assertEqual(ranking_servicos[0].percentual_grafico, 100)
        self.assertEqual(response.context["total_ranking_servicos"], 2)
        self.assertContains(response, 'class="services-pie"')
        self.assertContains(response, "#7c3aed 0.00% 100.00%")

    def test_dashboard_navigates_between_days(self):
        hoje = timezone.localdate()
        ontem = hoje - timedelta(days=1)
        amanha = hoje + timedelta(days=1)
        self.agendamento.inicio = timezone.make_aware(
            datetime.combine(hoje, time(hour=10))
        )
        self.agendamento.save(update_fields=["inicio"])
        agendamento_ontem = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.make_aware(datetime.combine(ontem, time(hour=11))),
        )
        agendamento_amanha = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.make_aware(datetime.combine(amanha, time(hour=12))),
        )

        response = self.client.get(reverse("dashboard"), {"data": amanha.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["data_selecionada"], amanha)
        self.assertEqual(list(response.context["agendamentos_hoje"]), [agendamento_amanha])
        self.assertEqual(response.context["qtd_hoje"], 1)
        self.assertContains(response, "Agenda de amanhã")
        self.assertContains(response, f"?data={hoje.isoformat()}")
        self.assertContains(response, f"?data={(amanha + timedelta(days=1)).isoformat()}")

        response = self.client.get(reverse("dashboard"), {"data": ontem.isoformat()})

        self.assertEqual(response.context["data_selecionada"], ontem)
        self.assertEqual(list(response.context["agendamentos_hoje"]), [agendamento_ontem])
        self.assertContains(response, "Agenda de ontem")

    def test_agendamento_page_filters_by_client(self):
        outro_cliente = Cliente.objects.create(nome="Outro Cliente", telefone="1100000000")
        Agendamento.objects.create(
            cliente=outro_cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.now() + timedelta(days=2),
        )

        response = self.client.get(
            reverse("agendamento_list"),
            {"cliente": self.cliente.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Joao Mendes")
        self.assertEqual(list(response.context["agendamentos"]), [self.agendamento])

    def test_staff_can_update_business_hours(self):
        horarios = list(HorarioFuncionamento.objects.order_by("dia_semana"))
        post_data = {
            "form-TOTAL_FORMS": str(len(horarios)),
            "form-INITIAL_FORMS": str(len(horarios)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        for index, horario in enumerate(horarios):
            post_data[f"form-{index}-id"] = horario.pk
            post_data[f"form-{index}-hora_abertura"] = "08:30"
            post_data[f"form-{index}-hora_fechamento"] = "18:00"
            if horario.dia_semana != HorarioFuncionamento.DOMINGO:
                post_data[f"form-{index}-aberto"] = "on"

        response = self.client.post(reverse("horario_funcionamento"), post_data)

        self.assertRedirects(response, reverse("horario_funcionamento"))
        domingo = HorarioFuncionamento.objects.get(
            dia_semana=HorarioFuncionamento.DOMINGO
        )
        segunda = HorarioFuncionamento.objects.get(
            dia_semana=HorarioFuncionamento.SEGUNDA
        )
        self.assertFalse(domingo.aberto)
        self.assertEqual(segunda.hora_abertura, time(hour=8, minute=30))
        self.assertEqual(segunda.hora_fechamento, time(hour=18))

    def test_agendar_page_uses_business_hours_for_available_times(self):
        data = self.future_date_for_weekday(HorarioFuncionamento.QUARTA)
        horario = HorarioFuncionamento.objects.get(dia_semana=data.weekday())
        horario.aberto = True
        horario.hora_abertura = time(hour=10)
        horario.hora_fechamento = time(hour=12)
        horario.save()

        response = self.client.get(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="09:00"')
        self.assertContains(response, 'value="10:00"')
        self.assertContains(response, 'value="11:30"')
        self.assertNotContains(response, 'value="12:00"')

    def test_agendar_page_disables_closed_business_days(self):
        data = self.future_date_for_weekday(HorarioFuncionamento.QUINTA)
        horario = HorarioFuncionamento.objects.get(dia_semana=data.weekday())
        horario.aberto = False
        horario.save(update_fields=["aberto"])

        response = self.client.get(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-date="{data.isoformat()}"')
        self.assertContains(response, "calendar-day-disabled")
        self.assertNotContains(response, f'name="data" value="{data.isoformat()}"')

    def test_manual_booking_outside_business_hours_is_blocked(self):
        data = self.future_date_for_weekday(HorarioFuncionamento.SEXTA)
        horario = HorarioFuncionamento.objects.get(dia_semana=data.weekday())
        horario.aberto = True
        horario.hora_abertura = time(hour=10)
        horario.hora_fechamento = time(hour=12)
        horario.save()

        response = self.client.post(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
                "horario": "09:00",
                "observacoes": "Fora do expediente.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "fora do expediente")
        self.assertFalse(
            Agendamento.objects.filter(observacoes="Fora do expediente.").exists()
        )

    def test_agendamento_model_rejects_outside_business_hours(self):
        data = self.future_date_for_weekday(HorarioFuncionamento.SABADO)
        horario = HorarioFuncionamento.objects.get(dia_semana=data.weekday())
        horario.aberto = True
        horario.hora_abertura = time(hour=10)
        horario.hora_fechamento = time(hour=12)
        horario.save()
        agendamento = Agendamento(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.make_aware(datetime.combine(data, time(hour=9))),
        )

        with self.assertRaises(ValidationError) as error:
            agendamento.full_clean()

        self.assertIn("fora do expediente", str(error.exception))

    def test_agendar_page_shows_database_options_and_free_times(self):
        data = timezone.localdate() + timedelta(days=5)

        response = self.client.get(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corte")
        self.assertContains(response, "Carlos")
        self.assertContains(response, 'name="servico"')
        self.assertContains(response, 'name="profissional"')
        self.assertContains(response, 'name="data"')
        self.assertContains(response, 'name="horario"')
        self.assertContains(response, 'class="appointment-observations"')
        self.assertContains(response, 'class="appointment-summary-grid"')
        self.assertContains(response, 'id="summary-service"')
        self.assertContains(response, 'id="summary-professional"')
        self.assertContains(response, 'id="summary-date"')
        self.assertContains(response, 'id="summary-time"')
        self.assertContains(response, 'id="summary-price"')
        self.assertContains(response, reverse("meus_agendamentos"))
        self.assertContains(response, 'class="btn btn-my-bookings"')
        self.assertContains(
            response,
            "Deseja realmente confirmar este agendamento?",
        )
        self.assertContains(response, 'id="booking-confirmation-modal"')
        self.assertContains(response, 'id="booking-confirmation-cancel"')
        self.assertContains(response, 'id="booking-confirmation-accept"')
        self.assertContains(response, "Sim, confirmar")
        self.assertNotContains(response, "window.confirm")
        self.assertContains(response, 'value="09:00"')
        self.assertContains(
            response,
            'sessionStorage.setItem(scrollKey, String(window.scrollY))',
        )
        self.assertContains(response, 'window.scrollTo(0, Number(savedScroll))')
        self.assertContains(response, 'const observationsKey = "agendar-observacoes"')
        self.assertContains(response, "savedObservations")

    def test_agendar_page_hides_busy_times(self):
        data = timezone.localdate() + timedelta(days=6)
        inicio_ocupado = timezone.make_aware(datetime.combine(data, time(hour=9)))
        Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=inicio_ocupado,
        )

        response = self.client.get(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="09:00"')
        self.assertContains(response, 'value="09:30"')

    def test_agendar_page_shows_unavailable_dates_disabled_in_calendar(self):
        data = timezone.localdate() + timedelta(days=35)
        abertura = datetime.combine(data, time(hour=9))
        for indice in range(20):
            Agendamento.objects.create(
                cliente=self.cliente,
                profissional=self.profissional,
                servico=self.servico,
                inicio=timezone.make_aware(abertura + timedelta(minutes=30 * indice)),
            )

        response = self.client.get(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "mes": data.strftime("%Y-%m"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="calendar-grid"')
        self.assertContains(response, f'data-date="{data.isoformat()}"')
        self.assertContains(response, "calendar-day-disabled")
        self.assertNotContains(response, f'name="data" value="{data.isoformat()}"')

    def test_agendar_page_creates_appointment_for_logged_client(self):
        data = timezone.localdate() + timedelta(days=7)

        response = self.client.post(
            reverse("agendar"),
            {
                "servico": self.servico.pk,
                "profissional": self.profissional.pk,
                "data": data.isoformat(),
                "horario": "09:00",
                "observacoes": "Criado pela tela agendar.",
            },
        )

        agendamento = Agendamento.objects.get(
            cliente=self.cliente,
            servico=self.servico,
            profissional=self.profissional,
            observacoes="Criado pela tela agendar.",
        )
        self.assertRedirects(
            response,
            f'{reverse("agendar")}?sucesso={agendamento.pk}',
        )

        confirmacao = self.client.get(response.url)
        self.assertContains(confirmacao, "Agendamento concluído")
        self.assertContains(confirmacao, self.cliente.nome)
        self.assertContains(confirmacao, self.servico.nome)
        self.assertContains(confirmacao, self.profissional.nome)
        self.assertContains(confirmacao, "Criado pela tela agendar.")
        self.assertContains(confirmacao, 'class="booking-success-detail-row"')
        self.assertContains(confirmacao, "Valor do serviço")
        self.assertContains(confirmacao, reverse("meus_agendamentos"))
        self.assertContains(confirmacao, "Meus agendamentos")
        self.assertContains(confirmacao, "booking-success-main-action")
        self.assertContains(confirmacao, "booking-success-secondary-actions")
        self.assertContains(confirmacao, "Fazer novo agendamento")
        self.assertContains(confirmacao, ">Sair<")

    def test_client_cannot_view_another_clients_confirmation(self):
        User = get_user_model()
        outro_usuario = User.objects.create_user(
            username="outro_cliente",
            password="cliente123",
            is_staff=False,
        )
        Cliente.objects.create(
            usuario=outro_usuario,
            nome="Outro Cliente",
            telefone="11444444444",
        )
        self.client.force_login(outro_usuario)

        response = self.client.get(
            reverse("agendar"),
            {"sucesso": self.agendamento.pk},
        )

        self.assertEqual(response.status_code, 404)

    def test_my_appointments_uses_logged_clients_data_and_filters(self):
        concluido = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.now() - timedelta(days=2),
            status=Agendamento.STATUS_CONCLUIDO,
        )
        cancelado = Agendamento.objects.create(
            cliente=self.cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.now() - timedelta(days=3),
            status=Agendamento.STATUS_CANCELADO,
        )
        outro_cliente = Cliente.objects.create(
            nome="Cliente de fora",
            telefone="11333333333",
        )
        outro_agendamento = Agendamento.objects.create(
            cliente=outro_cliente,
            profissional=self.profissional,
            servico=self.servico,
            inicio=timezone.now() + timedelta(days=4),
        )

        response = self.client.get(reverse("meus_agendamentos"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_proximos"], 1)
        self.assertEqual(response.context["total_concluidos"], 1)
        self.assertEqual(response.context["total_cancelados"], 1)
        self.assertEqual(
            set(response.context["agendamentos"]),
            {self.agendamento, concluido, cancelado},
        )
        self.assertNotIn(outro_agendamento, response.context["agendamentos"])
        self.assertContains(response, 'class="my-bookings-card"', count=3)
        self.assertContains(response, ">Sair<")

        response = self.client.get(
            reverse("meus_agendamentos"),
            {"status": "concluidos"},
        )
        self.assertEqual(list(response.context["agendamentos"]), [concluido])

        response = self.client.get(
            reverse("meus_agendamentos"),
            {"status": "cancelados"},
        )
        self.assertEqual(list(response.context["agendamentos"]), [cancelado])

        response = self.client.get(
            reverse("meus_agendamentos"),
            {"status": "proximos"},
        )
        self.assertEqual(list(response.context["agendamentos"]), [self.agendamento])

    def test_deleting_client_with_appointments_shows_warning(self):
        response = self.client.post(
            reverse("cliente_excluir", args=[self.cliente.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("cliente_list"))
        self.assertTrue(Cliente.objects.filter(pk=self.cliente.pk).exists())
        self.assertContains(response, "Não é possível excluir este cliente")

    def test_deleting_client_without_appointments_removes_linked_access_account(self):
        User = get_user_model()
        conta = User.objects.create_user(
            username="cliente_sem_agenda",
            password="cliente123",
            email="sem.agenda@example.com",
        )
        cliente = Cliente.objects.create(
            usuario=conta,
            nome="Cliente Sem Agenda",
            email="sem.agenda@example.com",
            telefone="11910101010",
        )

        response = self.client.post(reverse("cliente_excluir", args=[cliente.pk]))

        self.assertRedirects(response, reverse("cliente_list"))
        self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())
        self.assertFalse(User.objects.filter(pk=conta.pk).exists())

    def test_deleting_service_with_appointments_shows_warning(self):
        response = self.client.post(
            reverse("servico_excluir", args=[self.servico.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("servico_list"))
        self.assertTrue(Servico.objects.filter(pk=self.servico.pk).exists())
        self.assertContains(response, "Não é possível excluir este serviço")

    def test_deleting_professional_with_appointments_shows_warning(self):
        response = self.client.post(
            reverse("profissional_excluir", args=[self.profissional.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("profissional_list"))
        self.assertTrue(Profissional.objects.filter(pk=self.profissional.pk).exists())
        self.assertContains(response, "Não é possível excluir este profissional")

    def test_main_pages_render(self):
        urls = [
            reverse("dashboard"),
            reverse("cliente_cadastro"),
            reverse("cliente_list"),
            reverse("cliente_novo"),
            reverse("cliente_editar", args=[self.cliente.pk]),
            reverse("cliente_excluir", args=[self.cliente.pk]),
            reverse("servico_list"),
            reverse("servico_novo"),
            reverse("servico_editar", args=[self.servico.pk]),
            reverse("servico_excluir", args=[self.servico.pk]),
            reverse("profissional_list"),
            reverse("profissional_novo"),
            reverse("profissional_editar", args=[self.profissional.pk]),
            reverse("profissional_excluir", args=[self.profissional.pk]),
            reverse("horario_funcionamento"),
            reverse("agendamento_list"),
            reverse("agendar"),
            reverse("meus_agendamentos"),
            reverse("agendamento_novo"),
            reverse("agendamento_editar", args=[self.agendamento.pk]),
            reverse("agendamento_cancelar", args=[self.agendamento.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
