from django.contrib.auth.models import Group


ADMIN_CAPABILITIES = (
    {
        "code": "overview",
        "label": "Visão geral",
        "description": "Consultar indicadores da comunidade.",
        "group": "NKATA_STAFF_VISAO_GERAL",
    },
    {
        "code": "access",
        "label": "Pedidos",
        "description": "Rever identidade e decidir pedidos de entrada.",
        "group": "NKATA_STAFF_PEDIDOS",
    },
    {
        "code": "members",
        "label": "Membros e planos",
        "description": "Gerir contas, perfis e planos ativos.",
        "group": "NKATA_STAFF_MEMBROS",
    },
    {
        "code": "content",
        "label": "Moderação",
        "description": "Aprovar ou rejeitar publicações e Momentos.",
        "group": "NKATA_STAFF_MODERACAO",
    },
    {
        "code": "reports",
        "label": "Denúncias",
        "description": "Analisar denúncias e aplicar medidas de segurança.",
        "group": "NKATA_STAFF_DENUNCIAS",
    },
    {
        "code": "operations",
        "label": "Operações",
        "description": "Acompanhar matches e chamadas.",
        "group": "NKATA_STAFF_OPERACOES",
    },
    {
        "code": "audit",
        "label": "Auditoria",
        "description": "Consultar o histórico das ações administrativas.",
        "group": "NKATA_STAFF_AUDITORIA",
    },
)

CAPABILITY_BY_CODE = {item["code"]: item for item in ADMIN_CAPABILITIES}
CAPABILITY_BY_GROUP = {item["group"]: item["code"] for item in ADMIN_CAPABILITIES}


def is_operator(user):
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    )


def member_profile_for_user(user):
    """Operadores administrativos nunca atuam como perfis da comunidade."""
    if not user or not getattr(user, "is_authenticated", False) or is_operator(user):
        return None
    return getattr(user, "perfil_nkata", None)


def active_member_profile_for_user(user):
    profile = member_profile_for_user(user)
    if not profile or profile.status != "ATIVO" or not getattr(user, "is_active", False):
        return None
    return profile


def admin_capability_codes(user):
    if not is_operator(user):
        return []
    if user.is_superuser:
        return [item["code"] for item in ADMIN_CAPABILITIES]

    group_names = set(
        user.groups.filter(name__in=CAPABILITY_BY_GROUP).values_list("name", flat=True)
    )
    return [
        item["code"]
        for item in ADMIN_CAPABILITIES
        if item["group"] in group_names
    ]


def has_admin_capability(user, capability):
    return capability in admin_capability_codes(user)


def admin_capabilities_payload(user):
    allowed = set(admin_capability_codes(user))
    return [
        {
            "code": item["code"],
            "label": item["label"],
            "description": item["description"],
        }
        for item in ADMIN_CAPABILITIES
        if item["code"] in allowed
    ]


def ensure_admin_capability_groups():
    return {
        item["code"]: Group.objects.get_or_create(name=item["group"])[0]
        for item in ADMIN_CAPABILITIES
    }


def set_admin_capabilities(user, capability_codes):
    valid_codes = {str(code).strip().lower() for code in capability_codes or []}
    invalid_codes = valid_codes.difference(CAPABILITY_BY_CODE)
    if invalid_codes:
        raise ValueError("Permissão administrativa inválida.")

    groups = ensure_admin_capability_groups()
    user.groups.remove(*groups.values())
    if valid_codes:
        user.groups.add(*(groups[code] for code in valid_codes))
    return admin_capability_codes(user)
