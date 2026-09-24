"""스캔 PDF 를 페이지별 JPG 로 저장하고, 가로/세로와 A4 서류/작은 서류로 나눈다.

    python poc/split_pdf.py --pdfs data/samples --backend rule --run-id my_run
    python poc/split_pdf.py --pdfs data/samples --backend clip --run-id my_run

판정은 두 단계다.
  1) 페이지 크기 (규칙, 모든 백엔드 공통)
     - 가로/세로: 페이지 가로가 세로보다 길면 가로
     - 페이지 자체가 A4 의 --a4-ratio 보다 작으면 (예: A5) 바로 '작은 서류'
  2) A4 페이지 안에 작은 종이가 올라가 있는가 (백엔드마다 다름)
     - rule : 잉크가 있는 영역의 가로·세로가 페이지의 --a4-ratio 이상이면 A4 서류
     - clip : 이미지를 보고 설명문 두 묶음 중 어느 쪽에 가까운지 고른다 (제로샷 분류)

결과:
  outputs/<run-id>/<backend>/<A4_세로|A4_가로|작은서류_세로|작은서류_가로>/<pdf>_p01.jpg
  outputs/<run-id>/<backend>/predictions.csv
"""
import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

A4_MM = (210.0, 297.0)
PT_PER_MM = 72 / 25.4

# 제로샷 분류 설명문.
# v1: 결과를 보기 전에 정했다 (run1).
# v2: v1 의 가짜 샘플 실패 2건(작은 아포스티유, 작은 확인서)만 보고 '서류처럼 생긴 작은 종이' 설명을 더했다.
#     실제 서류(private_samples)는 v2 를 확정한 뒤 한 번만 돌린다 (run2).
PROMPTS = {
    "v1": {
        "A4": ["a scanned full page paper document",
               "a scanned A4 document page with text and tables",
               "a scanned certificate that fills the whole page"],
        "small": ["a small ID card or passport placed on a blank white sheet of paper",
                  "a small piece of paper lying on a larger empty white page",
                  "a scan of a passport on an otherwise blank page"],
    },
}
PROMPTS["v2"] = {
    "A4": PROMPTS["v1"]["A4"] + ["a scanned document page with text at the top and blank space below"],
    "small": PROMPTS["v1"]["small"] + [
        "a small certificate with a border placed in the middle of a large blank white page",
        "a small printed form surrounded by wide empty white margins on all sides",
    ],
}


def page_to_image(page, dpi):
    pix = page.get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def page_facts(page, a4_ratio):
    """페이지 크기만으로 알 수 있는 것."""
    w_mm, h_mm = page.rect.width / PT_PER_MM, page.rect.height / PT_PER_MM
    orient = "landscape" if w_mm > h_mm else "portrait"
    short, long_ = sorted((w_mm, h_mm))
    smaller_than_a4 = short < A4_MM[0] * a4_ratio or long_ < A4_MM[1] * a4_ratio
    return orient, smaller_than_a4, (w_mm, h_mm)


class RuleJudge:
    """잉크 영역 크기로 판단하는 기준선."""
    name = "rule"

    def __init__(self, a4_ratio, ink_threshold=200, edge_ignore=0.01):
        self.a4_ratio, self.ink, self.edge = a4_ratio, ink_threshold, edge_ignore

    def __call__(self, img):
        g = np.asarray(img.convert("L"))
        h, w = g.shape
        m = int(min(h, w) * self.edge)  # 스캔 가장자리 잡티는 무시
        ys, xs = np.where(g[m:h - m, m:w - m] < self.ink)
        if len(xs) == 0:
            return "small", {"ink_w": 0.0, "ink_h": 0.0}
        rw, rh = (xs.max() - xs.min()) / w, (ys.max() - ys.min()) / h
        size = "A4" if (rw >= self.a4_ratio and rh >= self.a4_ratio) else "small"
        return size, {"ink_w": round(float(rw), 4), "ink_h": round(float(rh), 4)}


class ClipJudge:
    """CLIP 제로샷 분류. 설명문 두 묶음 중 이미지에 가까운 쪽을 고른다."""
    name = "clip"

    def __init__(self, model_id, small_threshold, prompt_set="v1"):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_id).to(self.device).eval()
        self.proc = CLIPProcessor.from_pretrained(model_id)
        self.th = small_threshold
        p = PROMPTS[prompt_set]
        texts = p["A4"] + p["small"]
        with torch.no_grad():
            t = self.proc(text=texts, return_tensors="pt", padding=True).to(self.device)
            f = self.model.get_text_features(**t)
            f = getattr(f, "pooler_output", f)
            self.text = f / f.norm(dim=-1, keepdim=True)
        self.n_a4 = len(p["A4"])

    def __call__(self, img):
        torch = self.torch
        # 세로·가로 모두 비율을 유지한 채 흰 정사각형에 넣는다 (CLIP 기본 전처리는 가운데를 잘라낸다)
        side = max(img.size)
        sq = Image.new("RGB", (side, side), (255, 255, 255))
        sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        with torch.no_grad():
            x = self.proc(images=sq, return_tensors="pt").to(self.device)
            f = self.model.get_image_features(**x)
            f = getattr(f, "pooler_output", f)
            f = f / f.norm(dim=-1, keepdim=True)
            logits = (100.0 * f @ self.text.T).softmax(dim=-1)[0].cpu().numpy()
        p_small = float(logits[self.n_a4:].sum())
        return ("small" if p_small >= self.th else "A4"), {"p_small": round(p_small, 4)}


FOLDER = {("A4", "portrait"): "A4_세로", ("A4", "landscape"): "A4_가로",
          ("small", "portrait"): "작은서류_세로", ("small", "landscape"): "작은서류_가로"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdfs", required=True, help="PDF 가 들어 있는 폴더")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    ap.add_argument("--backend", choices=["rule", "clip"], default="clip")
    ap.add_argument("--dpi", type=int, default=200, help="JPG 저장 해상도")
    ap.add_argument("--judge-dpi", type=int, default=72, help="판정용 해상도 (낮아도 된다)")
    ap.add_argument("--a4-ratio", type=float, default=0.95, help="A4 로 인정하는 최소 비율 (가로·세로 각각)")
    ap.add_argument("--clip-model", default="openai/clip-vit-base-patch32")
    ap.add_argument("--clip-threshold", type=float, default=0.5, help="p_small 이 이 값 이상이면 작은 서류")
    ap.add_argument("--clip-prompts", choices=sorted(PROMPTS), default="v2", help="설명문 묶음 (v1: 첫 실행, v2: 개선)")
    ap.add_argument("--jpg-quality", type=int, default=92)
    a = ap.parse_args()

    out = Path(a.out) / a.run_id / a.backend
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(vars(a), ensure_ascii=False, indent=2), encoding="utf-8")

    t0 = time.perf_counter()
    judge = RuleJudge(a.a4_ratio) if a.backend == "rule" else ClipJudge(a.clip_model, a.clip_threshold, a.clip_prompts)
    load_s = time.perf_counter() - t0

    rows = []
    for pdf in sorted(Path(a.pdfs).glob("*.pdf")):
        doc = pymupdf.open(pdf)
        for i, page in enumerate(doc, start=1):
            t = time.perf_counter()
            orient, smaller, (w_mm, h_mm) = page_facts(page, a.a4_ratio)
            if smaller:
                size, extra, how = "small", {}, "page_size"
            else:
                size, extra = judge(page_to_image(page, a.judge_dpi))
                how = a.backend
            folder = out / FOLDER[(size, orient)]
            folder.mkdir(exist_ok=True)
            name = f"{pdf.stem}_p{i:02d}.jpg"
            page_to_image(page, a.dpi).save(folder / name, quality=a.jpg_quality)
            rows.append({"pdf": pdf.name, "page": i, "size": size, "orientation": orient, "decided_by": how,
                         "page_mm": f"{w_mm:.0f}x{h_mm:.0f}", "seconds": round(time.perf_counter() - t, 3),
                         "file": f"{FOLDER[(size, orient)]}/{name}", **extra})
            print(f"{pdf.name} p{i:02d}  {orient:9s} {size:5s} ({how}) {extra}")

    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(out / "predictions.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    total = time.perf_counter() - t0
    print(f"\n{len(rows)} pages, model load {load_s:.1f}s, total {total:.1f}s -> {out}")


if __name__ == "__main__":
    main()
