from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import PedidoEntrada


def image_file(name):
    stream = BytesIO()
    Image.new("RGB", (640, 640), color=(115, 40, 58)).save(stream, format="JPEG")
    stream.seek(0)
    return SimpleUploadedFile(name, stream.read(), content_type="image/jpeg")


class AccessStatusApiTests(TestCase):
    def create_request(self, status="PENDENTE", email="pedido@example.com"):
        return PedidoEntrada.objects.create(
            nome_completo="Pessoa de Teste",
            email=email,
            telefone="+258840000000",
            idade=31,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=image_file("perfil.jpg"),
            foto_extra_1=image_file("extra-1.jpg"),
            foto_extra_2=image_file("extra-2.jpg"),
            foto_extra_3=image_file("extra-3.jpg"),
            bi_frente=image_file("bi-frente.jpg"),
            bi_verso=image_file("bi-verso.jpg"),
            selfie_com_bi=image_file("selfie.jpg"),
            status=status,
            observacao_admin="Nota interna que nunca pode sair pela API.",
        )

    def test_novo_pedido_devolve_codigo_privado(self):
        response = self.client.post(
            "/api/pedir-acesso/",
            data={
                "nome_completo": "Nova Pessoa",
                "email": "nova@example.com",
                "telefone": "+258850000000",
                "idade": 29,
                "cidade": "Matola",
                "genero": "MASCULINO",
                "objetivo": "CASAMENTO_FUTURO",
                "aceita_verificacao": "on",
                "foto_perfil": image_file("novo-perfil.jpg"),
                "foto_extra_1": image_file("novo-extra-1.jpg"),
                "foto_extra_2": image_file("novo-extra-2.jpg"),
                "foto_extra_3": image_file("novo-extra-3.jpg"),
                "bi_frente": image_file("novo-bi-frente.jpg"),
                "bi_verso": image_file("novo-bi-verso.jpg"),
                "selfie_com_bi": image_file("novo-selfie.jpg"),
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        pedido = PedidoEntrada.objects.get(email="nova@example.com")
        self.assertEqual(payload["codigo"], str(pedido.token))
        self.assertIn(str(pedido.token), payload["message"])

    def test_consulta_exige_email_e_codigo(self):
        response = self.client.post(
            "/api/acompanhar-pedido/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_email_ou_codigo_errado_nao_revela_o_pedido(self):
        pedido = self.create_request()

        wrong_email = self.client.post(
            "/api/acompanhar-pedido/",
            data={"email": "outro@example.com", "codigo": str(pedido.token)},
            content_type="application/json",
        )
        wrong_code = self.client.post(
            "/api/acompanhar-pedido/",
            data={
                "email": pedido.email,
                "codigo": "00000000-0000-0000-0000-000000000000",
            },
            content_type="application/json",
        )

        self.assertEqual(wrong_email.status_code, 404)
        self.assertEqual(wrong_code.status_code, 404)
        self.assertEqual(wrong_email.json()["detail"], wrong_code.json()["detail"])

    def test_consulta_apresenta_apenas_dados_seguros(self):
        pedido = self.create_request(status="EM_ANALISE")

        response = self.client.post(
            "/api/acompanhar-pedido/",
            data={"email": pedido.email, "codigo": str(pedido.token)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "EM_ANALISE")
        self.assertEqual(payload["stage"], 2)
        self.assertFalse(payload["can_login"])

        forbidden_fields = {
            "email",
            "telefone",
            "nome_completo",
            "observacao_admin",
            "foto_perfil",
            "bi_frente",
            "bi_verso",
            "selfie_com_bi",
        }
        self.assertTrue(forbidden_fields.isdisjoint(payload.keys()))

    def test_pedido_aprovado_indica_que_pode_entrar(self):
        pedido = self.create_request(status="APROVADO", email="aprovado@example.com")

        response = self.client.post(
            "/api/acompanhar-pedido/",
            data={"email": pedido.email, "codigo": str(pedido.token)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["can_login"])
        self.assertEqual(response.json()["tone"], "success")
