from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import PedidoEntrada, PerfilNKATA, QuestionarioEntrada


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-test", content_type="image/jpeg")


class SavedProfilesPrivacyTests(TestCase):
    def create_profile(self, email, name):
        user = User.objects.create_user(
            username=email.split("@")[0],
            email=email,
            password="SenhaForte123",
            first_name=name,
        )
        pedido = PedidoEntrada.objects.create(
            nome_completo=name,
            email=email,
            telefone="840000000",
            idade=30,
            cidade="Maputo",
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=uploaded_file(f"{name}-perfil.jpg"),
            foto_extra_1=uploaded_file(f"{name}-extra-1.jpg"),
            foto_extra_2=uploaded_file(f"{name}-extra-2.jpg"),
            foto_extra_3=uploaded_file(f"{name}-extra-3.jpg"),
            bi_frente=uploaded_file(f"{name}-bi-frente.jpg"),
            bi_verso=uploaded_file(f"{name}-bi-verso.jpg"),
            selfie_com_bi=uploaded_file(f"{name}-selfie.jpg"),
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(
            pedido=pedido,
            disponibilidade="SIM",
            tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM",
            cidade_preferida="Maputo",
            faixa_etaria_preferida="25 a 40 anos",
            sobre_si="Procuro conhecer alguém com calma e intenção.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            aceita_regras=True,
        )
        perfil = PerfilNKATA.objects.create(
            pedido=pedido,
            usuario=user,
            nome_publico=name,
            cidade="Maputo",
            idade=30,
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Sou uma pessoa tranquila e gosto de conversas sinceras.",
            o_que_valoriza="Respeito, honestidade e compromisso.",
            o_que_nao_aceita="Mentiras e falta de respeito.",
            status="ATIVO",
            visivel=True,
        )
        return user, perfil

    def test_visitante_nao_pode_ver_guardados(self):
        response = self.client.get("/api/minha-conta/guardados/")
        self.assertIn(response.status_code, [401, 403])

    def test_guardados_sao_isolados_por_conta(self):
        user_a, _ = self.create_profile("marta@example.com", "Marta")
        user_b, _ = self.create_profile("matola@example.com", "Matola")
        _, profile_target = self.create_profile("alvo@example.com", "Alvo")

        self.client.force_login(user_a)
        save_response = self.client.post(
            f"/api/perfis/{profile_target.id}/guardar/"
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(save_response.json()["active"])

        list_a = self.client.get("/api/minha-conta/guardados/")
        self.assertEqual(list_a.status_code, 200)
        self.assertEqual(list_a.json()["count"], 1)

        self.client.force_login(user_b)
        list_b = self.client.get("/api/minha-conta/guardados/")
        self.assertEqual(list_b.status_code, 200)
        self.assertEqual(list_b.json()["count"], 0)

    def test_remover_guardado_so_altera_a_conta_atual(self):
        user, _ = self.create_profile("pessoa@example.com", "Pessoa")
        _, profile_target = self.create_profile("destino@example.com", "Destino")
        self.client.force_login(user)

        self.client.post(f"/api/perfis/{profile_target.id}/guardar/")
        remove_response = self.client.post(
            f"/api/perfis/{profile_target.id}/guardar/"
        )

        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(remove_response.json()["active"])
        result = self.client.get("/api/minha-conta/guardados/")
        self.assertEqual(result.json()["count"], 0)
