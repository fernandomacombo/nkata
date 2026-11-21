from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image

from config.social_preview import PUBLIC_IMAGES


class SocialPreviewTests(SimpleTestCase):
    def test_public_social_image_is_square_png(self):
        response = self.client.get("/social-preview.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1080, 1080))

    def test_preview_does_not_require_authentication(self):
        response = self.client.get("/social-preview.png")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("private", response["Cache-Control"].lower())

    def test_preview_works_if_visual_assets_are_missing(self):
        with patch("config.social_preview.PUBLIC_IMAGES", PUBLIC_IMAGES / "missing-assets"):
            response = self.client.get("/social-preview.png")
        self.assertEqual(response.status_code, 200)
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.size, (1080, 1080))
