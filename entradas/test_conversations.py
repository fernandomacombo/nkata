from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import AcaoPerfil, Conversa, MatchPerfil, MensagemMatch, PedidoConversa, PedidoEntrada, PerfilNKATA, QuestionarioEntrada
from .notification_models import NotificacaoNKATA


def profile(i):
    user = get_user_model().objects.create_user(f"member{i}", password="fixture-password")
    pedido = PedidoEntrada.objects.create(nome_completo=f"Membro {i}", email=f"{i}@example.test",
                                         telefone=f"84000000{i}", foto_perfil="perfil.jpg", idade=30, status="APROVADO")
    QuestionarioEntrada.objects.create(pedido=pedido)
    return PerfilNKATA.objects.create(usuario=user, pedido=pedido, idade=30, status="ATIVO", nome_publico=f"Membro {i}")


class ConversationTests(TestCase):
    def setUp(self):
        self.a, self.b, self.c = [profile(i) for i in range(3)]

    def ask(self, sender, recipient):
        self.client.force_login(sender.usuario)
        return self.client.post(f"/api/chats/pedir/{recipient.pk}/")

    def decide(self, actor, pk, decision):
        self.client.force_login(actor.usuario)
        return self.client.post(f"/api/chats/pedidos/{pk}/", {"decisao": decision})

    def test_reciprocal_and_repeated_requests(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.ask(self.a, self.b)
            self.assertEqual(first.status_code, 201, first.content)
            self.assertEqual(self.ask(self.a, self.b).json()["id"], first.json()["id"])
            self.assertEqual(self.ask(self.b, self.a).json()["estado"], "ACEITE")
            self.assertEqual(self.ask(self.a, self.b).json()["estado"], "ACEITE")
        self.assertEqual(Conversa.objects.count(), 1)
        self.assertFalse(MatchPerfil.objects.exists())
        self.assertEqual(NotificacaoNKATA.objects.filter(tipo="PEDIDO_CHAT").count(), 1)

    def test_only_recipient_decides_and_cooldown_starts_at_refusal(self):
        pk = self.ask(self.a, self.b).json()["id"]
        self.assertEqual(self.decide(self.c, pk, "ACEITE").status_code, 404)
        self.assertEqual(self.decide(self.a, pk, "ACEITE").status_code, 404)
        self.assertEqual(self.decide(self.b, pk, "RECUSADO").status_code, 200)
        self.assertEqual(self.ask(self.a, self.b).status_code, 409)
        PedidoConversa.objects.update(decidido_em=timezone.now()-timedelta(days=30))
        self.assertEqual(self.ask(self.a, self.b).status_code, 201)

    def test_expired_request_cannot_be_accepted(self):
        pk = self.ask(self.a, self.b).json()["id"]
        PedidoConversa.objects.update(expira_em=timezone.now())
        self.assertEqual(self.decide(self.b, pk, "ACEITE").json()["estado"], "EXPIRADO")
        self.assertEqual(self.ask(self.b, self.a).status_code, 201)
        self.assertFalse(Conversa.objects.exists())

    def test_text_plan_membership_and_block(self):
        pk = self.ask(self.a, self.b).json()["id"]
        chat = self.decide(self.b, pk, "ACEITE").json()["conversation_id"]
        url = f"/api/chats/{chat}/"
        self.assertEqual(self.client.post(url, {"texto": "Olá"}).status_code, 403)
        with patch("entradas.conversations_api.can_send_chat_text", return_value=True):
            self.assertEqual(self.client.post(url, {"texto": "Olá"}).status_code, 201)
        self.client.force_login(self.c.usuario)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.get(url).json()["mensagens"][0]["texto"], "Olá")
        self.assertTrue(MensagemMatch.objects.get().lida)
        AcaoPerfil.objects.create(usuario=self.a.usuario, perfil=self.b, tipo="BLOQUEIO")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"], [])

    def test_identity_required(self):
        self.a.pedido.identidade_revogada = True
        self.a.pedido.save()
        self.assertEqual(self.ask(self.a, self.b).status_code, 403)
        self.assertEqual(self.ask(self.b, self.a).status_code, 404)
