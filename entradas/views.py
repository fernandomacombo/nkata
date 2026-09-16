from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EditarPerfilForm, PedidoEntradaForm, QuestionarioEntradaForm
from .models import AcaoPerfil, MensagemPerfil, PedidoEntrada, PerfilNKATA, MatchPerfil, MensagemMatch

from .models import PerfilNKATA, DenunciaPerfil












def criar_match_se_mutuo(perfil_alvo, usuario_atual, tipo):
    if tipo not in ["INTERESSE", "GOSTAR"]:
        return None

    if not usuario_atual.is_authenticated:
        return None

    perfil_usuario = getattr(usuario_atual, "perfil_nkata", None)

    if not perfil_usuario:
        return None

    if perfil_usuario.id == perfil_alvo.id:
        return None

    acao_mutua_existe = AcaoPerfil.objects.filter(
        perfil=perfil_usuario,
        usuario=perfil_alvo.usuario,
        tipo=tipo
    ).exists()

    if not acao_mutua_existe:
        return None

    perfil_1, perfil_2 = sorted(
        [perfil_usuario, perfil_alvo],
        key=lambda perfil: perfil.id
    )

    match, criado = MatchPerfil.objects.get_or_create(
        perfil_1=perfil_1,
        perfil_2=perfil_2,
        defaults={
            "tipo_origem": tipo,
            "status": "ATIVO",
        }
    )

    if not criado and match.status != "ATIVO":
        match.status = "ATIVO"
        match.tipo_origem = tipo
        match.save(update_fields=["status", "tipo_origem", "atualizado_em"])

    return match




def usuario_tem_acesso_ao_match(user, match):
    if not user.is_authenticated:
        return False

    perfil = getattr(user, "perfil_nkata", None)

    if not perfil:
        return False

    return match.perfil_1_id == perfil.id or match.perfil_2_id == perfil.id







def home(request):
    return render(request, "entradas/home.html")


def solicitar_entrada(request):
    if request.method == "POST":
        form = PedidoEntradaForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Recebemos o seu pedido de entrada. A equipa NKATA irá analisar os seus dados."
            )
            return redirect("entradas:sucesso")
    else:
        form = PedidoEntradaForm()

    return render(request, "entradas/solicitar_entrada.html", {
        "form": form
    })


def sucesso(request):
    return render(request, "entradas/sucesso.html")


def _get_or_create_user_for_pedido(pedido):
    user = User.objects.filter(email__iexact=pedido.email).first()

    if user:
        return user

    base_username = pedido.email.split("@")[0][:80] or f"nkata_{pedido.id}"
    username = base_username
    count = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{count}"
        count += 1

    user = User.objects.create_user(
        username=username,
        email=pedido.email,
        password=None,
        first_name=pedido.nome_completo[:150],
    )
    user.set_unusable_password()
    user.save()

    return user


def responder_questionario(request, token):
    pedido = get_object_or_404(PedidoEntrada, token=token)

    if pedido.status != "APROVADO":
        return render(request, "entradas/acesso_negado.html", {
            "pedido": pedido
        })

    questionario_existente = getattr(pedido, "questionario", None)

    if request.method == "POST":
        form = QuestionarioEntradaForm(
            request.POST,
            instance=questionario_existente
        )

        if form.is_valid():
            questionario = form.save(commit=False)
            questionario.pedido = pedido
            questionario.save()

            if not request.session.session_key:
                request.session.create()

            usuario = _get_or_create_user_for_pedido(pedido)

            perfil, criado = PerfilNKATA.objects.get_or_create(
                pedido=pedido,
                defaults={
                    "usuario": usuario,
                    "nome_publico": pedido.nome_completo,
                    "cidade": pedido.cidade,
                    "idade": pedido.idade,
                    "genero": pedido.genero,
                    "objetivo": pedido.objetivo,
                    "sobre_si": questionario.sobre_si,
                    "o_que_valoriza": questionario.o_que_valoriza,
                    "o_que_nao_aceita": questionario.o_que_nao_aceita,
                    "status": "ATIVO",
                    "visivel": True,
                    "foto_destaque_publico_aprovada": True,
                    "owner_session_key": request.session.session_key,
                }
            )

            if not criado:
                perfil.usuario = usuario
                perfil.nome_publico = pedido.nome_completo
                perfil.cidade = pedido.cidade
                perfil.idade = pedido.idade
                perfil.genero = pedido.genero
                perfil.objetivo = pedido.objetivo
                perfil.sobre_si = questionario.sobre_si
                perfil.o_que_valoriza = questionario.o_que_valoriza
                perfil.o_que_nao_aceita = questionario.o_que_nao_aceita
                perfil.status = "ATIVO"
                perfil.visivel = True

                if not perfil.owner_session_key:
                    perfil.owner_session_key = request.session.session_key

                perfil.save()

            return redirect("entradas:criar_senha", token=pedido.token)
    else:
        form = QuestionarioEntradaForm(instance=questionario_existente)

    return render(request, "entradas/questionario.html", {
        "form": form,
        "pedido": pedido
    })


def questionario_sucesso(request):
    return render(request, "entradas/questionario_sucesso.html")


def criar_senha(request, token):
    pedido = get_object_or_404(PedidoEntrada, token=token)

    if pedido.status != "APROVADO":
        return render(request, "entradas/acesso_negado.html", {
            "pedido": pedido
        })

    perfil = getattr(pedido, "perfil", None)

    if not perfil:
        messages.error(request, "Ainda não existe perfil associado a este pedido.")
        return redirect("entradas:home")

    usuario = perfil.usuario or _get_or_create_user_for_pedido(pedido)

    if not perfil.usuario:
        perfil.usuario = usuario
        perfil.save(update_fields=["usuario"])

    if request.method == "POST":
        senha = request.POST.get("senha", "").strip()
        confirmar_senha = request.POST.get("confirmar_senha", "").strip()

        if len(senha) < 6:
            return render(request, "entradas/criar_senha.html", {
                "pedido": pedido,
                "perfil": perfil,
                "erro_senha": "A senha deve ter pelo menos 6 caracteres.",
            })

        elif senha != confirmar_senha:
            return render(request, "entradas/criar_senha.html", {
                "pedido": pedido,
                "perfil": perfil,
                "erro_senha": "As senhas não coincidem.",
            })

        else:
            usuario.set_password(senha)
            usuario.save()

            login(request, usuario)

            messages.success(request, "Senha criada com sucesso. Bem-vindo ao NKATA.")
            return redirect("entradas:minha_conta")

    return render(request, "entradas/criar_senha.html", {
        "pedido": pedido,
        "perfil": perfil,
    })


def entrar(request):
    if request.user.is_authenticated:
        perfil = getattr(request.user, "perfil_nkata", None)

        if perfil:
            return redirect("entradas:minha_conta")

        return redirect("entradas:listar_perfis")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        senha = request.POST.get("senha", "").strip()

        user_obj = User.objects.filter(email__iexact=email).first()

        if not user_obj:
            messages.error(request, "Email ou senha inválidos.")
            return render(request, "entradas/login.html")

        user = authenticate(
            request,
            username=user_obj.username,
            password=senha
        )

        if user is None:
            messages.error(request, "Email ou senha inválidos.")
            return render(request, "entradas/login.html")

        login(request, user)

        perfil = getattr(user, "perfil_nkata", None)

        if perfil:
            return redirect("entradas:minha_conta")

        return redirect("entradas:listar_perfis")

    return render(request, "entradas/login.html")


def sair(request):
    logout(request)
    return redirect("entradas:home")


def listar_perfis(request):
    perfis = (
        PerfilNKATA.objects
        .filter(status="ATIVO", visivel=True)
        .select_related("pedido", "usuario")
        .annotate(
            total_gostos=Count(
                "acoes_recebidas",
                filter=Q(acoes_recebidas__tipo="GOSTAR")
            ),
            total_seguidores=Count(
                "acoes_recebidas",
                filter=Q(acoes_recebidas__tipo="SEGUIR")
            ),
            total_interesses=Count(
                "acoes_recebidas",
                filter=Q(acoes_recebidas__tipo="INTERESSE")
            ),
        )
    )

    return render(request, "entradas/perfis.html", {
        "perfis": perfis
    })


def detalhe_perfil(request, perfil_id):
    perfil = get_object_or_404(
        PerfilNKATA.objects.select_related("pedido", "usuario"),
        id=perfil_id,
        status="ATIVO",
        visivel=True
    )

    acoes_feitas = []

    if request.session.session_key:
        acoes_feitas = list(
            AcaoPerfil.objects.filter(
                perfil=perfil,
                session_key=request.session.session_key
            ).values_list("tipo", flat=True)
        )

    total_gostos = AcaoPerfil.objects.filter(perfil=perfil, tipo="GOSTAR").count()
    total_seguidores = AcaoPerfil.objects.filter(perfil=perfil, tipo="SEGUIR").count()
    total_interesses = AcaoPerfil.objects.filter(perfil=perfil, tipo="INTERESSE").count()

    is_owner = (
        request.user.is_authenticated
        and perfil.usuario_id
        and perfil.usuario_id == request.user.id
    )

    return render(request, "entradas/perfil_detalhe.html", {
        "perfil": perfil,
        "acoes_feitas": acoes_feitas,
        "total_gostos": total_gostos,
        "total_seguidores": total_seguidores,
        "total_interesses": total_interesses,
        "is_owner": is_owner,
    })


@require_POST
def registrar_acao_perfil(request, perfil_id, tipo):
    perfil = get_object_or_404(
        PerfilNKATA,
        id=perfil_id,
        status="ATIVO",
        visivel=True
    )

    tipos_validos = ["INTERESSE", "GOSTAR", "SEGUIR"]

    if tipo not in tipos_validos:
        return JsonResponse({
            "ok": False,
            "message": "Ação inválida."
        }, status=400)

    if request.user.is_authenticated and perfil.usuario_id == request.user.id:
        return JsonResponse({
            "ok": False,
            "owner": True,
            "message": "Não pode realizar ações no seu próprio perfil."
        }, status=403)

    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        acao_existente = AcaoPerfil.objects.filter(
            perfil=perfil,
            tipo=tipo,
            usuario=request.user
        ).first()
    else:
        acao_existente = AcaoPerfil.objects.filter(
            perfil=perfil,
            tipo=tipo,
            session_key=request.session.session_key
        ).first()

    if acao_existente:
        acao_existente.delete()
        ativo = False
        message = "Ação removida."
    else:
        AcaoPerfil.objects.create(
            perfil=perfil,
            tipo=tipo,
            usuario=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key
        )

        match = criar_match_se_mutuo(
            perfil_alvo=perfil,
            usuario_atual=request.user,
            tipo=tipo
        )

        ativo = True

        if match:
            message = "Match criado! Também existe interesse do outro lado."
        else:
            message = "Ação registada."     

    total_gostos = AcaoPerfil.objects.filter(perfil=perfil, tipo="GOSTAR").count()
    total_seguidores = AcaoPerfil.objects.filter(perfil=perfil, tipo="SEGUIR").count()
    total_interesses = AcaoPerfil.objects.filter(perfil=perfil, tipo="INTERESSE").count()

    return JsonResponse({
        "ok": True,
        "ativo": ativo,
        "tipo": tipo,
        "total_gostos": total_gostos,
        "total_seguidores": total_seguidores,
        "total_interesses": total_interesses,
        "message": message,
        "match": bool(match) if ativo else False,
    })


@require_POST
def enviar_mensagem_perfil(request, perfil_id, tipo):
    perfil = get_object_or_404(
        PerfilNKATA,
        id=perfil_id,
        status="ATIVO",
        visivel=True
    )

    tipos_validos = [
        "GOSTEI_DO_PERFIL",
        "CONVERSAR_COM_CALMA",
        "ALGO_SERIO",
    ]

    if tipo not in tipos_validos:
        return JsonResponse({
            "ok": False,
            "message": "Mensagem inválida."
        }, status=400)

    if request.user.is_authenticated and perfil.usuario_id == request.user.id:
        return JsonResponse({
            "ok": False,
            "owner": True,
            "message": "Não pode enviar mensagem para o seu próprio perfil."
        }, status=403)

    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        mensagem, criada = MensagemPerfil.objects.get_or_create(
            perfil=perfil,
            tipo=tipo,
            usuario=request.user,
            defaults={
                "session_key": request.session.session_key
            }
        )
    else:
        mensagem, criada = MensagemPerfil.objects.get_or_create(
            perfil=perfil,
            tipo=tipo,
            session_key=request.session.session_key
        )

    total_mensagens = MensagemPerfil.objects.filter(perfil=perfil).count()

    if criada:
        message = "Mensagem enviada com sucesso."
    else:
        message = "Esta mensagem já foi enviada."

    return JsonResponse({
        "ok": True,
        "criada": criada,
        "total_mensagens": total_mensagens,
        "message": message,
    })


@login_required(login_url="entradas:entrar")
def perfil_interacoes(request, perfil_id):
    perfil = get_object_or_404(
        PerfilNKATA.objects.select_related("pedido", "usuario"),
        id=perfil_id,
        status="ATIVO",
        visivel=True
    )

    if not perfil.usuario_id or perfil.usuario_id != request.user.id:
        return render(request, "entradas/perfil_acesso_negado.html", {
            "perfil": perfil
        })

    gostos = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="GOSTAR"
    ).select_related("usuario", "usuario__perfil_nkata")

    seguidores = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="SEGUIR"
    ).select_related("usuario", "usuario__perfil_nkata")

    interesses = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="INTERESSE"
    ).select_related("usuario", "usuario__perfil_nkata")

    mensagens = MensagemPerfil.objects.filter(
        perfil=perfil
    ).select_related("usuario", "usuario__perfil_nkata")

    return render(request, "entradas/perfil_interacoes.html", {
        "perfil": perfil,
        "gostos": gostos,
        "seguidores": seguidores,
        "interesses": interesses,
        "mensagens": mensagens,
        "total_gostos": gostos.count(),
        "total_seguidores": seguidores.count(),
        "total_interesses": interesses.count(),
        "total_mensagens": mensagens.count(),
    })






@login_required(login_url="entradas:entrar")
def minha_conta(request):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        messages.error(request, "Não encontramos um perfil NKATA associado à sua conta.")
        return redirect("entradas:listar_perfis")

    total_gostos = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="GOSTAR"
    ).count()

    total_seguidores = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="SEGUIR"
    ).count()

    total_interesses = AcaoPerfil.objects.filter(
        perfil=perfil,
        tipo="INTERESSE"
    ).count()

    total_mensagens = MensagemPerfil.objects.filter(
        perfil=perfil
    ).count()

    matches_do_usuario = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO"
    )

    total_matches = matches_do_usuario.count()

    total_mensagens_nao_lidas = MensagemMatch.objects.filter(
        match__in=matches_do_usuario,
        lida=False
    ).exclude(
        remetente=request.user
    ).count()

    return render(request, "entradas/minha_conta.html", {
        "perfil": perfil,
        "total_gostos": total_gostos,
        "total_seguidores": total_seguidores,
        "total_interesses": total_interesses,
        "total_mensagens": total_mensagens,
        "total_matches": total_matches,
        "total_mensagens_nao_lidas": total_mensagens_nao_lidas,
    })






@login_required(login_url="entradas:entrar")
def editar_perfil(request):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        messages.error(request, "Não encontramos um perfil NKATA associado à sua conta.")
        return redirect("entradas:listar_perfis")

    if request.method == "POST":
        form = EditarPerfilForm(request.POST, instance=perfil)

        if form.is_valid():
            form.save()
            messages.success(request, "O seu perfil foi atualizado com sucesso.")
            return redirect("entradas:minha_conta")
    else:
        form = EditarPerfilForm(instance=perfil)

    return render(request, "entradas/editar_perfil.html", {
        "form": form,
        "perfil": perfil,
    })






@login_required(login_url="entradas:entrar")
def alternar_visibilidade_perfil(request):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        messages.error(request, "Não encontramos um perfil NKATA associado à sua conta.")
        return redirect("entradas:home")

    if request.method != "POST":
        return redirect("entradas:minha_conta")

    if perfil.status == "BLOQUEADO":
        messages.error(request, "Este perfil está bloqueado e não pode ser alterado.")
        return redirect("entradas:minha_conta")

    if perfil.visivel:
        perfil.visivel = False
        perfil.status = "PAUSADO"
        messages.success(request, "O seu perfil foi pausado e deixou de aparecer publicamente.")
    else:
        perfil.visivel = True
        perfil.status = "ATIVO"
        messages.success(request, "O seu perfil foi reativado e voltou a aparecer publicamente.")

    perfil.save(update_fields=["visivel", "status"])

    return redirect("entradas:minha_conta")







def denunciar_perfil(request, perfil_id):
    if request.method != "POST":
        return JsonResponse({
            "ok": False,
            "message": "Método inválido."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "ok": False,
            "message": "Para denunciar um perfil, precisa primeiro entrar na sua conta NKATA."
        }, status=401)

    perfil = get_object_or_404(
        PerfilNKATA,
        id=perfil_id,
        status="ATIVO",
        visivel=True
    )

    if perfil.usuario == request.user:
        return JsonResponse({
            "ok": False,
            "message": "Não pode denunciar o seu próprio perfil."
        }, status=400)

    motivo = request.POST.get("motivo", "").strip()
    detalhes = request.POST.get("detalhes", "").strip()

    motivos_validos = [item[0] for item in DenunciaPerfil.MOTIVOS]

    if motivo not in motivos_validos:
        return JsonResponse({
            "ok": False,
            "message": "Selecione um motivo válido."
        }, status=400)

    DenunciaPerfil.objects.create(
        denunciante=request.user,
        perfil=perfil,
        motivo=motivo,
        detalhes=detalhes
    )

    return JsonResponse({
        "ok": True,
        "message": "Denúncia enviada. A equipa NKATA irá analisar."
    })






@login_required
def meus_matches(request):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        messages.error(request, "Não encontramos um perfil NKATA associado à sua conta.")
        return redirect("entradas:home")

    matches = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO"
    ).select_related(
        "perfil_1",
        "perfil_2",
        "perfil_1__usuario",
        "perfil_2__usuario",
    )

    matches_processados = []

    for match in matches:
        outro_perfil = match.perfil_2 if match.perfil_1_id == perfil.id else match.perfil_1

        mensagens_nao_lidas = match.mensagens.filter(
            lida=False
        ).exclude(
            remetente=request.user
        ).count()

        ultima_mensagem = match.mensagens.order_by("-criado_em").first()

        matches_processados.append({
            "match": match,
            "outro_perfil": outro_perfil,
            "mensagens_nao_lidas": mensagens_nao_lidas,
            "ultima_mensagem": ultima_mensagem,
        })

    return render(request, "entradas/meus_matches.html", {
        "perfil": perfil,
        "matches_processados": matches_processados,
        "total_matches": matches.count(),
    })






@login_required
def conversa_match(request, match_id):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        messages.error(request, "Não encontramos um perfil NKATA associado à sua conta.")
        return redirect("entradas:home")

    match = get_object_or_404(
        MatchPerfil.objects.select_related(
            "perfil_1",
            "perfil_2",
            "perfil_1__usuario",
            "perfil_2__usuario",
        ),
        id=match_id,
        status="ATIVO"
    )

    if not usuario_tem_acesso_ao_match(request.user, match):
        return render(request, "entradas/perfil_acesso_negado.html", {
            "perfil": perfil
        })

    outro_perfil = match.perfil_2 if match.perfil_1_id == perfil.id else match.perfil_1

    if request.method == "POST":
        texto = request.POST.get("texto", "").strip()

        if not texto:
            messages.error(request, "Escreva uma mensagem antes de enviar.")
            return redirect("entradas:conversa_match", match_id=match.id)

        if len(texto) > 1200:
            messages.error(request, "A mensagem é muito longa.")
            return redirect("entradas:conversa_match", match_id=match.id)

        MensagemMatch.objects.create(
            match=match,
            remetente=request.user,
            texto=texto
        )

        return redirect("entradas:conversa_match", match_id=match.id)

    mensagens_match = match.mensagens.select_related(
        "remetente",
        "remetente__perfil_nkata"
    )

    match.mensagens.exclude(
        remetente=request.user
    ).filter(
        lida=False
    ).update(
        lida=True
    )

    return render(request, "entradas/conversa_match.html", {
        "perfil": perfil,
        "match": match,
        "outro_perfil": outro_perfil,
        "mensagens_match": mensagens_match,
    })
