# 스캔 PDF 페이지 분류 PoC

문서 대행 업무에서 남은 스캔 PDF 를 **페이지별 JPG 로 떼어 내고**, 페이지마다
**가로/세로**와 **A4 서류 / A4 위에 놓인 작은 서류(여권·신분증·아포스티유)**로 나눠 폴더에 담는 도구입니다.
블로그 포스팅용 서류 이미지를 정리하는 수작업을 대신하려고 만들었습니다.

**결론부터:**
- 가로/세로는 AI 가 필요 없습니다. PDF 페이지 크기만으로 45쪽 전부 맞혔습니다.
- **A4 서류 / 작은 서류 구분에는 AI 가 필요합니다.** 흰 종이·흰 스캐너에서는 종이 경계가 보이지 않아, 규칙으로는
  "내용이 짧은 A4 서류"와 "A4 위의 작은 서류"를 가를 수 없습니다 (실제 서류 2/26).
- CLIP 제로샷 분류로 **실제 서류 25/26 (96.2%)**, 가짜 샘플 17/19 (89.5%). 작은 서류는 두 자료 모두 전부 잡았습니다.
- 수작업 14쪽 약 2분 → 도구 약 16초 (로컬 CPU).
- 남은 실패는 **회색 배경 위 장식 테두리 졸업장**입니다. 가짜 샘플에서 먼저 드러났고 실제 서류에서도 같은 이유로 틀렸습니다.

---

## 결과 미리보기 (가짜 샘플 19쪽)

초록 = 맞음, 빨강 = 틀림. 줄마다 도구가 넣은 폴더입니다.

### 기준선: 규칙 (글자 영역 95%) · 10/19

![규칙](docs/assets/result_rule.jpg)

A4 서류도 여백이 있어 글자 영역이 95% 에 못 미칩니다. A4 서류 9장이 작은 서류로 갔습니다.

### CLIP v1 (첫 설명문) · 17/19

![CLIP v1](docs/assets/result_clip_v1.jpg)

여권·신분증은 전부 잡았지만, **서류처럼 생긴 작은 종이**(아포스티유, 확인서)는 A4 로 봤습니다.

### CLIP v2 (설명문 보강) · 17/19

![CLIP v2](docs/assets/result_clip_v2.jpg)

작은 서류는 전부 잡았지만, 대신 **가로 졸업장 2장**을 작은 서류로 보냈습니다. 실제 서류에서는 25/26 입니다.

## 실제 서류 26쪽 (비공개, 로컬에서만 실행)

| | 규칙 (95%) | CLIP v1 | **CLIP v2** |
|---|---|---|---|
| 폴더까지 정확 | 2/26 | 23/26 | **25/26** |
| 작은 서류 잡아냄 | 2/2 | 1/2 | **2/2** |
| A4 를 작은 서류로 잘못 보냄 | 24 | 2 | 1 |

실제 서류는 작은 서류가 2장뿐이라 "전부 A4" 라고만 해도 25/26 이 나옵니다. 그래서 숫자보다
**무엇을 틀렸는지**가 중요합니다. 자세한 내용은 [검증 결과](docs/03_verification.md)에 있습니다.

---

## 저장소 구성

| 경로 | 내용 |
|---|---|
| [`docs/01_problem_definition.md`](docs/01_problem_definition.md) | **문제 정의서** — 도메인, 현재 문제, 개선 가설, 대상 사용자, 성공 기준 |
| [`docs/02_model_selection.md`](docs/02_model_selection.md) | **모델 선정 근거** — CLIP 을 고른 이유, SAM·YOLO 를 뺀 이유, 설명문 v1/v2 |
| [`docs/03_verification.md`](docs/03_verification.md) | **검증 결과** — 기준선 비교, 실패 사례, 실제 서류 페이지별 점수 |
| [`docs/04_limits_next.md`](docs/04_limits_next.md) | **한계와 다음 단계** — 실패 대응, 개인정보 마스킹 계획 |
| [`poc/split_pdf.py`](poc/split_pdf.py) | 본체. PDF → JPG 저장 + 폴더 분류 |
| [`poc/score.py`](poc/score.py) | 정답표와 비교해 채점 |
| [`poc/overview.py`](poc/overview.py) | 결과를 한 장의 그림으로 모음 |
| [`notebooks/run_poc_colab.ipynb`](notebooks/run_poc_colab.ipynb) | Colab 에서 전체 실행 |
| [`data/make_samples.py`](data/make_samples.py) | 가짜 샘플 생성기 (실제 서류 구성을 본뜸) |
| [`data/samples/`](data/samples/) | 가짜 스캔 PDF 3개, 19쪽. 이름·기관·번호 전부 가짜, SPECIMEN 표시 |
| [`data/ground_truth.csv`](data/ground_truth.csv) | **모델을 돌리기 전에** 확정한 정답 |
| `outputs/<run>/<backend>/` | `predictions.csv`(판정), `score.txt`(채점), `config.json`(설정). JPG 는 용량 때문에 올리지 않음 |

실제 고객 서류(`private_samples/`)와 그 결과(`outputs_private/`)는 `.gitignore` 로 제외했습니다.

---

## 실행 방법

### 방법 A — Google Colab (권장)

[Colab 에서 열기](https://colab.research.google.com/github/weriousdf/scan-pdf-sorter-poc/blob/main/notebooks/run_poc_colab.ipynb)
→ **런타임 → 모두 실행**. 저장소를 내려받고, 규칙·CLIP v1·CLIP v2 를 차례로 돌려 채점하고, 결과를 그림으로 보여 줍니다.
GPU 가 없어도 됩니다.

### 방법 B — 로컬 PC

GPU 는 필요 없습니다. 처음 실행할 때 CLIP 모델(약 600MB)을 내려받습니다.

```bash
git clone https://github.com/weriousdf/scan-pdf-sorter-poc.git
cd scan-pdf-sorter-poc
pip install -r requirements.txt
python poc/split_pdf.py --pdfs data/samples --backend clip --run-id my_run
python poc/score.py --truth data/ground_truth.csv --pred outputs/my_run/clip/predictions.csv
```

내 PDF 를 돌릴 때는 `--pdfs` 에 PDF 가 든 폴더를 주면 됩니다. 결과는 이렇게 나옵니다.

```
outputs/my_run/clip/
├── A4_세로/        sample_p01.jpg, sample_p02.jpg, ...
├── A4_가로/
├── 작은서류_세로/
├── 작은서류_가로/
└── predictions.csv
```

### 주요 인자

| 인자 | 뜻 | 기본값 |
|---|---|---|
| `--backend` | `rule`(규칙) / `clip`(AI) | `clip` |
| `--clip-prompts` | 설명문 묶음 `v1` / `v2` | `v2` |
| `--clip-threshold` | "작은 서류" 확률이 이 값 이상이면 작은 서류 | `0.5` |
| `--a4-ratio` | A4 로 인정하는 최소 비율 (가로·세로 각각) | `0.95` |
| `--dpi` | 저장 JPG 해상도 | `200` |
| `--judge-dpi` | 판정용 해상도 | `72` |
| `--run-id` | 결과 폴더 이름. 이전 결과를 덮어쓰지 않음 | 실행 시각 |

---

## 실행 환경

| | Colab | 로컬 |
|---|---|---|
| 하드웨어 | Tesla T4 | CPU (GPU 없음) |
| torch / transformers | 2.11.0 / 5.16.1 | 2.13.0 / 5.14.1 |
| pymupdf | 1.28.2 | 1.28.2 |

두 환경에서 가짜 샘플 결과(CLIP v1)는 소수점 넷째 자리까지 같았습니다.

모델: `openai/clip-vit-base-patch32` (MIT). PyMuPDF 는 AGPL 입니다 (→ [모델 선정 근거](docs/02_model_selection.md)).

## 데모 URL

배포하지 않았습니다. 고객 서류를 다루는 도구라 외부 서버에 올리지 않고 로컬에서 쓰는 것을 전제로 합니다.
