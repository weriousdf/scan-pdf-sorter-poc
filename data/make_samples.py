"""가짜 스캔 서류 PDF 를 만든다.

실제 고객 서류(private_samples/, GitHub 제외)에서 관찰한 구성을 본떠 만든 제출용 샘플이다.
이름·기관·번호는 전부 가짜이고, 모든 페이지에 SPECIMEN 표시가 있다.

실행:  python data/make_samples.py
결과:  data/samples/*.pdf, data/ground_truth.csv  (정답은 이 스크립트가 만들 때 확정된다)
"""
import csv
import random
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "samples"
DPI = 200
MM = DPI / 25.4  # 1mm 당 픽셀
FONT_DIR = Path("C:/Windows/Fonts")

random.seed(7)
np.random.seed(7)


def font(size, bold=False, serif=False):
    names = (["timesbd.ttf", "times.ttf"] if serif else ["malgunbd.ttf", "malgun.ttf"])
    name = names[0] if bold else names[1]
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


def mm(v):
    return int(round(v * MM))


def paper(w_mm, h_mm, color=(255, 255, 255)):
    return Image.new("RGB", (mm(w_mm), mm(h_mm)), color)


# ---------------------------------------------------------------- 서류 내용 그리기

def lines(d, x, y, width, n, gap=mm(7), size=30, seed=0):
    """가짜 본문 줄. 글자 대신 길이가 다른 문장을 적는다."""
    rnd = random.Random(seed)
    words = ["SAMPLE", "certificate", "hereby", "confirms", "student", "HONG GILDONG", "the", "of",
             "학위", "과정", "증명", "합니다", "위", "사람은", "본교", "재학", "중임을", "2026"]
    f = font(size)
    for i in range(n):
        s, cur = "", 0
        target = width * rnd.uniform(0.55, 1.0)
        while True:
            w = rnd.choice(words) + " "
            tw = d.textlength(s + w, font=f)
            if tw > target:
                break
            s += w
        d.text((x, y + i * gap), s.strip(), fill=(30, 30, 30), font=f)
    return y + n * gap


def stamp(d, cx, cy, r, color=(200, 60, 70), text="SEAL"):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=6)
    d.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], outline=color, width=3)
    f = font(int(r * 0.4), bold=True)
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, cy - r * 0.25), text, fill=color, font=f)


def signature(d, x, y, w=mm(40)):
    pts = [(x + i * w / 20, y + 25 * np.sin(i * 1.3) + random.uniform(-8, 8)) for i in range(21)]
    d.line(pts, fill=(40, 40, 120), width=4)


def specimen(img):
    """페이지 대각선에 옅게 SPECIMEN 을 찍는다."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(int(min(img.size) * 0.12), bold=True)
    d.text((img.width * 0.12, img.height * 0.42), "SPECIMEN", fill=(220, 40, 40, 45), font=f)
    layer = layer.rotate(25, center=(img.width / 2, img.height / 2))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def doc_certificate(w=210, h=297):
    """테두리가 페이지를 꽉 채우는 번역 인증서 표지."""
    im = paper(w, h); d = ImageDraw.Draw(im)
    d.rectangle([mm(12), mm(18), mm(w - 12), mm(h - 18)], outline=(40, 40, 40), width=5)
    d.text((mm(18), mm(24)), "Registered No. 0000-0000", fill=(30, 30, 30), font=font(26))
    title = "CERTIFICATE OF LICENSED TRANSLATION"
    f = font(44, bold=True, serif=True)
    d.text(((im.width - d.textlength(title, font=f)) / 2, mm(h * 0.35)), title, fill=(20, 20, 20), font=f)
    for i, t in enumerate(["SAMPLE TRANSLATION OFFICE", "HONG GILDONG", "#000 Sample-ro, Sample-gu"]):
        ff = font(30, bold=i < 2, serif=True)
        d.text(((im.width - d.textlength(t, font=ff)) / 2, mm(h * 0.62) + i * mm(8)), t, fill=(30, 30, 30), font=ff)
    stamp(d, mm(38), mm(h - 50), mm(18), color=(150, 110, 30), text="SAMPLE")
    return im


def doc_dense(w=210, h=297, seed=1):
    """글자가 페이지 전체에 찬 일반 세로 서류."""
    im = paper(w, h); d = ImageDraw.Draw(im)
    d.text((mm(80), mm(20)), "재 학 증 명 서", fill=(20, 20, 20), font=font(56, bold=True))
    y = lines(d, mm(22), mm(45), mm(w - 44), 30, seed=seed)
    stamp(d, mm(w - 45), y + mm(10), mm(14))
    d.text((mm(22), mm(h - 25)), "SAMPLE UNIVERSITY  |  Sample-ro 1, Seoul", fill=(60, 60, 60), font=font(24))
    return im


def doc_sparse(w=210, h=297, seed=2):
    """내용이 위쪽 절반에만 있는 A4 서류 (증명서 뒷장 같은 것). 규칙이 헷갈리는 경우."""
    im = paper(w, h); d = ImageDraw.Draw(im)
    d.text((mm(22), mm(20)), "2026. 04. 12  SAMPLE UNIVERSITY", fill=(30, 30, 30), font=font(26))
    y = lines(d, mm(22), mm(35), mm(w - 44), 12, seed=seed, size=26)
    stamp(d, mm(w - 40), y + mm(12), mm(10))
    return im


def doc_table_top(w=210, h=297):
    """위쪽에 표 하나만 있는 아포스티유 번역본."""
    im = paper(w, h); d = ImageDraw.Draw(im)
    d.text((mm(95), mm(15)), "아포스티유", fill=(20, 20, 20), font=font(32, bold=True))
    x0, x1, y = mm(18), mm(w - 18), mm(25)
    labels = ["1. 국가", "2. 서명자", "3. 직위", "4. 기관", "5. 장소", "6. 일자", "7. 발급자", "8. 번호", "9. 관인", "10. 서명"]
    for i, t in enumerate(labels):
        d.rectangle([x0, y, x1, y + mm(8)], outline=(60, 60, 60), width=2)
        d.text((x0 + 10, y + 8), t, fill=(30, 30, 30), font=font(22))
        d.text((x1 - mm(45), y + 8), "SAMPLE", fill=(30, 30, 30), font=font(22))
        y += mm(8)
    stamp(d, mm(w - 40), y + mm(18), mm(10))
    return im


def doc_diploma(w=297, h=210):
    """가로 졸업장 원본. 장식 테두리와 금색 인장."""
    im = paper(w, h, (248, 246, 236)); d = ImageDraw.Draw(im)
    for k, c in enumerate([(40, 110, 90), (180, 150, 70)]):
        d.rectangle([mm(8 + k * 4), mm(8 + k * 4), mm(w - 8 - k * 4), mm(h - 8 - k * 4)], outline=c, width=8)
    for i, (t, s) in enumerate([("SAMPLE COLLEGE", 70), ("Greetings:", 34), ("HONG GILDONG", 90),
                                ("Bachelor of Science in Sample Studies", 50)]):
        ff = font(s, bold=True, serif=True)
        d.text(((im.width - d.textlength(t, font=ff)) / 2, mm(30) + i * mm(28)), t, fill=(30, 50, 40), font=ff)
    stamp(d, mm(40), mm(40), mm(16), color=(160, 130, 40), text="SEAL")
    stamp(d, mm(w - 40), mm(40), mm(16), color=(160, 130, 40), text="SEAL")
    signature(d, mm(60), mm(h - 30)); signature(d, mm(w - 110), mm(h - 30))
    return im


def doc_landscape_translation(w=297, h=210):
    im = paper(w, h); d = ImageDraw.Draw(im)
    d.text((mm(120), mm(18)), "SAMPLE 대학교", fill=(20, 20, 20), font=font(44, bold=True))
    lines(d, mm(40), mm(40), mm(w - 80), 12, seed=5, size=28)
    d.text((mm(130), mm(h - 50)), "HONG GILDONG", fill=(20, 20, 20), font=font(34, bold=True))
    stamp(d, mm(w - 60), mm(h - 45), mm(12))
    return im


def doc_transcript(w=210, h=297):
    """표가 빽빽한 성적증명서 원본."""
    im = paper(w, h, (246, 250, 244)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, mm(18)], fill=(60, 140, 90))
    d.text((mm(10), mm(4)), "SAMPLE COLLEGE  Official Transcript", fill=(255, 255, 255), font=font(34, bold=True))
    y = mm(28)
    for i in range(34):
        d.line([mm(10), y, mm(w - 10), y], fill=(150, 170, 150), width=1)
        d.text((mm(12), y + 4), f"SMP{100 + i}  Sample Course {i + 1}", fill=(30, 30, 30), font=font(20))
        d.text((mm(w - 40), y + 4), f"{random.choice(['A', 'B+', 'A-', 'B'])}   3.0", fill=(30, 30, 30), font=font(20))
        y += mm(7)
    signature(d, mm(30), mm(h - 20))
    return im


def doc_passport():
    """여권 정보면 (125 x 88mm)."""
    im = paper(125, 88, (236, 240, 248)); d = ImageDraw.Draw(im)
    for k in range(0, im.width, 18):  # 배경 무늬
        d.line([k, 0, k - 200, im.height], fill=(222, 228, 240), width=2)
    d.text((mm(6), mm(4)), "PASSPORT  ·  SPECIMEN STATE", fill=(40, 50, 90), font=font(30, bold=True))
    d.rectangle([mm(6), mm(14), mm(38), mm(56)], fill=(200, 205, 215))
    d.ellipse([mm(14), mm(18), mm(30), mm(36)], fill=(150, 155, 170))      # 얼굴 자리
    d.pieslice([mm(10), mm(36), mm(34), mm(64)], 180, 360, fill=(150, 155, 170))
    y = mm(15)
    for t in ["Surname  HONG", "Given names  GILDONG", "Nationality  SPECIMEN", "Date of birth  01 JAN 2000",
              "Passport No.  X00000000", "Date of expiry  01 JAN 2036"]:
        d.text((mm(44), y), t, fill=(30, 30, 50), font=font(24)); y += mm(6.3)
    for i in range(2):
        d.text((mm(6), mm(66) + i * mm(8)), "P<SPCHONG<<GILDONG<<<<<<<<<<<<<<<<<<<<<<<"[:44] if i == 0 else
               "X000000000SPC0001011M3601011<<<<<<<<<<<<<<00",
               fill=(20, 20, 20), font=ImageFont.truetype(str(FONT_DIR / "consola.ttf"), 30))
    return im


def doc_idcard(back=False):
    """신분증 (86 x 54mm)."""
    im = paper(86, 54, (240, 244, 236)); d = ImageDraw.Draw(im)
    if not back:
        d.text((mm(4), mm(3)), "주민등록증  SPECIMEN", fill=(40, 60, 40), font=font(28, bold=True))
        d.text((mm(4), mm(13)), "홍길동 (HONG GILDONG)", fill=(20, 20, 20), font=font(26, bold=True))
        d.text((mm(4), mm(21)), "000000-0000000", fill=(20, 20, 20), font=font(26))
        d.text((mm(4), mm(29)), "서울특별시 샘플구 샘플로 1", fill=(20, 20, 20), font=font(22))
        d.rectangle([mm(60), mm(12), mm(82), mm(40)], fill=(200, 205, 200))
        d.ellipse([mm(65), mm(15), mm(77), mm(28)], fill=(150, 160, 150))
    else:
        d.text((mm(4), mm(4)), "주소 변경 이력  SPECIMEN", fill=(40, 60, 40), font=font(24, bold=True))
        for i in range(5):
            d.line([mm(4), mm(14 + i * 7), mm(82), mm(14 + i * 7)], fill=(160, 170, 160), width=2)
    return im


def doc_apostille_small():
    """작은 아포스티유 원본 (약 150 x 160mm), 테두리 없이 글자만."""
    im = paper(150, 160); d = ImageDraw.Draw(im)
    d.rectangle([mm(3), mm(3), mm(147), mm(157)], outline=(80, 80, 80), width=3)
    d.text((mm(55), mm(8)), "APOSTILLE", fill=(20, 20, 20), font=font(34, bold=True, serif=True))
    d.text((mm(22), mm(18)), "(Convention de La Haye du 5 octobre 1961)", fill=(30, 30, 30), font=font(22, serif=True))
    y = mm(30)
    for i in range(1, 11):
        d.text((mm(10), y), f"{i}. Sample field ............ SPECIMEN", fill=(30, 30, 30), font=font(22, serif=True))
        y += mm(10)
    stamp(d, mm(35), mm(135), mm(14), color=(70, 80, 160))
    signature(d, mm(80), mm(138))
    return im


def doc_small_receipt():
    """A6 크기 작은 증명서 (105 x 148mm)."""
    im = paper(148, 105); d = ImageDraw.Draw(im)
    d.text((mm(8), mm(6)), "SAMPLE 확인서", fill=(20, 20, 20), font=font(36, bold=True))
    lines(d, mm(8), mm(22), mm(130), 8, seed=9, size=24)
    stamp(d, mm(125), mm(85), mm(10))
    return im


# ---------------------------------------------------------------- 스캔 흉내

def place(page, item, x_mm, y_mm, angle=0.0, edge=True):
    """A4 페이지 위에 작은 종이를 올린다. edge=True 면 종이 가장자리에 옅은 그림자를 넣는다."""
    item = item.convert("RGBA")
    if angle:
        item = item.rotate(angle, expand=True, resample=Image.BICUBIC)
    x, y = mm(x_mm), mm(y_mm)
    if edge:
        shadow = Image.new("RGBA", item.size, (0, 0, 0, 0))
        mask = item.split()[3].point(lambda a: 70 if a > 0 else 0)
        shadow.putalpha(mask)
        shadow = shadow.filter(ImageFilter.GaussianBlur(6))
        page.paste(shadow, (x + 5, y + 6), shadow)
    page.paste(item, (x, y), item)
    return page


def scan(img, bg=None, noise=4, blur=0.6):
    """스캐너 느낌: 약한 흐림, 잡음, 약간 어두운 톤."""
    arr = np.asarray(img).astype(np.float32)
    arr = arr * 0.97 + np.random.normal(0, noise, arr.shape)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return out.filter(ImageFilter.GaussianBlur(blur)) if blur else out


def photo_on_gray(doc, page_w, page_h, scale=0.92, angle=1.2):
    """회색 배경 위에서 찍은 사진 같은 페이지. 종이가 약간 작고 기울어 있다."""
    bg = Image.new("RGB", (mm(page_w), mm(page_h)), (150, 152, 150))
    arr = np.asarray(bg).astype(np.float32) + np.linspace(-25, 25, bg.height)[:, None, None]
    bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    w, h = int(bg.width * scale), int(bg.height * scale)
    d = doc.resize((w, h))
    d = d.convert("RGBA").rotate(angle, expand=True, resample=Image.BICUBIC)
    bg.paste(d, ((bg.width - d.width) // 2, (bg.height - d.height) // 2), d)
    return bg


def blank(w=210, h=297):
    return paper(w, h, (253, 253, 252))


# ---------------------------------------------------------------- 페이지 구성

def build_pages():
    """(PDF 이름, 페이지 설명, 정답: size(A4/small), orientation, 이미지) 목록."""
    P = []  # (pdf, note, size, orient, image)

    # PDF 1 — 세로 서류 묶음 + 작은 서류 (qnet 구성을 본뜸)
    P.append(("fake_01_mixed.pdf", "번역 인증서 표지 (테두리 꽉 참)", "A4", "portrait", scan(doc_certificate())))
    P.append(("fake_01_mixed.pdf", "재학증명서 (글자 많음)", "A4", "portrait", scan(doc_dense())))
    P.append(("fake_01_mixed.pdf", "증명서 뒷장 (내용 위쪽만)", "A4", "portrait", scan(doc_sparse())))
    P.append(("fake_01_mixed.pdf", "아포스티유 번역본 (위쪽 표만)", "A4", "portrait", scan(doc_table_top())))
    P.append(("fake_01_mixed.pdf", "A4 위 작은 아포스티유 (가운데)", "small", "portrait",
              scan(place(blank(), doc_apostille_small(), 30, 70))))
    P.append(("fake_01_mixed.pdf", "A5 페이지 아포스티유", "small", "portrait",
              scan(place(blank(148, 210), doc_apostille_small().resize((mm(130), mm(139))), 9, 30, edge=False))))
    P.append(("fake_01_mixed.pdf", "번역 확인서 (글자 많음)", "A4", "portrait", scan(doc_dense(seed=3))))

    # PDF 2 — 가로·세로 섞임 (가로샘플 구성을 본뜸)
    P.append(("fake_02_landscape.pdf", "번역 인증서 표지", "A4", "portrait", scan(doc_certificate())))
    P.append(("fake_02_landscape.pdf", "졸업장 번역본 (가로)", "A4", "landscape", scan(doc_landscape_translation())))
    P.append(("fake_02_landscape.pdf", "졸업장 원본 (가로, 회색 배경 사진)", "A4", "landscape",
              scan(photo_on_gray(doc_diploma(), 297, 210, scale=0.9, angle=-0.8))))
    P.append(("fake_02_landscape.pdf", "성적증명서 원본 (회색 배경 사진)", "A4", "portrait",
              scan(photo_on_gray(doc_transcript(), 210, 297, scale=0.93, angle=1.0))))
    P.append(("fake_02_landscape.pdf", "가로 A4 위 작은 확인서", "small", "landscape",
              scan(place(blank(297, 210), doc_small_receipt(), 70, 45))))
    P.append(("fake_02_landscape.pdf", "성적증명서 번역본 (위쪽 절반)", "A4", "portrait", scan(doc_sparse(seed=4))))

    # PDF 3 — 신분증·여권 (A4 위 작은 서류가 여러 형태로)
    P.append(("fake_03_id_passport.pdf", "A4 위 여권 정보면 (위쪽)", "small", "portrait",
              scan(place(blank(), doc_passport(), 42, 25))))
    P.append(("fake_03_id_passport.pdf", "A4 위 신분증 앞·뒷면", "small", "portrait",
              scan(place(place(blank(), doc_idcard(), 20, 30), doc_idcard(True), 110, 30))))
    P.append(("fake_03_id_passport.pdf", "A4 위 여권 (비스듬히, 가운데)", "small", "portrait",
              scan(place(blank(), doc_passport(), 38, 100, angle=6))))
    P.append(("fake_03_id_passport.pdf", "A4 위 신분증 (경계 그림자 없음)", "small", "portrait",
              scan(place(blank(), doc_idcard(), 62, 40, edge=False))))
    P.append(("fake_03_id_passport.pdf", "여권 번역본 (A4 서류)", "A4", "portrait", scan(doc_table_top())))
    P.append(("fake_03_id_passport.pdf", "A4 위 여권 (경계 그림자 없음, 가운데)", "small", "portrait",
              scan(place(blank(), doc_passport(), 42, 105, edge=False))))
    return P


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = build_pages()
    docs, rows, counters = {}, [], {}
    for pdf, note, size, orient, img in pages:
        img = specimen(img)
        doc = docs.setdefault(pdf, pymupdf.open())
        w_pt, h_pt = img.width / DPI * 72, img.height / DPI * 72
        page = doc.new_page(width=w_pt, height=h_pt)
        tmp = OUT / "_tmp.jpg"
        img.save(tmp, quality=85)
        page.insert_image(page.rect, filename=str(tmp))
        counters[pdf] = counters.get(pdf, 0) + 1
        rows.append({"pdf": pdf, "page": counters[pdf], "size": size, "orientation": orient, "note": note})
    (OUT / "_tmp.jpg").unlink()
    for name, doc in docs.items():
        doc.save(OUT / name, deflate=True)
    with open(ROOT / "ground_truth.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["pdf", "page", "size", "orientation", "note"])
        w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} pages -> {OUT}")


if __name__ == "__main__":
    main()
