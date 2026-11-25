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

    def test_free_consent_before_identity_without_message_access(self):
        from .wallet_service import credit_balance
        self.a.pedido.identidade_revogada = True
        self.a.pedido.save()
        before = credit_balance(self.a.usuario)
        first = self.ask(self.b, self.a)
        self.assertEqual(first.status_code, 201, first.content)
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.get("/api/chats/").json()["pedidos"][0]["id"], first.json()["id"])
        accepted = self.decide(self.a, first.json()["id"], "ACEITE")
        self.assertTrue(accepted.json()["identity_pending"])
        chat = accepted.json()["conversation_id"]
        root = f"/api/chats/{chat}/"
        self.assertEqual(self.client.get(root).status_code, 403)
        self.assertEqual(self.client.post(root, {"texto": "Olá"}).status_code, 403)
        self.client.force_login(self.b.usuario)
        self.assertEqual(self.client.get(root).status_code, 404)
        row = self.client.get("/api/chats/").json()["conversas"][0]
        self.assertTrue(row["identity_pending"])
        self.assertIsNone(row["ultima_mensagem"])
        self.assertEqual(row["nao_lidas"], 0)
        self.assertEqual(credit_balance(self.a.usuario), before)
        self.a.pedido.identidade_revogada = False
        self.a.pedido.save()
        self.assertEqual(self.client.get(root).status_code, 200)

    def test_unverified_member_can_send_but_not_to_blocked_or_inactive_profile(self):
        self.a.pedido.verificacao_apos_entrada = True
        self.a.pedido.save()
        self.assertEqual(self.ask(self.a, self.b).status_code, 201)
        AcaoPerfil.objects.create(usuario=self.c.usuario, perfil=self.a, tipo="BLOQUEIO")
        self.assertEqual(self.ask(self.a, self.c).status_code, 404)
        self.c.usuario.is_active = False
        self.c.usuario.save()
        self.assertEqual(self.ask(self.a, self.c).status_code, 404)


    def test_imported_empty_chat_requires_real_acceptance(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        chat = match.chat
        root = f"/api/chats/{chat.pk}/"
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"], [])
        self.assertEqual(self.client.get(root).status_code, 404)
        self.assertEqual(self.client.get(f"/api/minha-conta/matches/{match.pk}/conversa/").status_code, 404)
        asked = self.ask(self.a, self.b)
        self.assertEqual(asked.status_code, 201, asked.content)
        self.assertEqual(asked.json()["estado"], "PENDENTE")
        self.assertEqual(self.ask(self.a, self.b).json()["estado"], "PENDENTE")
        self.assertEqual(self.client.get(root).status_code, 404)
        self.assertEqual(self.decide(self.b, asked.json()["id"], "ACEITE").json()["conversation_id"], chat.pk)
        self.assertEqual(self.client.get(root).status_code, 200)
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"][0]["consent_state"], "ACEITE")
        self.assertEqual(Conversa.objects.count(), 1)

    def test_imported_history_is_not_labelled_accepted_without_receipt(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        chat = match.chat
        MensagemMatch.objects.create(match=match, conversa=chat, remetente=self.a.usuario, texto="Histórico")
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"][0]["consent_state"], "ANTERIOR")
        self.assertEqual(self.ask(self.a, self.b).json()["estado"], "ANTERIOR")
        self.assertFalse(PedidoConversa.objects.exists())
        PedidoConversa.objects.create(remetente=self.a, destinatario=self.b, expira_em=timezone.now()+timedelta(days=7))
        self.assertEqual(self.client.get(f"/api/chats/{chat.pk}/").status_code, 404)
        self.assertEqual(self.ask(self.a, self.b).json()["estado"], "PENDENTE")
        self.assertEqual(MensagemMatch.objects.get(conversa=chat).texto, "Histórico")

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
        with patch("entradas.conversations_api.can_send_chat_text", return_value=True), patch("entradas.conversations_api.plan_for_user", return_value={"features": {"chat_text": True}}):
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
        MensagemMatch.objects.create(match=match, conversa=chat, remetente=self.a.usuario, texto="Histórico")
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

    def test_cancel_only_sender_and_no_acceptance_after_cancel(self):
        with self.captureOnCommitCallbacks(execute=True):
            pk = self.ask(self.a, self.b).json()["id"]
        url = f"/api/chats/pedidos/{pk}/cancelar/"
        for profile in (self.b, self.c):
            self.client.force_login(profile.usuario)
            self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.post(url).json()["estado"], "CANCELADO")
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertTrue(NotificacaoNKATA.objects.get(chave=f"pedido-chat:{pk}").lida)
        self.assertEqual(self.decide(self.b, pk, "ACEITE").status_code, 409)
        self.assertFalse(Conversa.objects.exists())
        self.assertEqual(self.ask(self.a, self.b).status_code, 201)

    def test_cancel_after_acceptance_or_expiry_is_rejected(self):
        pk = self.ask(self.a, self.b).json()["id"]
        self.decide(self.b, pk, "ACEITE")
        self.client.force_login(self.a.usuario)
        self.assertEqual(self.client.post(f"/api/chats/pedidos/{pk}/cancelar/").status_code, 409)
        expired = self.ask(self.a, self.c).json()["id"]
        PedidoConversa.objects.filter(pk=expired).update(expira_em=timezone.now())
        response = self.client.post(f"/api/chats/pedidos/{expired}/cancelar/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["estado"], "EXPIRADO")
        self.assertEqual(Conversa.objects.count(), 1)

    def test_request_details_and_history_for_both_participants(self):
        pk = self.ask(self.a, self.b).json()["id"]
        url = f"/api/chats/pedidos/{pk}/"
        detail = self.client.get(url).json()
        self.assertFalse(detail["recebido"])
        self.assertGreater(detail["segundos_restantes"], 0)
        self.assertEqual(self.client.get("/api/chats/").json()["pedidos"][0]["id"], pk)
        self.client.force_login(self.c.usuario)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.decide(self.b, pk, "RECUSADO")
        self.assertEqual(self.client.get("/api/chats/").json()["pedidos"], [])
        history = self.client.get("/api/chats/").json()["historico_pedidos"]
        self.assertEqual(history[0]["estado"], "RECUSADO")
        self.assertTrue(history[0]["recebido"])
        self.assertEqual(self.ask(self.a, self.b).status_code, 409)

    def test_inbox_previews_unread_and_connections(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        MensagemMatch.objects.create(conversa=chat, remetente=self.b.usuario, texto="Olá")
        MatchPerfil.objects.create(perfil_1=self.a, perfil_2=self.c)
        AcaoPerfil.objects.create(usuario=self.b.usuario, perfil=self.a, tipo="SINAL_OLA")
        self.client.force_login(self.a.usuario)
        result = self.client.get("/api/chats/").json()
        item = result["conversas"][0]
        self.assertEqual(item["perfil"]["id"], self.b.pk)
        self.assertEqual(item["nao_lidas"], 1)
        self.assertEqual(item["ultima_mensagem"]["texto"], "Olá")
        self.assertFalse(item["ultima_mensagem"]["minha"])
        self.assertEqual({c["perfil"]["id"] for c in result["conexoes"]}, {self.b.pk, self.c.pk})
        self.assertEqual(Conversa.objects.count(), 1)
        self.client.get(f"/api/chats/{chat.pk}/")
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"][0]["nao_lidas"], 0)
        AcaoPerfil.objects.create(usuario=self.a.usuario, perfil=self.b, tipo="BLOQUEIO")
        result = self.client.get("/api/chats/").json()
        self.assertEqual(result["conversas"], [])
        self.assertNotIn(self.b.pk, [c["perfil"]["id"] for c in result["conexoes"]])

    def test_inbox_counts_legacy_audio_until_opened(self):
        from .chat_media_models import MensagemAudioMatchNKATA

        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        audio = MensagemAudioMatchNKATA.objects.create(
            match=match, remetente=self.b.usuario, audio="chat/test.webm", duracao_segundos=2
        )
        self.client.force_login(self.a.usuario)
        item = self.client.get("/api/chats/").json()["conversas"][0]
        self.assertEqual(item["audios_nao_lidos"], 1)
        self.assertEqual(item["nao_lidas"], 1)
        self.assertEqual(item["ultima_mensagem"]["texto"], "Nota de voz")
        self.client.get(f"/api/chats/{match.chat.pk}/")
        audio.refresh_from_db()
        self.assertFalse(audio.lida)
        self.assertEqual(self.client.get(f"/api/minha-conta/matches/{match.pk}/audio/").status_code, 200)
        self.assertEqual(self.client.get("/api/chats/").json()["conversas"][0]["nao_lidas"], 0)

    def test_notifications_are_routed_to_independent_chat(self):
        pk = self.ask(self.a, self.b).json()["id"]
        with self.captureOnCommitCallbacks(execute=True):
            chat_id = self.decide(self.b, pk, "ACEITE").json()["conversation_id"]
        notice = NotificacaoNKATA.objects.get(destinatario=self.a.usuario, tipo="CHAT_ACEITE")
        self.assertEqual(notice.conversation_id, chat_id)
        with self.captureOnCommitCallbacks(execute=True):
            with patch("entradas.conversations_api.can_send_chat_text", return_value=True):
                self.assertEqual(self.client.post(f"/api/chats/{chat_id}/", {"texto": "Olá"}).status_code, 201)
        notice = NotificacaoNKATA.objects.get(destinatario=self.a.usuario, tipo="MENSAGEM")
        self.assertEqual(notice.conversation_id, chat_id)
        self.client.force_login(self.a.usuario)
        self.client.get(f"/api/chats/{chat_id}/")
        notice.refresh_from_db()
        self.assertTrue(notice.lida)

    def test_hidden_profile_photo_is_not_exposed_in_chat(self):
        from .conversations_api import chat_profile

        self.b.visivel = False
        with patch("entradas.conversations_api.profile_photo_url", return_value="/private-test-photo/"):
            self.assertIsNone(chat_profile(self.b)["foto_url"])

    def test_expired_request_notification_is_marked_read(self):
        with self.captureOnCommitCallbacks(execute=True):
            pk = self.ask(self.a, self.b).json()["id"]
        PedidoConversa.objects.filter(pk=pk).update(expira_em=timezone.now())
        self.client.force_login(self.b.usuario)
        self.assertEqual(self.client.get("/api/minha-conta/notificacoes/").status_code, 200)
        self.assertTrue(NotificacaoNKATA.objects.get(chave=f"pedido-chat:{pk}").lida)

    def test_chat_cursor_pagination_and_incremental_state(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        root = f"/api/chats/{chat.pk}/"
        items = MensagemMatch.objects.bulk_create([
            MensagemMatch(conversa=chat, remetente=self.a.usuario, texto=f"Mensagem {i}")
            for i in range(65)
        ])
        self.client.force_login(self.a.usuario)
        initial = self.client.get(root, {"paginado": 1}).json()
        self.assertEqual(len(initial["mensagens"]), 50)
        self.assertTrue(initial["mais"])
        first = initial["mensagens"][0]["id"]
        last = initial["mensagens"][-1]["id"]
        older = self.client.get(root, {"paginado": 1, "antes": first}).json()
        self.assertEqual(len(older["mensagens"]), 15)
        self.assertFalse(older["mais"])
        self.assertEqual(older["mensagens"][0]["id"], items[0].pk)
        self.client.force_login(self.b.usuario)
        self.client.get(root)
        self.client.force_login(self.a.usuario)
        self.client.delete(root + f"mensagens/{items[0].pk}/")
        new = MensagemMatch.objects.create(conversa=chat, remetente=self.b.usuario, texto="Nova")
        delta = self.client.get(root, {"paginado": 1, "depois": last, "estado_desde": items[0].pk}).json()
        self.assertEqual([m["id"] for m in delta["mensagens"]], [new.pk])
        self.assertIn(items[0].pk, delta["apagadas"])
        self.assertEqual(delta["lidas_ate"], last)
        self.assertEqual(self.client.get(root, {"paginado": 1, "depois": -1}).status_code, 400)
        self.assertEqual(self.client.get(root, {"paginado": 1, "depois": 0, "antes": 1}).status_code, 400)
        self.client.force_login(self.c.usuario)
        self.assertEqual(self.client.get(root, {"paginado": 1, "depois": 0}).status_code, 404)

    def test_chat_cursor_catches_up_in_multiple_pages(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        root = f"/api/chats/{chat.pk}/"
        rows = MensagemMatch.objects.bulk_create([
            MensagemMatch(conversa=chat, remetente=self.b.usuario, texto=str(i))
            for i in range(101)
        ])
        self.client.force_login(self.a.usuario)
        cursor = 0
        seen = []
        for _ in range(3):
            page = self.client.get(root, {"paginado": 1, "depois": cursor}).json()
            ids = [item["id"] for item in page["mensagens"]]
            seen.extend(ids)
            cursor = ids[-1]
        self.assertFalse(page["mais"])
        self.assertEqual(seen, [row.pk for row in rows])

    def test_presets_cannot_be_used_to_reply(self):
        from .plan_service import CHAT_PHRASES

        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        original = MensagemMatch.objects.create(conversa=chat, remetente=self.a.usuario, texto="Olá")
        self.client.force_login(self.a.usuario)
        with patch("entradas.conversations_api.can_send_chat_text", return_value=True), patch(
            "entradas.conversations_api.plan_for_user", return_value={"features": {"chat_text": False, "chat_presets": True}}
        ):
            response = self.client.post(f"/api/chats/{chat.pk}/", {"texto": CHAT_PHRASES[0], "resposta_a": original.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MensagemMatch.objects.filter(conversa=chat).count(), 1)

    def test_legacy_routes_reject_revoked_peer_including_media(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        self.b.pedido.identidade_revogada = True
        self.b.pedido.save(update_fields=["identidade_revogada"])
        self.client.force_login(self.a.usuario)
        root = f"/api/minha-conta/matches/{match.pk}/"
        for suffix in ("conversa/", "audio/", "audio/1/media/", "live/", "call/", "calls/history/"):
            self.assertEqual(self.client.get(root + suffix).status_code, 404, suffix)
        self.assertEqual(self.client.get(f"/api/chats/{match.chat.pk}/").status_code, 404)

    def test_legacy_routes_reject_block_even_if_match_remains_active(self):
        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        AcaoPerfil.objects.create(usuario=self.b.usuario, perfil=self.a, tipo="BLOQUEIO")
        for actor in (self.a, self.b):
            self.client.force_login(actor.usuario)
            for suffix in ("conversa/", "audio/", "live/", "call/", "calls/history/"):
                self.assertEqual(self.client.get(f"/api/minha-conta/matches/{match.pk}/{suffix}").status_code, 404)

    def test_legacy_presets_cannot_reply_without_text_plan(self):
        from .plan_service import CHAT_PHRASES

        match = historical_match(perfil_1=self.a, perfil_2=self.b)
        message = MensagemMatch.objects.create(match=match, conversa=match.chat, remetente=self.a.usuario, texto="Olá")
        self.client.force_login(self.a.usuario)
        with patch("entradas.api_views.can_send_chat_text", return_value=True), patch(
            "entradas.api_views.plan_for_user", return_value={"features": {"chat_text": False, "chat_presets": True}}
        ):
            response = self.client.post(f"/api/minha-conta/matches/{match.pk}/conversa/",
                                        {"texto": CHAT_PHRASES[0], "resposta_a": message.pk},
                                        content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MensagemMatch.objects.count(), 1)

    def test_block_api_preserves_report_and_history_and_cancels_pending(self):
        from .models import DenunciaPerfil

        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        message = MensagemMatch.objects.create(conversa=chat, remetente=self.b.usuario, texto="Histórico")
        # Include a pending request left over from an older session.
        pending = PedidoConversa.objects.create(remetente=self.b, destinatario=self.a,
                                               expira_em=timezone.now()+timedelta(days=7))
        self.client.force_login(self.a.usuario)
        reported = self.client.post(f"/api/perfis/{self.b.pk}/denunciar/",
                                    {"motivo": "COMPORTAMENTO_INADEQUADO", "detalhes": "Teste de segurança"})
        self.assertEqual(reported.status_code, 201, reported.content)
        blocked = self.client.post(f"/api/perfis/{self.b.pk}/bloquear/")
        self.assertEqual(blocked.status_code, 200, blocked.content)
        pending.refresh_from_db()
        self.assertEqual(pending.estado, "CANCELADO")
        self.assertEqual(MensagemMatch.objects.get(pk=message.pk).texto, "Histórico")
        self.assertTrue(DenunciaPerfil.objects.filter(denunciante=self.a.usuario, perfil=self.b).exists())
        for actor in (self.a, self.b):
            self.client.force_login(actor.usuario)
            root = f"/api/chats/{chat.pk}/"
            self.assertEqual(self.client.get(root).status_code, 404)
            self.assertEqual(self.client.post(root, {"texto": "Olá"}).status_code, 404)
            self.assertEqual(self.client.post(root + "escrita/").status_code, 404)
        self.assertEqual(self.decide(self.a, pending.pk, "ACEITE").status_code, 404)


    def test_chat_signal_uses_existing_quota_and_history(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        self.client.force_login(self.a.usuario)
        root = f"/api/chats/{chat.pk}/"
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.post(root + "sinais/", {"tipo": "FLOR"})
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(AcaoPerfil.objects.filter(tipo="SINAL_FLOR").count(), 1)
        self.assertEqual(self.client.post(root + "sinais/", {"tipo": "FLOR"}).status_code, 409)
        self.client.force_login(self.b.usuario)
        message = self.client.get(root).json()["mensagens"][0]
        self.assertEqual((message["tipo"], message["sinal"]), ("SINAL", "FLOR"))
        self.assertEqual(NotificacaoNKATA.objects.filter(destinatario=self.b.usuario, tipo="MENSAGEM").count(), 1)
        self.client.force_login(self.c.usuario)
        self.assertEqual(self.client.post(root + "sinais/", {"tipo": "OLA"}).status_code, 404)

    def test_profile_signal_does_not_create_chat_but_joins_existing(self):
        self.client.force_login(self.a.usuario)
        url = f"/api/perfis/{self.b.pk}/sinais/"
        self.assertEqual(self.client.post(url, {"tipo": "OLA"}).status_code, 201)
        self.assertFalse(Conversa.objects.exists())
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        self.assertEqual(self.client.post(url, {"tipo": "FLOR"}).status_code, 201)
        self.assertEqual(chat.mensagens.filter(tipo="SINAL").count(), 1)

    def test_icebreaker_allowlist_and_daily_limit(self):
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        root = f"/api/chats/{chat.pk}/"
        self.client.force_login(self.a.usuario)
        url = root + "quebra-gelo/"
        self.assertEqual(self.client.post(url, {"codigo": "texto arbitrário"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"codigo": "VALORES"}).status_code, 201)
        self.assertEqual(self.client.post(url, {"codigo": "VALORES"}).status_code, 409)
        for code in ("ENCONTRO", "SORRISO"):
            self.assertEqual(self.client.post(url, {"codigo": code}).status_code, 201)
        self.assertEqual(self.client.post(url, {"codigo": "SONHO"}).status_code, 429)
        self.assertEqual(self.client.get(root).json()["quebra_gelo"]["restantes"], 0)
        AcaoPerfil.objects.create(usuario=self.b.usuario, perfil=self.a, tipo="BLOQUEIO")
        self.assertEqual(self.client.post(url, {"codigo": "SONHO"}).status_code, 404)


    def test_free_presets_remain_after_received_message_and_share_daily_limit(self):
        from .plan_service import CHAT_PHRASES_PT, PRESET_DAILY_LIMIT
        chat = Conversa.objects.create(perfil_1=self.a, perfil_2=self.b)
        legacy = historical_match(perfil_1=self.a, perfil_2=self.c)
        MensagemMatch.objects.create(conversa=chat, remetente=self.b.usuario, texto="Como estás?")
        self.client.force_login(self.a.usuario)
        root = f"/api/chats/{chat.pk}/"
        legacy_url = f"/api/minha-conta/matches/{legacy.pk}/conversa/"
        self.assertEqual(self.client.get(root).json()["predefinidas"]["restantes"], PRESET_DAILY_LIMIT)
        self.assertEqual(self.client.post(root, {"texto": "Texto personalizado"}).status_code, 403)
        for i in range(PRESET_DAILY_LIMIT):
            response = self.client.post(root if i % 2 == 0 else legacy_url, {"texto": CHAT_PHRASES_PT[i]})
            self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.client.get(root).json()["frases"], [])
        self.assertEqual(self.client.post(legacy_url, {"texto": CHAT_PHRASES_PT[0]}).status_code, 403)
        self.assertEqual(MensagemMatch.objects.filter(remetente=self.a.usuario, tipo="PREDEFINIDA").count(), PRESET_DAILY_LIMIT)
        message = chat.mensagens.filter(remetente=self.a.usuario).first()
        self.assertEqual(self.client.delete(root + f"mensagens/{message.pk}/").status_code, 204)
        self.assertEqual(self.client.get(root).json()["predefinidas"]["restantes"], 0)
        MensagemMatch.objects.filter(remetente=self.a.usuario).update(criado_em=timezone.now()-timedelta(days=1))
        self.assertEqual(self.client.get(root).json()["predefinidas"]["restantes"], PRESET_DAILY_LIMIT)
