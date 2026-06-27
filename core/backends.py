from django.contrib.auth.backends import ModelBackend

from .auth_utils import contas_por_identificador


class EmailOuTelefoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identificador = username or kwargs.get("email") or kwargs.get("telefone")
        if not identificador or password is None:
            return None

        for conta in contas_por_identificador(identificador):
            if conta.check_password(password) and self.user_can_authenticate(conta):
                return conta

        return None
