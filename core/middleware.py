from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse


class ControleAcessoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        caminho = request.path_info

        # Permite o carregamento de imagens, CSS e JavaScript.
        static_url = settings.STATIC_URL
        media_url = getattr(settings, "MEDIA_URL", "")
        if caminho.startswith(static_url) or (
            media_url
            and media_url != "/"
            and caminho.startswith(media_url)
        ):
            return self.get_response(request)

        login = reverse("login")
        cadastro = reverse("usuario_novo")
        agendar = reverse("agendar")
        meus_agendamentos = reverse("meus_agendamentos")
        logout = reverse("logout")
        usuario = request.user


        if not usuario.is_authenticated or not usuario.is_active:
            paginas_publicas = [login, cadastro]
            if caminho not in paginas_publicas:
                return redirect_to_login(request.get_full_path(), login)


        elif not usuario.is_staff:
            paginas_do_cliente = [agendar, meus_agendamentos, logout]
            if caminho not in paginas_do_cliente:
                return redirect(agendar)

        return self.get_response(request)
