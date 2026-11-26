from django.test import SimpleTestCase
from uuid import uuid4
from .moment_credit_service import parse_moment_confirmation, MomentCreditError, PHOTO_COST, VIDEO_COST

class MomentCreditConfirmationTests(SimpleTestCase):
    def test_prices_and_keys(self):
        key = uuid4()
        self.assertEqual(PHOTO_COST, 2)
        self.assertEqual(VIDEO_COST, 5)
        for cost in (0, 2, 5):
            self.assertEqual(parse_moment_confirmation({"key":str(key),"expected_cost":cost}), (key,cost))

    def test_invalid_or_missing_confirmation(self):
        for data in ({}, {"key":"bad","expected_cost":0}, {"key":str(uuid4()),"expected_cost":-1}, {"key":str(uuid4()),"expected_cost":1}):
            with self.assertRaises(MomentCreditError):
                parse_moment_confirmation(data)
