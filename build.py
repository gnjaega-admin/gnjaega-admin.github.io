"""src/pages 의 본문에 공통 머리말·꼬리말을 붙여 최상위 폴더에 HTML 파일을 만듭니다.
검색 포털용 sitemap.xml, robots.txt 도 함께 만듭니다.

사용법:  python build.py

각 페이지 맨 첫 줄에는 다음과 같은 설정 줄이 있어야 합니다.
<!--meta {"title": "...", "description": "...", "nav": "about", "news": true} -->
"""
import datetime
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SITE = "서울시 강남구 재가노인복지기관"
BASE = "https://www.gnjaega.or.kr/"

# 검색 포털용 기관 정보(구조화 데이터). 첫 화면에만 넣는다.
ORG_JSONLD = """  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "서울시 강남구 재가노인복지기관",
    "alternateName": "서울시강남구재가노인복지기관",
    "url": "https://www.gnjaega.or.kr/",
    "logo": "https://www.gnjaega.or.kr/assets/og-image.png",
    "telephone": "+82-2-573-7943",
    "faxNumber": "+82-2-576-7943",
    "email": "gnjaega@gnjaega.or.kr",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "개포로24길 29, 지하 1층 (하임빌딩)",
      "addressLocality": "강남구",
      "addressRegion": "서울특별시",
      "postalCode": "06308",
      "addressCountry": "KR"
    },
    "parentOrganization": { "@type": "Organization", "name": "사단법인 오픈도어", "url": "https://opendoors.co.kr/" }
  }
  </script>
"""

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
    url = BASE if page.stem == "index" else BASE + page.name
    head = (header.replace("{{TITLE}}", title)
            .replace("{{DESCRIPTION}}", meta["description"])
            .replace("{{URL}}", url)
            .replace("{{JSONLD}}", ORG_JSONLD if page.stem == "index" else ""))
    if meta.get("nav"):
        head = head.replace(f'data-nav="{meta["nav"]}"', f'data-nav="{meta["nav"]}" aria-current="page"')

    scripts = ['<script src="assets/news.js"></script>'] if meta.get("news") else []
    scripts.append('<script src="assets/site.js"></script>')
    foot = footer.replace("{{SCRIPTS}}", "\n  ".join(scripts))

    (ROOT / page.name).write_text(head + body + foot, encoding="utf-8")
    print("만듦:", page.name)

# 검색 포털용 파일: 사이트 지도(상세 글 틀인 post 제외)와 로봇 안내
today = datetime.date.today().isoformat()
stems = sorted((p.stem for p in (ROOT / "src/pages").glob("*.html") if p.stem != "post"), key=lambda s: (s != "index", s))
urls = "".join(f"  <url><loc>{BASE if s == 'index' else BASE + s + '.html'}</loc><lastmod>{today}</lastmod></url>\n" for s in stems)
(ROOT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
    encoding="utf-8")
(ROOT / "robots.txt").write_text(
    "User-agent: *\nAllow: /\nDisallow: /src/\nDisallow: /tools/\nDisallow: /docs/\n\nSitemap: " + BASE + "sitemap.xml\n",
    encoding="utf-8")
print("만듦: sitemap.xml, robots.txt")
