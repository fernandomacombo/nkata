"""Pré-visualização pública quadrada da página inicial do NKATA.

A imagem usa os ficheiros visuais oficiais já publicados no frontend.
Não lê fotografias, documentos ou dados dos utilizadores.
"""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from PIL import Image, ImageDraw, ImageFont, ImageOps


SIDE = 1080
PUBLIC_IMAGES = Path(settings.BASE_DIR) / "frontend" / "public" / "images"


def _font(size, bold=False):
    names = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    )
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


@require_GET
def social_preview(request):
    # Apenas recursos públicos e estáticos do NKATA; nunca media de perfis.
    sources = [
        PUBLIC_IMAGES / "nkata-hero-mobile.webp",
        PUBLIC_IMAGES / "nkata-hero-desktop.webp",
    ]
    hero = next((source for source in sources if source.is_file()), None)
    if hero:
        with Image.open(hero) as original:
            picture = ImageOps.fit(original.convert("RGB"), (SIDE, SIDE), method=Image.Resampling.LANCZOS)
    else:
        picture = Image.new("RGB", (SIDE, SIDE), "#2d0716")

    canvas = picture.convert("RGBA")
    shade = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    overlay = ImageDraw.Draw(shade)
    for y in range(SIDE):
        # Gradiente que preserva a fotografia mas dá contraste ao texto.
        alpha = int(130 + 100 * (y / SIDE))
        overlay.line((0, y, SIDE, y), fill=(31, 3, 17, min(alpha, 235)))
    canvas = Image.alpha_composite(canvas, shade)
    draw = ImageDraw.Draw(canvas)

    gold = "#e7c687"
    white = "#fff8f3"
    draw.rounded_rectangle((48, 48, SIDE - 48, SIDE - 48), radius=34, outline=gold, width=3)

    logo = PUBLIC_IMAGES / "nkata-logo-original.png"
    if logo.is_file():
        with Image.open(logo) as source:
            mark = source.convert("RGBA")
            mark.thumbnail((205, 205), Image.Resampling.LANCZOS)
            canvas.alpha_composite(mark, ((SIDE - mark.width) // 2, 92))
    else:
        draw.text((SIDE // 2, 150), "NKATA", anchor="mm",
                  font=_font(90, True), fill=gold)

    draw = ImageDraw.Draw(canvas)
    draw.text((SIDE // 2, 420), "Relações sérias", anchor="mm",
              font=_font(79, True), fill=white, stroke_width=1, stroke_fill="#260b13")
    draw.text((SIDE // 2, 525), "começam com", anchor="mm",
              font=_font(72, True), fill=white, stroke_width=1, stroke_fill="#260b13")
    draw.text((SIDE // 2, 630), "confiança.", anchor="mm",
              font=_font(79, True), fill=gold, stroke_width=1, stroke_fill="#260b13")

    draw.line((270, 720, 810, 720), fill=gold, width=3)
    draw.text((SIDE // 2, 790), "Acesso controlado · 18+", anchor="mm",
              font=_font(39), fill=white)
    draw.text((SIDE // 2, 922), "www.nkata.date", anchor="mm",
              font=_font(43, True), fill=white)

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["Cache-Control"] = "public, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response
