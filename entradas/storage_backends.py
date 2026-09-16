import os

from django.core.files.storage import FileSystemStorage
from django.core.files.storage import storages
from storages.backends.s3 import S3Storage


class _ProtectedUrlMixin:
    def url(self, name):
        raise ValueError(
            "Media privada não possui URL direta; use o endpoint autorizado."
        )


class ProtectedFileSystemStorage(_ProtectedUrlMixin, FileSystemStorage):
    """Storage privado com leitura compatível dos uploads locais antigos."""

    def __init__(self, *args, legacy_location=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._legacy_storage = (
            FileSystemStorage(location=legacy_location, base_url=None)
            if legacy_location
            else None
        )

    def path(self, name):
        primary_path = super().path(name)
        if os.path.exists(primary_path) or not self._legacy_storage:
            return primary_path

        legacy_path = self._legacy_storage.path(name)
        return legacy_path if os.path.exists(legacy_path) else primary_path


class ProtectedS3Storage(_ProtectedUrlMixin, S3Storage):
    pass


def profile_media_storage():
    return storages["profiles"]


def identity_media_storage():
    return storages["identity"]


def private_content_storage():
    return storages["private"]
