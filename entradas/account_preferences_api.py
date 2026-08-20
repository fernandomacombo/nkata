from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import PreferenciasContaNKATA


PREFERENCE_FIELDS = {
    "idioma": dict(PreferenciasContaNKATA.Idioma.choices),
    "tema_perfil": dict(PreferenciasContaNKATA.TemaPerfil.choices),
    "fundo_conversa": dict(PreferenciasContaNKATA.FundoConversa.choices),
}


def serialize_preferences(preferences):
    return {
        "idioma": preferences.idioma,
        "tema_perfil": preferences.tema_perfil,
        "fundo_conversa": preferences.fundo_conversa,
        "opcoes": {
            field: [
                {"value": value, "label": label}
                for value, label in choices.items()
            ]
            for field, choices in PREFERENCE_FIELDS.items()
        },
        "atualizado_em": preferences.atualizado_em,
    }


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def api_preferencias_da_conta(request):
    preferences, _ = PreferenciasContaNKATA.objects.get_or_create(
        usuario=request.user,
    )

    if request.method == "PATCH":
        errors = {}
        changed_fields = []

        for field, choices in PREFERENCE_FIELDS.items():
            if field not in request.data:
                continue

            value = str(request.data.get(field, "")).strip().upper()
            if value not in choices:
                errors[field] = ["Escolha uma opção válida."]
                continue

            if getattr(preferences, field) != value:
                setattr(preferences, field, value)
                changed_fields.append(field)

        if errors:
            return Response(
                {"detail": "Revise as preferências indicadas.", "errors": errors},
                status=400,
            )

        if changed_fields:
            preferences.save(update_fields=[*changed_fields, "atualizado_em"])

    return Response(serialize_preferences(preferences))
