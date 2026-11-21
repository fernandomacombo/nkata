import re
import unicodedata

from django.core.exceptions import ValidationError


NAME_PUNCTUATION = " -‐‑'’"
CONTACT_TOKEN = re.compile(r"\b(?:https?://|www\.)\S+|\S*@\S+|\b[\w-]+(?:\.[\w-]+)+\b", re.IGNORECASE)


def _letter_or_mark(character):
    return unicodedata.category(character)[0] in {"L", "M"}


def validate_profile_name(value):
    name = " ".join(value.split())
    if not any(character.isalpha() for character in name) or any(
        not _letter_or_mark(character) and character not in NAME_PUNCTUATION
        for character in name
    ):
        raise ValidationError(
            "Introduza apenas o nome, sem números, contactos ou links.",
            code="invalid_profile_name",
        )


def public_name_from_registration(value):
    without_contacts = CONTACT_TOKEN.sub(" ", unicodedata.normalize("NFC", value))
    letters = "".join(
        character if _letter_or_mark(character) or character in NAME_PUNCTUATION else " "
        for character in without_contacts
    )
    words = (word.strip(NAME_PUNCTUATION) for word in letters.split())
    name = " ".join(word for word in words if any(character.isalpha() for character in word))
    return name or "Membro NKATA"
