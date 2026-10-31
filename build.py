"""src/pages 의 본문에 공통 머리말·꼬리말을 붙여 최상위 폴더에 HTML 파일을 만듭니다.

사용법:  python build.py

각 페이지 맨 첫 줄에는 다음과 같은 설정 줄이 있어야 합니다.
<!--meta {"title": "...", "description": "...", "nav": "about", "news": true} -->
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SITE = "서울시 강남구 재가노인복지기관"

header = (ROOT / "src/partials/header.html").read_text(encoding="utf-8")
footer = (ROOT / "src/partials/footer.html").read_text(encoding="utf-8")

for page in sorted((ROOT / "src/pages").glob("*.html")):
    text = page.read_text(encoding="utf-8")
    m = re.match(r"<!--meta (.*?) -->\n", text)
    if not m:
        raise SystemExit(f"{page.name}: 첫 줄에 <!--meta ... --> 설정이 없습니다.")
    meta = json.loads(m.group(1))
    body = text[m.end():]

    title = SITE if page.stem == "index" else f"{meta['title']} | {SITE}"
    head = header.replace("{{TITLE}}", title).replace("{{DESCRIPTION}}", meta["description"])
    if meta.get("nav"):
        head = head.replace(f'data-nav="{meta["nav"]}"', f'data-nav="{meta["nav"]}" aria-current="page"')

    scripts = ['<script src="assets/news.js"></script>'] if meta.get("news") else []
    scripts.append('<script src="assets/site.js"></script>')
    foot = footer.replace("{{SCRIPTS}}", "\n  ".join(scripts))

    (ROOT / page.name).write_text(head + body + foot, encoding="utf-8")
    print("만듦:", page.name)
