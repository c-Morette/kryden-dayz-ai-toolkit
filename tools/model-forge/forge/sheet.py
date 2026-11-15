"""Contact sheet: python sheet.py out.png cols scale img1 img2 ..."""
import sys
from PIL import Image, ImageDraw
out, cols, scale = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
ims = [Image.open(p).convert("RGB") for p in sys.argv[4:]]
w, h = int(ims[0].width * scale), int(ims[0].height * scale)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows), (40, 40, 40))
for i, (im, p) in enumerate(zip(ims, sys.argv[4:])):
    im = im.resize((w, h))
    d = ImageDraw.Draw(im)
    d.text((8, 8), p.replace("\\", "/").split("/")[-1], fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(out, sheet.size)
