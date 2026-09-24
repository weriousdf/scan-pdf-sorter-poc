"""predictions.csv 를 정답표와 비교해 채점한다.

    python poc/score.py --truth data/ground_truth.csv --pred outputs/my_run/clip/predictions.csv

--sweep 을 주면 판정 값(rule 은 잉크 비율, clip 은 p_small)의 기준을 바꿔 가며
'어떤 기준을 골랐어도 몇 장은 틀렸는가'를 함께 보여 준다.
"""
import argparse
import csv


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return {(r["pdf"], int(r["page"])): r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    truth, pred = load(a.truth), load(a.pred)
    keys = sorted(truth)
    missing = [k for k in keys if k not in pred]
    if missing:
        raise SystemExit(f"예측이 없는 페이지: {missing}")

    n = len(keys)
    ori_ok = sum(truth[k]["orientation"] == pred[k]["orientation"] for k in keys)
    size_ok = sum(truth[k]["size"] == pred[k]["size"] for k in keys)
    both_ok = sum(truth[k]["orientation"] == pred[k]["orientation"] and truth[k]["size"] == pred[k]["size"] for k in keys)
    print(f"페이지 {n}장")
    print(f"  가로/세로      {ori_ok}/{n}")
    print(f"  A4/작은 서류   {size_ok}/{n}")
    print(f"  폴더까지 정확  {both_ok}/{n}")

    cm = {(t, p): 0 for t in ("A4", "small") for p in ("A4", "small")}
    for k in keys:
        cm[(truth[k]["size"], pred[k]["size"])] += 1
    print("\n  정답\\예측     A4   small")
    for t in ("A4", "small"):
        print(f"  {t:10s} {cm[(t, 'A4')]:5d} {cm[(t, 'small')]:6d}")

    wrong = [k for k in keys if truth[k]["size"] != pred[k]["size"] or truth[k]["orientation"] != pred[k]["orientation"]]
    if wrong:
        print("\n틀린 페이지")
        for k in wrong:
            p = pred[k]
            extra = {c: p[c] for c in ("ink_w", "ink_h", "p_small") if p.get(c)}
            print(f"  {k[0]} p{k[1]:02d}  정답 {truth[k]['size']}/{truth[k]['orientation']}  "
                  f"예측 {p['size']}/{p['orientation']} ({p['decided_by']}) {extra}  | {truth[k].get('note', '')}")

    if a.sweep:
        judged = [k for k in keys if pred[k]["decided_by"] != "page_size"]
        fixed_wrong = sum(truth[k]["size"] != pred[k]["size"] for k in keys if pred[k]["decided_by"] == "page_size")
        if pred[judged[0]].get("p_small"):
            score = {k: float(pred[k]["p_small"]) for k in judged}
            is_small = lambda k, th: score[k] >= th
            label = "p_small >= 기준 → 작은 서류"
        else:
            score = {k: min(float(pred[k]["ink_w"]), float(pred[k]["ink_h"])) for k in judged}
            is_small = lambda k, th: score[k] < th
            label = "잉크 영역(짧은 쪽 비율) < 기준 → 작은 서류"
        cands = sorted(set(score.values()) | {0.0, 1.01})
        best = min(cands, key=lambda th: sum((truth[k]["size"] == "small") != is_small(k, th) for k in judged))
        errs = sum((truth[k]["size"] == "small") != is_small(k, th=best) for k in judged)
        print(f"\n[기준값 탐색] {label}")
        print(f"  가장 좋은 기준 {best:.4f} 에서도 {errs + fixed_wrong}장 틀림 (판정 대상 {len(judged)}장)")
        print("  판정 값 (정답별):")
        for t in ("A4", "small"):
            vals = sorted(round(score[k], 3) for k in judged if truth[k]["size"] == t)
            print(f"    {t:5s} {vals}")


if __name__ == "__main__":
    main()
