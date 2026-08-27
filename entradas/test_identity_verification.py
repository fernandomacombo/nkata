from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.test import TestCase, override_settings

from .identity_admin import VerificacaoIdentidadeNKATAAdmin
from .identity_api import (
    api_capturar_nkata_id,
    api_estado_nkata_id,
    api_qr_nkata_id,
    identity_email_hash,
)
from .identity_models import VerificacaoIdentidadeNKATA
from .identity_verification_service import (
    finalize_identity_analysis,
    inspect_identity_capture,
)
from .models import PedidoEntrada, PerfilNKATA
from .serializers import PerfilResumoSerializer
from .throttles import IdentityCaptureRateThrottle, IdentityStatusRateThrottle


def textured_image(name, width=900, height=650):
    stream = BytesIO()
    image = Image.new("RGB", (width, height), color=(238, 225, 203))
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 24):
        draw.line((x, 0, width - x // 2, height), fill=(90, 45, 58), width=3)
    for y in range(0, height, 30):
        draw.line((0, y, width, height - y // 2), fill=(54, 91, 75), width=2)
    image.save(stream, format="JPEG", quality=94)
    stream.seek(0)
    return SimpleUploadedFile(name, stream.read(), content_type="image/jpeg")


def accepted_result(capture_type):
    is_selfie = capture_type.startswith("selfie")
    return {
        "accepted": True,
        "score": 96,
        "checks": {
            "resolution": True,
            "brightness": True,
            "contrast": True,
            "sharpness": True,
            "glare": True,
            **({"single_face": True} if is_selfie else {}),
        },
        "messages": [],
        "metrics": {
            "width": 900,
            "height": 650,
            "brightness": 120,
            "contrast": 44,
            "sharpness": 180,
            "glare_ratio": 0.01,
            "faces": 1 if is_selfie else None,
        },
        "sha256": f"sha-{capture_type}",
    }


class NkataIdApiTests(TestCase):
    def create_session(self, email="nkata-id@example.com"):
        response = self.client.post(
            "/api/nkata-id/sessoes/",
            data={
                "email": email,
                "idade": 29,
                "aceita_biometria": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.json())
        return response.json()

    def test_session_requires_adult_age_and_explicit_consent(self):
        response = self.client.post(
            "/api/nkata-id/sessoes/",
            data={"email": "young@example.com", "idade": 17},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("idade", response.json()["errors"])
        self.assertIn("aceita_biometria", response.json()["errors"])

    def test_qr_and_public_status_do_not_expose_personal_data(self):
        payload = self.create_session()
        token = payload["token"]

        status_response = self.client.get(f"/api/nkata-id/sessoes/{token}/")
        qr_response = self.client.get(f"/api/nkata-id/sessoes/{token}/qr/")

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(qr_response["Content-Type"], "image/png")
        forbidden = {"email", "email_hash", "idade_declarada", "pedido"}
        self.assertTrue(forbidden.isdisjoint(status_response.json().keys()))

    def test_status_polling_does_not_consume_capture_rate_limit(self):
        self.assertIn(
            IdentityStatusRateThrottle,
            api_estado_nkata_id.cls.throttle_classes,
        )
        self.assertIn(
            IdentityStatusRateThrottle,
            api_qr_nkata_id.cls.throttle_classes,
        )
        self.assertIn(
            IdentityCaptureRateThrottle,
            api_capturar_nkata_id.cls.throttle_classes,
        )
        self.assertNotEqual(
            IdentityStatusRateThrottle.scope,
            IdentityCaptureRateThrottle.scope,
        )

    @patch("entradas.identity_api.inspect_identity_capture")
    def test_capture_flow_finishes_without_requiring_human_for_quality_checks(self, inspect):
        inspect.side_effect = lambda _upload, capture_type: accepted_result(capture_type)
        payload = self.create_session()
        token = payload["token"]

        for capture_type in (
            "bi_frente",
            "bi_verso",
            "selfie_ao_vivo",
            "selfie_desafio",
        ):
            response = self.client.post(
                f"/api/nkata-id/sessoes/{token}/capturas/{capture_type}/",
                data={"imagem": textured_image(f"{capture_type}.jpg")},
            )
            self.assertEqual(response.status_code, 200, response.json())

        result = response.json()
        self.assertTrue(result["capture_complete"])
        self.assertTrue(result["can_submit"])
        self.assertEqual(result["status"], "REVISAO")
        self.assertTrue(result["liveness_confirmed"])

    def test_low_quality_image_is_rejected_with_actionable_feedback(self):
        uniform = BytesIO()
        Image.new("RGB", (320, 240), color=(10, 10, 10)).save(uniform, format="JPEG")
        uniform.seek(0)
        result = inspect_identity_capture(
            SimpleUploadedFile("escura.jpg", uniform.read(), content_type="image/jpeg"),
            "bi_frente",
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(result["messages"])
        self.assertFalse(result["checks"]["resolution"])

    @patch("entradas.identity_api.inspect_identity_capture")
    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1)
    def test_completed_nkata_id_can_replace_legacy_document_uploads(self, inspect):
        inspect.side_effect = lambda _upload, capture_type: accepted_result(capture_type)
        payload = self.create_session(email="novo-fluxo@example.com")
        token = payload["token"]
        for capture_type in VerificacaoIdentidadeNKATA.CAPTURE_FIELDS:
            self.client.post(
                f"/api/nkata-id/sessoes/{token}/capturas/{capture_type}/",
                data={"imagem": textured_image(f"{capture_type}.jpg")},
            )

        response = self.client.post(
            "/api/pedir-acesso/",
            data={
                "nome_completo": "Pessoa Novo Fluxo",
                "email": "novo-fluxo@example.com",
                "telefone": "+258840000001",
                "idade": 29,
                "cidade": "Vilankulo",
                "genero": "FEMININO",
                "objetivo": "RELACIONAMENTO_SERIO",
                "aceita_verificacao": "on",
                "nkata_id_token": token,
                "foto_perfil": textured_image("perfil.jpg"),
                "foto_extra_1": textured_image("extra-1.jpg"),
                "foto_extra_2": textured_image("extra-2.jpg"),
                "foto_extra_3": textured_image("extra-3.jpg"),
            },
        )

        self.assertEqual(response.status_code, 201, response.json())
        pedido = PedidoEntrada.objects.get(email="novo-fluxo@example.com")
        verification = VerificacaoIdentidadeNKATA.objects.get(token=token)
        self.assertEqual(verification.pedido_id, pedido.id)
        self.assertFalse(bool(pedido.bi_frente))

    def test_identity_token_is_bound_to_the_same_email(self):
        payload = self.create_session(email="owner@example.com")
        token = payload["token"]
        response = self.client.post(
            "/api/pedir-acesso/",
            data={"email": "attacker@example.com", "nkata_id_token": token},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("nkata_id_token", response.json()["errors"])

    def test_identity_evidence_is_available_only_to_staff(self):
        verification = VerificacaoIdentidadeNKATA.objects.create(
            email_hash=identity_email_hash("private@example.com"),
            idade_declarada=30,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            bi_frente=textured_image("private-bi.jpg"),
        )
        member = User.objects.create_user(username="member-id", password="Strong123")
        staff = User.objects.create_user(
            username="staff-id", password="Strong123", is_staff=True
        )
        url = f"/api/admin/nkata-id/{verification.id}/media/bi_frente/"

        self.client.force_login(member)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(staff)
        allowed = self.client.get(url)
        try:
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed["Cache-Control"], "no-store")
        finally:
            allowed.close()

    @patch("entradas.identity_api.inspect_identity_capture")
    def test_staff_can_request_and_user_can_complete_a_new_capture(self, inspect):
        inspect.side_effect = lambda _upload, capture_type: accepted_result(capture_type)
        pedido = PedidoEntrada.objects.create(
            nome_completo="Pessoa Recaptura",
            email="recaptura@example.com",
            telefone="840000009",
            idade=31,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=textured_image("recaptura-perfil.jpg"),
            foto_extra_1=textured_image("recaptura-1.jpg"),
            foto_extra_2=textured_image("recaptura-2.jpg"),
            foto_extra_3=textured_image("recaptura-3.jpg"),
        )
        verification = VerificacaoIdentidadeNKATA.objects.create(
            pedido=pedido,
            email_hash=identity_email_hash(pedido.email),
            idade_declarada=pedido.idade,
            aceita_biometria=True,
            desafio_selfie="Sorria ligeiramente.",
            status="REVISAO",
            bi_frente=textured_image("antiga-frente.jpg"),
            bi_verso=textured_image("antigo-verso.jpg"),
            selfie_ao_vivo=textured_image("antiga-selfie.jpg"),
            selfie_desafio=textured_image("antigo-desafio.jpg"),
        )
        staff = User.objects.create_user(
            username="staff-recapture", password="Strong123", is_staff=True
        )
        request = RequestFactory().post("/admin/")
        request.user = staff
        model_admin = VerificacaoIdentidadeNKATAAdmin(
            VerificacaoIdentidadeNKATA, admin.site
        )

        model_admin.pedir_nova_captura(
            request, VerificacaoIdentidadeNKATA.objects.filter(pk=verification.pk)
        )
        verification.refresh_from_db()
        self.assertEqual(verification.status, "REPETIR")
        self.assertFalse(verification.capturas_completas)

        for capture_type in VerificacaoIdentidadeNKATA.CAPTURE_FIELDS:
            response = self.client.post(
                f"/api/nkata-id/sessoes/{verification.token}/capturas/{capture_type}/",
                data={"imagem": textured_image(f"nova-{capture_type}.jpg")},
            )
            self.assertEqual(response.status_code, 200, response.json())

        verification.refresh_from_db()
        self.assertTrue(verification.capturas_completas)
        self.assertEqual(verification.status, "REVISAO")


class NkataIdDecisionTests(TestCase):
    @patch("entradas.identity_verification_service._aws_face_similarity")
    def test_high_confidence_provider_can_approve_automatically(self, similarity):
        similarity.return_value = Decimal("96.40")
        checks = {
            capture_type: accepted_result(capture_type)
            for capture_type in VerificacaoIdentidadeNKATA.CAPTURE_FIELDS
        }
        verification = VerificacaoIdentidadeNKATA.objects.create(
            email_hash=identity_email_hash("automatic@example.com"),
            idade_declarada=33,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            bi_frente="nkata-id/front.jpg",
            bi_verso="nkata-id/back.jpg",
            selfie_ao_vivo="nkata-id/selfie.jpg",
            selfie_desafio="nkata-id/challenge.jpg",
            verificacoes_imagem=checks,
        )
        finalize_identity_analysis(verification)
        verification.refresh_from_db()
        self.assertEqual(verification.status, "APROVADA")
        self.assertEqual(verification.decisao_origem, "AUTOMATICA")
        self.assertEqual(verification.risco, "BAIXO")

    def test_public_badge_uses_nkata_id_decision_when_present(self):
        pedido = PedidoEntrada.objects.create(
            nome_completo="Pessoa Verificada",
            email="badge@example.com",
            telefone="840000000",
            idade=30,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=textured_image("badge-profile.jpg"),
            foto_extra_1=textured_image("badge-1.jpg"),
            foto_extra_2=textured_image("badge-2.jpg"),
            foto_extra_3=textured_image("badge-3.jpg"),
            status="APROVADO",
        )
        profile = PerfilNKATA.objects.create(
            pedido=pedido,
            nome_publico="Perfil",
            cidade="Maputo",
            idade=30,
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Uma descrição completa para o perfil.",
            o_que_valoriza="Respeito e compromisso.",
            o_que_nao_aceita="Mentiras.",
        )
        verification = VerificacaoIdentidadeNKATA.objects.create(
            pedido=pedido,
            email_hash=identity_email_hash(pedido.email),
            idade_declarada=pedido.idade,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            status="REVISAO",
        )
        self.assertFalse(PerfilResumoSerializer(profile).data["verificado"])
        verification.status = "APROVADA"
        verification.save(update_fields=["status"])
        PerfilNKATA.objects.filter(pk=profile.pk).update(status="ATIVO", visivel=True)
        profile = PerfilNKATA.objects.select_related(
            "pedido__verificacao_identidade"
        ).get(pk=profile.pk)
        self.assertTrue(
            PerfilResumoSerializer(profile).data["verificado"],
            (
                profile.pedido.status,
                profile.status,
                profile.visivel,
                profile.pedido.verificacao_identidade.status,
            ),
        )
