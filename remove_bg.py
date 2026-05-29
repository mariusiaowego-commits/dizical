from rembg import remove
from PIL import Image
import os

src = "/Users/mt16/dev/dizical/src/kid_app/static"

for i in range(1, 9):
    raw = os.path.join(src, f"dizi-modal-new-{i}-raw.png")
    clean = os.path.join(src, f"dizi-modal-new-{i}-clean.png")
    print(f"Processing {i}...")
    img = Image.open(raw).convert("RGBA")
    out = remove(img)
    out.save(clean)
    print(f"  -> saved to {clean}")
