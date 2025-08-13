from PIL import Image, ImageDraw, ImageFont
import qrcode
from io import BytesIO

def generate_label_with_overlays(
    background_path: str,
    fields: list[dict],
    qr_data: str,
    qr_position: tuple[int, int],
    font_path: str = None,
    qr_size: int = 100,
) -> BytesIO:
    base = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(base)

    def load_font(size):
        try:
            return ImageFont.truetype(font_path or "arial.ttf", size=size)
        except IOError:
            return ImageFont.load_default()
        
    for field in fields:
        text = field["text"]
        position = field["position"]
        font_size = field.get("font_size", 16)
        font = load_font(font_size)
        draw.text(position, text, font=font, fill="black")

    qr_img = qrcode.make(qr_data).resize((qr_size, qr_size)).convert("RGBA")
    base.paste(qr_img, qr_position, qr_img)

    output = BytesIO()
    base.save(output, format="PNG")
    output.seek(0)
    return output