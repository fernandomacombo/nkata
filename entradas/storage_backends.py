from django.core.files.storage import FileSystemStorage
from django.core.files.storage import storages
from storages.backends.s3 import S3Storage


class _ProtectedUrlMixin:
    def url(self, name):
        raise ValueError(
            "Media privada não possui URL direta; use o endpoint autorizado."
        )


class ProtectedFileSystemStorage(_ProtectedUrlMixin, FileSystemStorage):
    pass


class ProtectedS3Storage(_ProtectedUrlMixin, S3Storage):
    pass


def profile_media_storage():
    return storages["profiles"]


def identity_media_storage():
    return storages["identity"]


def private_content_storage():
    return storages["private"]
