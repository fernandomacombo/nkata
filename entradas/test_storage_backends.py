import os
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from .storage_backends import ProtectedFileSystemStorage


class ProtectedFileSystemStorageTests(SimpleTestCase):
    def setUp(self):
        self.primary = tempfile.TemporaryDirectory(prefix="nkata-private-primary-")
        self.legacy = tempfile.TemporaryDirectory(prefix="nkata-private-legacy-")
        self.addCleanup(self.primary.cleanup)
        self.addCleanup(self.legacy.cleanup)
        self.storage = ProtectedFileSystemStorage(
            location=self.primary.name,
            base_url=None,
            legacy_location=self.legacy.name,
        )

    def test_reads_existing_file_from_legacy_location(self):
        legacy_file = Path(self.legacy.name, "posts", "existing.jpg")
        legacy_file.parent.mkdir(parents=True)
        legacy_file.write_bytes(b"legacy-private-media")

        with self.storage.open("posts/existing.jpg", "rb") as handle:
            self.assertEqual(handle.read(), b"legacy-private-media")

        self.assertTrue(self.storage.exists("posts/existing.jpg"))

    def test_saves_new_file_only_in_private_location(self):
        name = self.storage.save("posts/new.jpg", ContentFile(b"new-private-media"))

        self.assertTrue(Path(self.primary.name, name).exists())
        self.assertFalse(Path(self.legacy.name, name).exists())

    def test_deletes_legacy_file_through_private_storage(self):
        legacy_file = Path(self.legacy.name, "moments", "old.jpg")
        legacy_file.parent.mkdir(parents=True)
        legacy_file.write_bytes(b"old-private-media")

        self.storage.delete("moments/old.jpg")

        self.assertFalse(os.path.exists(legacy_file))
