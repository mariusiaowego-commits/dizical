import urllib.request
import urllib.error
import ssl
import os
from rembg import remove
from PIL import Image
import subprocess

src = "/Users/mt16/dev/dizical/src/kid_app/static"
os.makedirs(src, exist_ok=True)

urls = [
    "https://v3b.fal.media/files/b/0a9c27d0/Dcuh2Z3fDZoeMcswZj31v_n7rI6HrO.png",
    "https://v3b.fal.media/files/b/0a9c27d5/nHknmDBgrZ6Yl8VnVbK3j_rKNlNc1O.png",
    "https://v3b.fal.media/files/b/0a9c27da/mMag2kcWUsurO2RMuMlVO_S0wOzdOx.png",
    "https://v3b.fal.media/files/b/0a9c27df/6XNGRIETp8j13A6K47z5X_xgU7wzQp.png",
    "https://v3b.fal.media/files/b/0a9c27e4/vwWyBRYXmgEf5EAiDl8cp_DiyiaE11.png",
    "https://v3b.fal.media/files/b/0a9c27ea/yliuJZZy6VOK2dtJFnKtx_xAo7mEJU.png",
    "https://v3b.fal.media/files/b/0a9c27ee/BH4evnOGaIgKe5QYsqdrs_6Zfh3h8F.png",
    "https://v3b.fal.media/files/b/0a9c27f3/uytUOUFs2wv8GavKnpfIH_zMo45ws6.png",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for i, url in enumerate(urls, 1):
    raw = os.path.join(src, f"dizi-modal-new-{i}-raw.png")
    clean = os.path.join(src, f"dizi-modal-new-{i}-clean.png")
    print(f"[{i}] Downloading...")
    try:
        with urllib.request.urlopen(url, context=ctx) as resp:
            data = resp.read()
        with open(raw, "wb") as f:
            f.write(data)
    except Exception as e:
        # fallback to curl
        subprocess.run(["curl", "-sL", "-k", url, "-o", raw], check=True)
    print(f"[{i}] Removing background...")
    img = Image.open(raw).convert("RGBA")
    out = remove(img)
    out.save(clean)
    print(f"[{i}] Done -> {clean}")
