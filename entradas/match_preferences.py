import re

from rest_framework import serializers


SMOKING = {
    "never": "Não fuma", "occasionally": "Fuma ocasionalmente", "regularly": "Fuma",
}
DRINKING = {
    "never": "Não bebe", "occasionally": "Bebe ocasionalmente", "regularly": "Bebe regularmente",
}


def preferred_ages(value):
    match = re.fullmatch(r"\s*(\d{2,3})\s*(?:a|[-–—])\s*(\d{2,3})(?:\s+anos)?\s*", value, re.IGNORECASE)
    if match:
        minimum, maximum = map(int, match.groups())
        if 18 <= minimum <= maximum <= 120:
            return [minimum, maximum]
    return None


def profile_preferences(profile):
    data = dict(profile.preferencias)
    if "ages" not in data:
        questionnaire = getattr(profile.pedido, "questionario", None)
        data["ages"] = preferred_ages(questionnaire.faixa_etaria_preferida) if questionnaire else None
    return data


class MatchPreferencesSerializer(serializers.Serializer):
    ages = serializers.ListField(
        child=serializers.IntegerField(min_value=18, max_value=120),
        min_length=2, max_length=2, allow_null=True, required=False,
    )
    show_ages = serializers.BooleanField(required=False)
    height = serializers.IntegerField(min_value=100, max_value=250, allow_null=True, required=False)
    smoking = serializers.ChoiceField(SMOKING, allow_blank=True, required=False)
    drinking = serializers.ChoiceField(DRINKING, allow_blank=True, required=False)
    education = serializers.ChoiceField(
        ["primary", "secondary", "technical", "higher", "other"], allow_blank=True, required=False,
    )
    occupation = serializers.ChoiceField(
        ["working", "studying", "both", "looking", "other"], allow_blank=True, required=False,
    )
    preferred_smoking = serializers.ChoiceField(["never"], allow_blank=True, required=False)
    preferred_drinking = serializers.ChoiceField(["never", "occasionally"], allow_blank=True, required=False)
    pets = serializers.ListField(
        child=serializers.ChoiceField(["dog", "cat", "other", "none"]),
        max_length=3, required=False,
    )
    preferred_pets = serializers.ChoiceField(
        ["welcome", "depends", "none"], allow_blank=True, required=False,
    )
    show_pets = serializers.BooleanField(required=False)
    show_details = serializers.BooleanField(required=False)

    def validate_pets(self, pets):
        if "none" in pets and len(pets) > 1:
            raise serializers.ValidationError("Escolha os animais que tem ou indique que não tem animais.")
        return list(dict.fromkeys(pets))

    def validate_ages(self, ages):
        if ages and ages[0] > ages[1]:
            raise serializers.ValidationError("A idade máxima deve ser igual ou superior à mínima.")
        return ages
