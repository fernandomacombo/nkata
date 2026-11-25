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

CREDIT_PRODUCTS = {f"CREDITOS_{pack['code']}": pack for pack in CREDIT_PACKS}

WELCOME_CREDITS = 5
CHAT_24H_CREDITS = 10
VOICE_NOTE_CREDITS = 2
AUDIO_CALL_CREDITS_PER_MINUTE = 3
VIDEO_CALL_CREDITS_PER_MINUTE = 5
SIGNAL_SAFETY_LIMIT = 100

ICEBREAKER_DAILY_LIMIT = 3
ICEBREAKERS = {
    "VALORES": "O que mais valorizas numa relação?",
    "ENCONTRO": "Como seria o teu encontro perfeito?",
    "SORRISO": "O que te faz sorrir facilmente?",
    "SONHO": "Qual é o teu maior sonho?",
}
SIGNAL_CHAT_TEXT = {"OLA": "Um olá para ti!", "FLOR": "Uma flor para ti!", "BEIJINHO": "Um beijinho para ti!"}


def credit_catalog(purchase_enabled=False):
    return {
        "enabled": False,
        "version": 1,
        "welcome_credits": WELCOME_CREDITS,
        "packs": [dict(pack, product=product, purchase_enabled=bool(purchase_enabled)) for product, pack in CREDIT_PRODUCTS.items()],
        "actions": [
            *[{"code": code, "label": item["label"], "credits": item["credits"], "unit": "signal"}
              for code, item in SIGNAL_DEFINITIONS.items()],
            {"code": "ICEBREAKER", "label": "Quebra-gelo", "credits": 0, "unit": "limited"},
            {"code": "PRESET", "label": "Mensagem predefinida", "credits": 0, "unit": "limited"},
            {"code": "CHAT_24H", "label": "Chat de texto", "credits": CHAT_24H_CREDITS, "unit": "24h"},
            {"code": "VOICE_NOTE", "label": "Nota de voz", "credits": VOICE_NOTE_CREDITS, "unit": "message"},
            {"code": "AUDIO_CALL", "label": "Chamada de áudio", "credits": AUDIO_CALL_CREDITS_PER_MINUTE, "unit": "minute"},
            {"code": "VIDEO_CALL", "label": "Videochamada", "credits": VIDEO_CALL_CREDITS_PER_MINUTE, "unit": "minute"},
        ],
    }
