"""결과 폴더를 한 장의 그림으로 모은다. 폴더(예측)별로 줄을 나누고, 정답과 다르면 빨간 테두리를 친다.

    python poc/overview.py --run outputs/run2/clip --truth data/ground_truth.csv --out docs/assets/result_v2.jpg
"""
import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ORDER = ["A4_세로", "A4_가로", "작은서류_세로", "작은서류_가로"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    run = Path(a.run)
    with open(a.truth, encoding="utf-8-sig") as f:
        truth = {(r["pdf"], int(r["page"])): r for r in csv.DictReader(f)}
    with open(run / "predictions.csv", encoding="utf-8-sig") as f:
        preds = list(csv.DictReader(f))

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 18)
        big = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 22)
    except OSError:
        font = big = ImageFont.load_default()

    T, pad, label_w = 190, 12, 150
    groups = {k: [p for p in preds if p["file"].startswith(k + "/")] for k in ORDER}
    groups = {k: v for k, v in groups.items() if v}
    cols = max(len(v) for v in groups.values())
    top = 44 if a.title else 0
    W = label_w + cols * (T + pad) + pad
    H = top + len(groups) * (T + 50) + pad
    sheet = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    if a.title:
        d.text((pad, 10), a.title, fill=(20, 20, 20), font=big)
    for gi, (g, items) in enumerate(groups.items()):
        y = top + gi * (T + 50) + pad
        d.text((pad, y + T // 2 - 12), g, fill=(20, 20, 20), font=big)
        for ci, p in enumerate(items):
            x = label_w + ci * (T + pad)
            im = Image.open(run / p["file"]).convert("RGB")
            im.thumbnail((T, T))
            ox, oy = x + (T - im.width) // 2, y + (T - im.height) // 2
            sheet.paste(im, (ox, oy))
            t = truth[(p["pdf"], int(p["page"]))]
            ok = t["size"] == p["size"] and t["orientation"] == p["orientation"]
            color = (40, 150, 70) if ok else (220, 40, 40)
            d.rectangle([ox - 3, oy - 3, ox + im.width + 3, oy + im.height + 3], outline=color, width=4 if ok else 7)
            tag = f"{Path(p['file']).stem.replace('fake_', '')}"
            if not ok:
                tag = "[X] " + tag
            d.text((x, y + T + 4), tag, fill=color, font=font)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out, quality=88)
    print(a.out)


if __name__ == "__main__":
    main()
