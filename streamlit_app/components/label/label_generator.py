from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
from io import BytesIO


LABEL_SIZE_MM = 76
TARGET_DPI = 300
MM_PER_INCH = 25.4

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_FONT_PATH = os.path.join(
    # BASE_DIR, "..", "..", "assets", "fonts", "Inter-Bold.ttf"
    BASE_DIR, "..", "..", "assets", "fonts", "JetBrainsMono-Bold.ttf"
)

def generate_label_with_overlays(
    background_path: str,
    fields: dict[dict],
    qr_specs: dict,
    font_path: str = None,
    qr_required: bool = True,
    print_size: int = 0

) -> BytesIO:
    base = Image.open(background_path).convert("RGBA")
    underlay = Image.new("RGBA", base.size, (0, 0, 0, 0))

    if qr_required:
        qr_data = qr_specs['qr_data']
        qr_size = qr_specs['qr_size']
        qr_position = qr_specs['qr_position']
        qr_img = qrcode.make(qr_data).resize((qr_size, qr_size)).convert("RGBA")
        underlay.paste(qr_img, qr_position, qr_img)
    # label_inches = print_size / MM_PER_INCH
    # target_px = int(round(label_inches * TARGET_DPI))
    # base = base.resize((target_px, target_px))

    composed = Image.alpha_composite(underlay, base)
    draw = ImageDraw.Draw(composed)

    # draw = ImageDraw.Draw(base)

    def load_font(size, font_path=DEFAULT_FONT_PATH):
        try:
            return ImageFont.truetype(font_path, size=size)
        except IOError:
            return ImageFont.load_default()
        
    # for field in fields:
    for field in fields.values():
        text = field["text"]
        position = field["position"]
        font_size = field.get("font_size", 16)
        font_path = field.get("font_path", DEFAULT_FONT_PATH)
        font = load_font(font_size, font_path)
        draw.text(position, text, font=font, fill="black")

    # if qr_required:
    #     qr_data = qr_specs['qr_data']
    #     qr_size = qr_specs['qr_size']
    #     qr_position = qr_specs['qr_position']
    #     qr_img = qrcode.make(qr_data).resize((qr_size, qr_size)).convert("RGBA")
    #     base.paste(qr_img, qr_position, qr_img)

    # bg = Image.new("RGBA", base.size, (255, 255, 255, 255))
    bg = Image.new("RGBA", composed.size, (255, 255, 255, 255))
    # flattened = Image.alpha_composite(bg, base)
    flattened = Image.alpha_composite(bg, composed).convert("RGB")
    return flattened

    # rgb_base = flattened.convert("RGB")

    # output = BytesIO()
    # # base.save(output, format="PNG") 
    # # rgb_base.save(output, format="PDF")
    # flattened.save(output, format="PDF")
    # # rgb_base.save(output, format="PDF", resolution=TARGET_DPI)
    # output.seek(0)
    # return output