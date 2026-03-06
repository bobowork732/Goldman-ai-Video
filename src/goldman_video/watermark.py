from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio.v3 as iio


def apply_text_watermark(input_video: Path, output_video: Path, text: str, fps: int) -> Path:
    frames = iio.imread(input_video, index=None)
    stamped = []
    for frame in frames:
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        w, h = img.size
        x, y = 12, h - 24
        draw.rectangle((x - 5, y - 3, x + 8 * len(text), y + 14), fill=(0, 0, 0, 128))
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        stamped.append(img)

    output_video.parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(output_video, [f.copy() for f in stamped], fps=fps)
    return output_video
