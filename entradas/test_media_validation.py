from io import BytesIO
from types import SimpleNamespace

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .media_validation import (
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_SIDE,
    image_dimensions_are_safe,
    sanitized_image_upload,
)


class MediaValidationTests(SimpleTestCase):
    def test_normal_mobile_photo_dimensions_are_allowed(self):
        self.assertTrue(image_dimensions_are_safe(SimpleNamespace(size=(4032, 3024))))

    def test_excessive_pixel_count_is_rejected(self):
        self.assertFalse(
            image_dimensions_are_safe(SimpleNamespace(size=(10_000, 10_000)))
        )
        self.assertLess(MAX_IMAGE_PIXELS, 10_000 * 10_000)

    def test_excessive_single_dimension_is_rejected(self):
        self.assertFalse(
            image_dimensions_are_safe(
                SimpleNamespace(size=(MAX_IMAGE_SIDE + 1, 1)),
            )
        )

    def test_sanitized_upload_removes_exif_metadata(self):
        source = BytesIO()
        image = Image.new("RGB", (64, 64), color=(125, 38, 56))
        exif = image.getexif()
        exif[0x010E] = "informação privada"
        image.save(source, format="JPEG", exif=exif)
        upload = SimpleUploadedFile(
            "fotografia.jpeg",
            source.getvalue(),
            content_type="image/jpeg",
        )

        clean = sanitized_image_upload(upload)
        with Image.open(clean) as result:
            self.assertFalse(result.getexif())
        self.assertEqual(clean.name, "fotografia.jpg")
