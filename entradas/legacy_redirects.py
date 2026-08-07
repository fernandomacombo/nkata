from django.conf import settings
from django.shortcuts import redirect


def questionario_moderno(request, token):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/questionario/{token}/")


def criar_senha_moderno(request, token):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/questionario/{token}/")


def recuperar_senha_moderno(request):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/recuperar-senha/")


def recuperar_senha_enviado_moderno(request):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/recuperar-senha/")


def nova_senha_moderno(request, uidb64, token):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/nova-senha/{uidb64}/{token}/")


def nova_senha_concluida_moderno(request):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/entrar/")


def alterar_senha_moderno(request):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/alterar-senha/")


def alterar_senha_concluida_moderno(request):
    return redirect(f"{settings.NKATA_FRONTEND_URL}/conta/")
