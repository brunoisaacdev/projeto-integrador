from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse


class ControleAcessoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        caminho = request.path_info

        static_url = settings.STATIC_URL
        media_url = getattr(settings, "MEDIA_URL", "")
        if caminho.startswith(static_url) or (
            media_url
            and media_url != "/"
            and caminho.startswith(media_url)
        ):
            return self.get_response(request)
 
        login = reverse("login")
        cadastro = reverse("cliente_cadastro")
        password_reset = reverse("password_reset")
        password_reset_done = reverse("password_reset_done")
        password_reset_confirm_prefix = "/senha/redefinir/"
        password_reset_complete = reverse("password_reset_complete")
        agendar = reverse("agendar")
        meus_agendamentos = reverse("meus_agendamentos")
        cancelar_meu_agendamento_prefix = "/meus-agendamentos/"
        logout = reverse("logout")
        usuario = request.user


        if not usuario.is_authenticated or not usuario.is_active:
            paginas_publicas = [
                login,
                cadastro,
                password_reset,
                password_reset_done,
                password_reset_complete,
            ]
            if (
                caminho not in paginas_publicas
                and not caminho.startswith(password_reset_confirm_prefix)
            ):
                return redirect_to_login(request.get_full_path(), login)


        elif not usuario.is_staff:
            paginas_do_cliente = [agendar, meus_agendamentos, logout]
            if (
                caminho not in paginas_do_cliente
                and not (
                    caminho.startswith(cancelar_meu_agendamento_prefix)
                    and caminho.endswith("/cancelar/")
                )
            ):
                return redirect(agendar)

        return self.get_response(request)
