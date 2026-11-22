from .identity_models import pedido_tem_identidade_verificada
from .identity_verification_service import CAPTURE_LABELS, next_capture


def next_step(pedido):
    if pedido.status == "PRECISA_CORRIGIR":
        verification = getattr(pedido, "verificacao_identidade", None)
        if verification and verification.status == "REPETIR":
            return ("Envie novas capturas do NKATA ID",
                    "A equipa pediu novas capturas da frente e do verso do BI e uma selfie. Abra o seu pedido para retomar a verificação.",
                    "/acompanhar-pedido/")
        return ("Corrija o seu pedido de acesso ao NKATA",
                "O seu pedido precisa de uma correção. Consulte as instruções da equipa.",
                "/acompanhar-pedido/")
    if pedido.status != "APROVADO":
        return None

    perfil = getattr(pedido, "perfil", None)
    if not hasattr(pedido, "questionario"):
        return ("Responda ao questionário do NKATA",
                "O seu pedido de acesso foi aprovado. O questionário ajuda a completar o seu perfil "
                "e a apresentar o que procura a pessoas com intenções semelhantes. "
                "Depois de responder, crie a sua palavra-passe para entrar na conta.",
                f"/questionario/{pedido.token}/")
    if not perfil or not perfil.usuario or not perfil.usuario.has_usable_password():
        return ("Crie a sua palavra-passe para entrar no NKATA",
                "As suas respostas já foram guardadas. Crie uma palavra-passe para proteger a sua conta e poder entrar no NKATA.",
                f"/questionario/{pedido.token}/")
    if perfil.status in {"BLOQUEADO", "ENCERRAMENTO"} or not perfil.usuario.is_active:
        return None

    verification = getattr(pedido, "verificacao_identidade", None)
    if verification and verification.status == "REVISAO":
        return None
    if pedido_tem_identidade_verificada(pedido):
        return None
    if verification and verification.status == "REPETIR":
        message = "A equipa solicitou novas capturas. Entre no NKATA, abra Matches e siga as instruções do NKATA ID."
    elif verification and verification.status == "EM_CAPTURA" and not verification.capturas_completas:
        label = CAPTURE_LABELS[next_capture(verification)]
        message = f"A sua verificação está incompleta. Próxima captura: {label}. Entre no NKATA para continuar."
    else:
        message = "A sua conta já está criada. Entre, abra Matches e conclua o NKATA ID para desbloquear as funções que exigem identidade verificada."
    message += (
        " O NKATA ID faz parte da segurança da comunidade. A confirmação da identidade "
        "ajuda a reduzir perfis falsos e a proteger quem usa o NKATA."
    )
    return "Conclua a verificação de identidade no NKATA", message, "/matches/"
