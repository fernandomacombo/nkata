import re
import unicodedata
from datetime import date
from heapq import nlargest

from django.db.models import Count
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import VotoPerguntaDiaria
from .profile_api import discovery_profiles
from .serializers import PerfilResumoSerializer
from .user_roles import active_member_profile_for_user


QUESTIONS = (
    (("No primeiro encontro, prefere um café ou um passeio?", "On a first date, coffee or a walk?"),
     (("Um café", "Coffee"), ("Um passeio", "A walk"))),
    (("Para conhecer alguém, prefere conversar ou fazer uma atividade juntos?", "When getting to know someone, would you rather talk or do an activity together?"),
     (("Conversar", "Talk"), ("Fazer uma atividade", "Do an activity"))),
    (("Qual é o seu programa ideal para o fim de semana?", "What is your ideal weekend plan?"),
     (("Descobrir um lugar novo", "Discover somewhere new"), ("Descansar em casa", "Relax at home"))),
    (("O que aprecia mais numa surpresa?", "What do you appreciate more in a surprise?"),
     (("Uma mensagem carinhosa", "A thoughtful message"), ("Um programa a dois", "Something to do together"))),
    (("Prefere combinar um encontro com antecedência ou decidir no próprio dia?", "Would you rather plan a date in advance or decide on the day?"),
     (("Com antecedência", "In advance"), ("No próprio dia", "On the day"))),
)


def normalized_place(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def preferred_ages(value):
    numbers = re.findall(r"\d+", value)
    if len(numbers) == 2:
        minimum, maximum = map(int, numbers)
        if 18 <= minimum <= maximum <= 120:
            return minimum, maximum
    return None


def private_response(data, status=200):
    response = Response(data, status=status)
    add_never_cache_headers(response)
    return response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_suggestions(request):
    profile = active_member_profile_for_user(request.user)
    if not profile:
        return private_response({"detail": "Esta área está disponível apenas para membros."}, 403)

    questionnaire = getattr(profile.pedido, "questionario", None)
    city = normalized_place(questionnaire.cidade_preferida) if questionnaire else ""
    ages = preferred_ages(questionnaire.faixa_etaria_preferida) if questionnaire else None

    def ranked_profiles():
        for candidate in discovery_profiles(request.user, profile).filter(usuario__is_active=True).iterator():
            reasons = []
            score = 0
            if profile.objetivo and candidate.objetivo == profile.objetivo:
                reasons.append("same_goal")
                score += 3
            if city and normalized_place(candidate.cidade) == city:
                reasons.append("preferred_city")
                score += 2
            if ages and ages[0] <= candidate.idade <= ages[1]:
                reasons.append("preferred_age")
                score += 1
            if score:
                yield score, candidate, reasons

    selected = nlargest(5, ranked_profiles(), key=lambda item: (item[0], item[1].pk))
    profiles = [candidate for _, candidate, _ in selected]
    data = PerfilResumoSerializer(profiles, many=True, context={"request": request}).data
    return private_response({
        "results": [
            {**item, "reasons": reasons}
            for item, (_, _, reasons) in zip(data, selected)
        ],
    })


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_daily_question(request):
    if not active_member_profile_for_user(request.user):
        return private_response({"detail": "Esta área está disponível apenas para membros."}, 403)

    today = timezone.localdate()
    question, options = QUESTIONS[(today - date(2026, 11, 21)).days % len(QUESTIONS)]
    votes = VotoPerguntaDiaria.objects.filter(data=today)
    if request.method == "POST":
        if request.data.get("date") != today.isoformat():
            return private_response({"detail": "A pergunta mudou. Atualize a página."}, 409)
        option = request.data.get("option")
        if type(option) is not int or not 0 <= option < len(options):
            return private_response({"detail": "Escolha uma resposta válida."}, 400)
        vote, _ = votes.get_or_create(usuario=request.user, defaults={"data": today, "opcao": option})
        choice = vote.opcao
    else:
        choice = votes.filter(usuario=request.user).values_list("opcao", flat=True).first()

    counts = None
    if choice is not None:
        totals = dict(votes.values("opcao").annotate(total=Count("pk")).values_list("opcao", "total"))
        counts = [totals.get(i, 0) for i in range(len(options))]
    return private_response({
        "date": today.isoformat(),
        "question": dict(zip(("pt", "en"), question)),
        "options": [dict(zip(("pt", "en"), option)) for option in options],
        "choice": choice,
        "counts": counts,
    })
