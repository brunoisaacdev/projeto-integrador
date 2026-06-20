from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Agendamento, Cliente, Profissional, Servico


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

    def test_login_page_renders(self):
        self.client.logout()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("usuario_novo"))

    def test_usuario_form_creates_regular_user_and_cliente(self):
        self.client.logout()

        response = self.client.post(
            reverse("usuario_novo"),
            {
                "username": "recepcao",
                "first_name": "Maria",
                "last_name": "Recepcao",
                "email": "recepcao@example.com",
                "telefone": "11888888888",
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        User = get_user_model()
        user = User.objects.get(username="recepcao")
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.cliente.nome, "Maria Recepcao")
        self.assertEqual(user.cliente.telefone, "11888888888")

    def test_admin_can_create_active_admin_user_with_checkboxes(self):
        response = self.client.get(reverse("usuario_novo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_staff"')
        self.assertContains(response, 'name="is_active"')

        response = self.client.post(
            reverse("usuario_novo"),
            {
                "username": "novo_admin",
                "first_name": "Novo",
                "last_name": "Admin",
                "email": "novo.admin@example.com",
                "telefone": "11777777777",
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
                "is_staff": "on",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        User = get_user_model()
        novo_admin = User.objects.get(username="novo_admin")
        self.assertTrue(novo_admin.is_staff)
        self.assertTrue(novo_admin.is_active)

    def test_new_client_admin_checkbox_starts_unchecked(self):
        response = self.client.get(reverse("cliente_novo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_staff"')
        self.assertFalse(response.context["form"]["is_staff"].value())

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
                "observacoes": "",
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
                "observacoes": "",
                "ativo": "on",
            },
        )

        self.assertRedirects(response, reverse("cliente_list"))
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_staff)

    def test_anonymous_user_accesses_only_login_and_registration(self):
        self.client.logout()

        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("usuario_novo")).status_code, 200)

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
        self.assertEqual(self.client.get(reverse("usuario_novo")).status_code, 200)

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

    def test_main_pages_render(self):
        urls = [
            reverse("dashboard"),
            reverse("usuario_novo"),
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
