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
        self.assertContains(response, 'value="09:00"')

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

        self.assertRedirects(response, reverse("agendar"))
        self.assertTrue(
            Agendamento.objects.filter(
                cliente=self.cliente,
                servico=self.servico,
                profissional=self.profissional,
                observacoes="Criado pela tela agendar.",
            ).exists()
        )

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
            reverse("agendamento_novo"),
            reverse("agendamento_editar", args=[self.agendamento.pk]),
            reverse("agendamento_cancelar", args=[self.agendamento.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
