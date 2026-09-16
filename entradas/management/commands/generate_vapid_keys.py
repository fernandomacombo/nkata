import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management.base import BaseCommand


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class Command(BaseCommand):
    help = "Gera um par VAPID para as notificações Web Push do NKATA."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_value = private_key.private_numbers().private_value.to_bytes(32, "big")
        public_value = private_key.public_key().public_bytes(
            Encoding.X962,
            PublicFormat.UncompressedPoint,
        )

        self.stdout.write("Copie estas duas linhas para o ficheiro .env:")
        self.stdout.write(f"NKATA_WEBPUSH_PUBLIC_KEY={_base64url(public_value)}")
        self.stdout.write(f"NKATA_WEBPUSH_PRIVATE_KEY={_base64url(private_value)}")
        self.stdout.write("Guarde a chave privada apenas no servidor.")
