import unittest
from unittest.mock import patch, Mock

import requests
from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings, SimpleTestCase

from entradas.email_backend import ZohoAPIEmailBackend, ZohoEmailError


@override_settings(NKATA_ZOHO_API_KEY='Zoho-enczapikey test-secret', EMAIL_TIMEOUT=15)
class ZohoEmailTests(SimpleTestCase):
    def message(self):
        return EmailMultiAlternatives('NKATA', 'Texto', 'NKATA <notificacoes@nkata.date>', ['user@example.com'])

    @patch('entradas.email_backend.requests.post')
    def test_text_html_and_private_recipients(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {'data': [{'code': 'EM_104'}]}
        msg = self.message()
        msg.attach_alternative('<p>Texto</p>', 'text/html')
        msg.bcc = ['hidden@example.com']
        msg.reply_to = ['support@example.com']
        self.assertEqual(ZohoAPIEmailBackend().send_messages([msg]), 1)
        args, kw = post.call_args
        self.assertEqual(args[0], 'https://cpaas.zoho.com/v1.1/email')
        self.assertEqual(kw['headers']['Authorization'], 'Zoho-enczapikey test-secret')
        self.assertFalse(kw['allow_redirects'])
        self.assertEqual(kw['json']['textbody'], 'Texto')
        self.assertEqual(kw['json']['htmlbody'], '<p>Texto</p>')
        self.assertNotIn('hidden@example.com', str(kw['json']['to']))
        self.assertFalse(kw['json']['track_clicks'])

    @override_settings(NKATA_ZOHO_API_KEY='')
    def test_missing_key(self):
        with self.assertRaises(ImproperlyConfigured):
            ZohoAPIEmailBackend()

    @patch('entradas.email_backend.requests.post')
    def test_http_errors_and_redirect_not_success(self, post):
        for status in (301, 401, 429, 500):
            post.return_value = Mock(status_code=status)
            with self.assertRaises(ZohoEmailError):
                ZohoAPIEmailBackend().send_messages([self.message()])

    @patch('entradas.email_backend.requests.post')
    def test_timeout_no_retry_or_secret(self, post):
        post.side_effect = requests.Timeout('test-secret')
        with self.assertRaises(ZohoEmailError) as exc:
            ZohoAPIEmailBackend().send_messages([self.message()])
        self.assertNotIn('test-secret', str(exc.exception))
        self.assertEqual(post.call_count, 1)
        self.assertEqual(ZohoAPIEmailBackend(fail_silently=True).send_messages([self.message()]), 0)

    @patch('entradas.email_backend.requests.post')
    def test_invalid_or_rejected_response(self, post):
        post.return_value = Mock(status_code=200)
        for body in ({}, {'data': [{'code': 'ERROR'}]}, [], {'data': []}):
            post.return_value.json.return_value = body
            with self.assertRaises(ZohoEmailError):
                ZohoAPIEmailBackend().send_messages([self.message()])
        post.return_value.json.side_effect = ValueError('secret')
        with self.assertRaises(ZohoEmailError):
            ZohoAPIEmailBackend().send_messages([self.message()])

    @patch('entradas.email_backend.requests.post')
    def test_empty_recipients_and_unsupported_attachment(self, post):
        self.assertEqual(ZohoAPIEmailBackend().send_messages([EmailMessage()]), 0)
        msg = self.message()
        msg.attach('test.txt', 'content', 'text/plain')
        with self.assertRaises(ValueError):
            ZohoAPIEmailBackend().send_messages([msg])
        post.assert_not_called()
