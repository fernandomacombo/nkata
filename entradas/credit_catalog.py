"""NKATA unified commercial catalogue.

Configuration only: wallet settlement and consumption remain disabled until the
transaction ledger, payment verification and legacy entitlement migration exist.
Do not use catalogue prices to debit existing signal recharges.
"""

SIGNAL_DEFINITIONS = {
    "OLA": {
        "db_type": "SINAL_OLA", "label": "Olá", "icon": "hand", "credits": 1,
        "message": "Olá, gostei do seu perfil e gostaria de conhecer melhor.",
    },
    "FLOR": {
        "db_type": "SINAL_FLOR", "label": "Flor", "icon": "flower", "credits": 2,
        "message": "Uma flor para mostrar que este perfil chamou a sua atenção.",
    },
    "BEIJINHO": {
        "db_type": "SINAL_BEIJINHO", "label": "Beijinho", "icon": "heart", "credits": 3,
        "message": "Um gesto carinhoso, sem abrir uma conversa privada.",
    },
}

CREDIT_PACKS = (
    {"code": "INICIAL", "label": "Inicial", "price_mzn": 50, "credits": 50, "bonus": 0},
    {"code": "ESSENCIAL", "label": "Essencial", "price_mzn": 100, "credits": 100, "bonus": 0},
    {"code": "POPULAR", "label": "Popular", "price_mzn": 250, "credits": 275, "bonus": 25},
    {"code": "PREMIUM", "label": "Premium", "price_mzn": 500, "credits": 600, "bonus": 100},
)

WELCOME_CREDITS = 5


def credit_catalog():
    return {
        "enabled": False,
        "version": 1,
        "welcome_credits": WELCOME_CREDITS,
        "packs": [dict(pack, purchase_enabled=False) for pack in CREDIT_PACKS],
        "actions": [
            *[{"code": code, "label": item["label"], "credits": item["credits"], "unit": "signal"}
              for code, item in SIGNAL_DEFINITIONS.items()],
            {"code": "ICEBREAKER", "label": "Quebra-gelo", "credits": 0, "unit": "limited"},
            {"code": "PRESET", "label": "Mensagem predefinida", "credits": 0, "unit": "limited"},
            {"code": "CHAT_24H", "label": "Chat de texto", "credits": 10, "unit": "24h"},
            {"code": "VOICE_NOTE", "label": "Nota de voz", "credits": 2, "unit": "message"},
            {"code": "AUDIO_CALL", "label": "Chamada de áudio", "credits": 3, "unit": "minute"},
            {"code": "VIDEO_CALL", "label": "Videochamada", "credits": 5, "unit": "minute"},
        ],
    }
