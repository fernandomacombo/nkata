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


def historical_match(**kwargs):
    """Match with a conversation already associated by migration 0042."""
    match = MatchPerfil.objects.create(**kwargs)
    a, b = sorted((match.perfil_1_id, match.perfil_2_id))
    Conversa.objects.create(perfil_1_id=a, perfil_2_id=b, match_origem=match)
    return match


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


    def test_new_match_cannot_bypass_consent_through_legacy_routes(self):
        match = MatchPerfil.objects.create(perfil_1=self.a, perfil_2=self.b)
        self.client.force_login(self.a.usuario)
        for suffix in ("conversa/", "audio/", "live/", "call/", "calls/history/"):
            self.assertEqual(self.client.get(f"/api/minha-conta/matches/{match.pk}/{suffix}").status_code, 404)
        self.assertFalse(MensagemMatch.objects.exists())

    def test_typing_replies_and_deletion_are_scoped_to_participants(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        root = f"/api/chats/{chat.pk}/"
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.post(root + "escrita/").status_code, 204)
        message = MensagemMatch.objects.create(conversa=chat, remetente=self.a.usuario, texto="Olá!")
        self.client.force_login(self.b.usuario)
        self.assertTrue(self.client.get(root).json()["a_escrever"])
        delete = root + f"mensagens/{message.pk}/"
        self.assertEqual(self.client.delete(delete).status_code, 404)
        with patch("entradas.conversations_api.can_send_chat_text", return_value=True):
            self.assertEqual(self.client.post(root, {"texto": "Olá!", "resposta_a": message.pk},
                                              content_type="application/json").status_code, 201)
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.delete(delete).status_code, 204)
        message.refresh_from_db()
        self.assertEqual(message.texto, "")
        self.assertIsNotNone(message.apagada_em)

    def test_legacy_match_cannot_be_deleted_with_chat_history(self):
        from django.db.models.deletion import RestrictedError

        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        chat = match.chat
        message = MensagemMatch.objects.create(
            match=match, conversa=chat, remetente=self.a.usuario, texto="Histórico"
        )
        with self.assertRaises(RestrictedError):
            match.delete()
        self.assertTrue(MatchPerfil.objects.filter(pk=match.pk).exists())
        self.assertTrue(Conversa.objects.filter(pk=chat.pk).exists())
        self.assertEqual(MensagemMatch.objects.get(pk=message.pk).texto, "Histórico")

    def test_match_without_conversation_can_still_be_deleted(self):
        match = MatchPerfil.objects.create(perfil_1=self.a, perfil_2=self.b)
        pk = match.pk
        match.delete()
        self.assertFalse(MatchPerfil.objects.filter(pk=pk).exists())

    def test_history_reconciliation_only_updates_linked_matches(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        from types import SimpleNamespace

        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        other = MatchPerfil.objects.create(perfil_1=self.a, perfil_2=self.c)
        message = MensagemMatch.objects.create(
            match=match, remetente=self.a.usuario, texto="Mensagem anterior"
        )
        unrelated = MensagemMatch.objects.create(
            match=other, remetente=self.a.usuario, texto="Outra mensagem"
        )
        migration = import_module("entradas.migrations.0043_proteger_historico_chats")
        for _ in range(2):
            migration.reconciliar_mensagens(apps, SimpleNamespace(connection=connection))
        message.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertEqual(message.conversa_id, match.chat.pk)
        self.assertIsNone(unrelated.conversa_id)
        self.assertEqual(Conversa.objects.count(), 1)

    def test_closing_match_does_not_close_text_chat(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        chat = match.chat
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.post(f"/api/minha-conta/matches/{match.pk}/encerrar/").status_code, 200)
        match.refresh_from_db()
        self.assertEqual(match.status, "ENCERRADO")
        self.assertEqual(self.client.get(f"/api/chats/{chat.pk}/").status_code, 200)
        with patch("entradas.conversations_api.can_send_chat_text", return_value=True):
            self.assertEqual(self.client.post(f"/api/chats/{chat.pk}/", {"texto": "Olá"}).status_code, 201)

    def test_closing_chat_preserves_match_and_history_and_prevents_reopening(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        chat = match.chat
        message = MensagemMatch.objects.create(
            match=match, conversa=chat, remetente=self.a.usuario, texto="Histórico"
        )
        root = f"/api/chats/{chat.pk}/"
        self.client.force_login(self.c.usuario)
        self.assertEqual(self.client.post(root + "encerrar/").status_code, 404)
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.post(root + "encerrar/").status_code, 200)
        self.assertEqual(self.client.post(root + "encerrar/").status_code, 200)
        self.assertEqual(self.client.get(root).status_code, 404)
        self.assertEqual(self.client.post(root, {"texto": "Olá"}).status_code, 404)
        self.assertEqual(self.client.post(root + "escrita/").status_code, 404)
        self.assertEqual(self.ask(self.b, self.a).status_code, 404)
        for suffix in ("conversa/", "audio/", "live/", "call/", "calls/history/"):
            self.assertEqual(self.client.get(f"/api/minha-conta/matches/{match.pk}/{suffix}").status_code, 404)
        match.refresh_from_db()
        self.assertEqual(match.status, "ATIVO")
        self.assertEqual(MensagemMatch.objects.get(pk=message.pk).texto, "Histórico")
