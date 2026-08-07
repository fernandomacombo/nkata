from django.conf import settings
from django.shortcuts import redirect


def questionario_moderno(request, token):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/questionario/{token}/")


def criar_senha_moderno(request, token):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/questionario/{token}/")
