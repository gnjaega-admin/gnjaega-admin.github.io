"""홈페이지 소식 글(content/posts/*.json)에 개인정보가 들어 있는지 점검합니다.

사용법:  python tools/개인정보_점검.py            (모든 글 점검)
         python tools/개인정보_점검.py 글ID ...   (특정 글만 점검, 예: old-board5_1-87682)

찾는 것 (docs/소식-문체가이드.md 5번 기준)
- 반드시 고쳐야 함: 주민등록번호, 카드번호, 계좌번호, 휴대전화 번호
- 확인 필요: 개인 메일 주소(포털 메일), 성함이 붙은 어르신 호칭, 개인 이름이 많이 나열된 글(후원자 명단 등),
             건강·질병·수급 정보로 보이는 표현, 명단·대상자 이름의 첨부파일

고쳐야 할 내용이 있으면 끝에 '고쳐야 함'을 알리고 종료 코드 1을 돌려줍니다.
결과에는 찾은 값을 그대로 쓰지 않고 앞부분만 보여 줍니다.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

# 기관이 공개하려고 적는 연락처는 개인정보로 보지 않는다.
ALLOWED_EMAILS = {"gnjaega@gnjaega.or.kr", "hanareum7943@hanmail.net", "hanareum7943@daum.net", "hanareum7943@daum.com"}
PORTAL = r"(?:naver\.com|daum\.net|hanmail\.net|gmail\.com|nate\.com|hotmail\.com|kakao\.com|icloud\.com)"

MUST = [
    ("주민등록번호", re.compile(r"(?<!\d)\d{6}\s?-\s?[1-4]\d{6}(?!\d)")),
    ("카드번호", re.compile(r"(?<!\d)\d{4}-\d{4}-\d{4}-\d{4}(?!\d)")),
    ("계좌번호", re.compile(r"(?:계좌|예금주|입금)[^\n]{0,20}?\d{2,6}-\d{2,6}-\d{2,8}")),
    ("휴대전화 번호", re.compile(r"(?<!\d)01[016789][-.\s)]?\d{3,4}[-.\s]?\d{4}(?!\d)")),
]
SUR = "김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용"
CHECK = [
    ("개인 메일 주소", re.compile(r"[\w.+-]+@" + PORTAL)),
    ("성함이 붙은 어르신 호칭", re.compile(r"(?<![가-힣])(?!나들이|이웃의|이번에|지역별)[" + SUR + r"][가-힣][가-힣](?<![운는한은을의시구동들던된적별해고며서와과로에])\s?(?:어르신|할머니|할아버지)")),
    ("건강·형편 정보", re.compile(r"치매|뇌졸중|암 투병|투석|기초생활\s?수급|수급자|장애\s?\d급|진단(?:을|받)")),
]
NAME_TOKEN = re.compile(r"(?<![가-힣○])[" + SUR + r"][가-힣]{2}(?:님)?(?![가-힣○])")
LIST_TITLE = re.compile(r"후원자|명단|명부|합격자|당첨")


def peek(v):
    v = v.strip()
    return v[:4] + "…" if len(v) > 4 else v


def check(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    text = (d.get("title") or "") + "\n" + (d.get("body") or "")
    must, warn = [], []
    for name, pat in MUST:
        hits = pat.findall(text)
        if hits:
            must.append(f"{name} {len(hits)}건 ({', '.join(sorted({peek(h) for h in hits})[:3])})")
    for name, pat in CHECK:
        hits = [h for h in pat.findall(text) if h.lower() not in ALLOWED_EMAILS]
        if hits:
            warn.append(f"{name} {len(hits)}건 ({', '.join(sorted({peek(h) for h in hits})[:3])})")
    if LIST_TITLE.search(d.get("title") or ""):
        n = len(NAME_TOKEN.findall(d.get("body") or ""))
        if n >= 5:
            warn.append(f"개인 이름으로 보이는 말 {n}개 — 명단이면 단체명만 두고 개인은 '김○○'처럼 가리세요")
    for f in d.get("files") or []:
        if re.search(r"명단|명부|대상자|합격자|신청자", f.get("name", "")):
            warn.append(f"첨부파일 확인: {f.get('name')}")
    if LIST_TITLE.search(d.get("title") or "") and d.get("photos"):
        warn.append("명단 글에 사진이 있음 — 사진 속에 개인 이름이 있는지 확인")
    return d, must, warn


def main(argv):
    files = [POSTS / f"{a}.json" for a in argv] if argv else sorted(p for p in POSTS.glob("*.json") if p.name != "index.json")
    n_must = n_warn = 0
    for p in files:
        if not p.exists():
            print(f"[없음] {p.name}")
            continue
        d, must, warn = check(p)
        if must or warn:
            print(f"\n■ {p.stem}  {d.get('date', '')}  {d.get('title', '')}")
            for m in must:
                print("   [고쳐야 함]", m)
            for w in warn:
                print("   [확인 필요]", w)
        n_must += bool(must)
        n_warn += bool(warn) and not must
    print(f"\n점검한 글 {len(files)}개 · 고쳐야 함 {n_must}개 · 확인 필요 {n_warn}개")
    if n_must:
        print("고쳐야 함: 위 글은 공개하기 전에 해당 내용을 지우거나 가려 주세요.")
    return 1 if n_must else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
