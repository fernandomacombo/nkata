from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import TestCase

from .account_limits import save_limited_request, confirm_document, normalize_phone, document_key
from .forms import PedidoEntradaForm
from .models import PedidoEntrada


def request_form(email, phone, document):
    item = PedidoEntrada(nome_completo="Test", email=email, telefone=phone, idade=30,
        cidade="Maputo", genero="MASCULINO", objetivo="RELACIONAMENTO_SERIO")
    return SimpleNamespace(save=lambda commit=False: item, cleaned_data={"numero_bi":document})


class AccountLimitsTests(TestCase):
    def test_phone_cannot_be_reused_with_another_email_and_bi(self):
        save_limited_request(request_form("first@example.test", "84 123 4567", "BI00000001"))
        for phone in ("+258841234567", "00258 84 123 4567"):
            with self.assertRaisesMessage(ValidationError, "telefone"):
                save_limited_request(request_form("other@example.test", phone, "BI00000002"))
        self.assertEqual(PedidoEntrada.objects.count(), 1)

    def test_bi_cannot_be_reused_with_another_email_and_phone(self):
        save_limited_request(request_form("first@example.test", "840000001", "110100000001A"))
        with self.assertRaisesMessage(ValidationError, "BI"):
            save_limited_request(request_form("other@example.test", "850000001", "1101 0000-0001.a"))
        self.assertEqual(PedidoEntrada.objects.count(), 1)

    def test_reviewer_cannot_approve_second_account_under_false_bi_declaration(self):
        first = save_limited_request(request_form("first@example.test", "840000001", "110100000001A"))
        confirm_document(first, "110100000001A")
        other = save_limited_request(request_form("other@example.test", "850000001", "FALSE000009"))
        with self.assertRaisesMessage(ValidationError, "BI"):
            confirm_document(other, "110100000001A")
        other.refresh_from_db()
        self.assertFalse(other.documento_confirmado)

    def test_rejected_request_does_not_allow_identity_reuse(self):
        first = save_limited_request(request_form("first@example.test", "840000001", "110100000001A"))
        first.status = "RECUSADO"
        first.save(update_fields=["status"])
        with self.assertRaisesMessage(ValidationError, "BI"):
            save_limited_request(request_form("other@example.test", "850000001", "110100000001A"))

    def test_confirmation_preserves_slot_and_stores_no_raw_bi(self):
        item = save_limited_request(request_form("one@example.test", "840000001", "110100000001A"))
        confirm_document(item, "110100000001A")
        confirm_document(item, "110100000001A")
        item.refresh_from_db()
        self.assertTrue(item.documento_confirmado)
        self.assertEqual(item.documento_chave, document_key("110100000001A"))
        self.assertNotIn("110100000001A", item.documento_chave)

    def test_new_access_form_requires_bi_number(self):
        form = PedidoEntradaForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("numero_bi", form.errors)

    def test_email_is_case_insensitive_and_remains_unique(self):
        save_limited_request(request_form("member@example.test", "840000001", "110100000001A"))
        form = PedidoEntradaForm()
        form.cleaned_data = {"email":"MEMBER@EXAMPLE.TEST"}
        with self.assertRaises(ValidationError):
            form.clean_email()

    def test_document_hash_is_stable_and_phone_rejects_text(self):
        self.assertEqual(document_key("1101 0000-0001.a"), document_key("110100000001A"))
        self.assertEqual(normalize_phone("+258 84 123 4567"), "258841234567")
        self.assertEqual(normalize_phone("not a phone"), "")
