from PIL import Image
import os

src = "/Users/mt16/dev/dizical/src/kid_app/static"

def crop_to_content(img, padding=20):
    """裁剪到非透明内容区域，加padding"""
    alpha = img.split()[3]  # RGBA
    bbox = alpha.getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        x0 = max(0, x0 - padding)
        y0 = max(0, y0 - padding)
        x1 = min(img.width, x1 + padding)
        y1 = min(img.height, y1 + padding)
        return img.crop((x0, y0, x1, y1))
    return img

for i in range(1, 9):
    raw_path = f"{src}/dizi-modal-new-{i}-clean.png"
    out_path = f"{src}/dizi-modal-new-{i}-crop.png"
    img = Image.open(raw_path)
    cropped = crop_to_content(img, padding=30)
    cropped.save(out_path)
    print(f"[{i}] {img.width}x{img.height} -> {cropped.width}x{cropped.height}")
