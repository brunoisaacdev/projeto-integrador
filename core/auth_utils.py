import re

from django.contrib.auth import get_user_model
from django.db.models import Q


def normalizar_telefone(valor):
    return re.sub(r"\D", "", valor or "")


def contas_por_identificador(identificador):
    identificador = (identificador or "").strip()
    if not identificador:
        return []

    User = get_user_model()
    if "@" in identificador:
        return list(
            User._default_manager.filter(
                Q(email__iexact=identificador)
                | Q(cliente__email__iexact=identificador)
            ).distinct()
        )

    telefone = normalizar_telefone(identificador)
    if not telefone:
        return []

    return [
        conta
        for conta in User._default_manager.select_related("cliente").filter(
            cliente__isnull=False
        )
        if normalizar_telefone(conta.cliente.telefone) == telefone
    ]
