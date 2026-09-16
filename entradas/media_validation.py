import os
from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.uploadedfile import SimpleUploadedFile


MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 12_000
MAX_STORED_IMAGE_SIDE = 2_048

IMAGE_OUTPUTS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}


def image_dimensions_are_safe(image):
    try:
        width, height = image.size
    except (AttributeError, TypeError, ValueError):
        return False
    if width <= 0 or height <= 0:
        return False
    return (
        width <= MAX_IMAGE_SIDE
        and height <= MAX_IMAGE_SIDE
        and width * height <= MAX_IMAGE_PIXELS
    )


def sanitized_image_upload(upload):
    """Normaliza orientação e remove EXIF/GPS antes de guardar media."""
    upload.seek(0)
    with Image.open(upload) as source:
        image_format = (source.format or "").upper()
        if image_format not in IMAGE_OUTPUTS:
            raise ValueError("Formato de imagem não suportado.")
        image = ImageOps.exif_transpose(source)
        image.load()
        image.thumbnail(
            (MAX_STORED_IMAGE_SIDE, MAX_STORED_IMAGE_SIDE),
            Image.Resampling.LANCZOS,
        )

        if image_format == "JPEG" and image.mode != "RGB":
            if "A" in image.mode:
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

        output = BytesIO()
        save_options = {"format": image_format}
        if image_format == "JPEG":
            save_options.update({"quality": 84, "optimize": True, "progressive": True})
        elif image_format == "WEBP":
            save_options.update({"quality": 82, "method": 5})
        elif image_format == "PNG":
            save_options.update({"optimize": True})
        image.save(output, **save_options)

    upload.seek(0)
    extension, content_type = IMAGE_OUTPUTS[image_format]
    stem = os.path.splitext(os.path.basename(upload.name or "imagem"))[0] or "imagem"
    return SimpleUploadedFile(
        f"{stem}{extension}",
        output.getvalue(),
        content_type=content_type,
    )
