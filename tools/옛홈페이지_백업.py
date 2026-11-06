"""한아름 홈페이지 게시판 백업 스크립트.

사용법: python backup_board.py <board_code> <게시판이름> <저장폴더>
예:     python backup_board.py sub4_1 행사자료 "H:/.../게시글/행사자료"
"""
import csv
import json
import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://www.hanareum.or.kr"
FILE_EXT = re.compile(r"\.(jpe?g|png|gif|bmp|webp|pdf|hwp|hwpx|docx?|xlsx?|pptx?|zip)$", re.I)

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (hanareum board backup)"


def get(url):
    for attempt in range(3):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2)


def safe_name(s, limit=60):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", s).strip().rstrip(".")
    return s[:limit]


def list_posts(board):
    posts, seen, page = [], set(), 1
    while True:
        url = f"{BASE}/bbs_shop/list.htm?page={page}&list_mode=board&board_code={board}"
        soup = BeautifulSoup(get(url).text, "html.parser")
        new = 0
        for tr in soup.find_all("tr"):
            # 1페이지는 /bbs/sub4_1/123, 2페이지부터는 read.htm?...&idx=123 형식
            a = tr.find("a", href=re.compile(rf"/bbs/{board}/\d+$|read\.htm\?.*board_code={board}&.*idx=\d+"))
            if not a:
                continue
            pid = re.search(r"(\d+)$", a["href"]).group(1)
            a["href"] = f"/bbs/{board}/{pid}"
            if pid in seen:
                # 공지글은 매 페이지 위에 반복되고, 원래 번호 자리에도 한 번 나온다
                num = tr.find("td").get_text(strip=True)
                if num.isdigit():
                    for p in posts:
                        if p["id"] == pid and not p["번호"].isdigit():
                            p["번호"], p["공지"] = num, "Y"
                continue
            seen.add(pid)
            new += 1
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            posts.append({
                "id": pid,
                "번호": cells[0] if cells else "",
                "제목": a.get_text(" ", strip=True),
                "이름": cells[2] if len(cells) > 2 else "",
                "날짜": cells[3] if len(cells) > 3 else "",
                "조회수": cells[4] if len(cells) > 4 else "",
                "원본주소": urljoin(BASE, a["href"]),
            })
        print(f"목록 {page}페이지: 새 글 {new}개")
        if new == 0:
            break
        page += 1
        time.sleep(0.3)
    return posts


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    try:
        data = get(url).content
    except requests.RequestException as e:
        print(f"   ! 다운로드 실패 {url}: {e}")
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def backup_post(post, board_name, out_root):
    num = post["번호"] if post["번호"].isdigit() else "공지"
    folder = safe_name(f"{num.zfill(3) if num.isdigit() else num}_{post['날짜']}_{post['제목']}")
    pdir = os.path.join(out_root, "게시글", folder)
    os.makedirs(os.path.join(pdir, "사진"), exist_ok=True)

    html = get(post["원본주소"]).text
    with open(os.path.join(pdir, "원본페이지.html"), "w", encoding="utf-8") as f:
        f.write(html)
    soup = BeautifulSoup(html, "html.parser")

    head = soup.select_one(".info_head dd")
    post["작성일시"] = head.get_text(strip=True) if head else post["날짜"]
    body = soup.select_one("#tblContent .ccbody") or soup.select_one("#tblContent")

    files, idx = [], 0
    if body:
        # 사진/첨부파일 내려받고 본문 안 주소를 로컬 경로로 바꾼다
        targets = []
        for img in body.find_all("img"):
            if img.get("src"):
                targets.append((img, "src", img["src"]))
        for a in body.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"popview\('([^']+)'\)", href)
            if m:
                a["href"] = m.group(1)
                href = a["href"]
            if FILE_EXT.search(urlparse(href).path):
                targets.append((a, "href", href))
        local_of = {}
        for el, attr, src in targets:
            url = urljoin(BASE, src)
            if url not in local_of:
                idx += 1
                ext = os.path.splitext(unquote(urlparse(url).path))[1].lower() or ".jpg"
                name = f"{idx:02d}{ext}"
                ok = download(url, os.path.join(pdir, "사진", name))
                local_of[url] = f"사진/{name}" if ok else url
                files.append({"순서": idx, "파일": f"사진/{name}", "원본주소": url, "성공": ok})
                time.sleep(0.2)
            el[attr] = local_of[url]

        text = "\n".join(
            line.strip() for line in body.get_text("\n").replace("\xa0", " ").splitlines()
        )
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        body_html = body.decode_contents().strip()
    else:
        text, body_html = "", ""

    # 본문 아래 따로 붙은 첨부파일 (file_download(0), (1) ...)
    attachments = []
    names = re.findall(r'file_name_arr\[(\d+)\]\s*=\s*"([^"]*)"', html)
    board = post["원본주소"].rstrip("/").split("/")[-2]
    for no, name in dict(names).items():
        os.makedirs(os.path.join(pdir, "첨부파일"), exist_ok=True)
        local = f"첨부파일/{safe_name(name, 120)}"
        url = f"{BASE}/bbs_shop/file_download.php?board_code={board}&board_idx={post['id']}&sel_no={no}"
        ok = download(url, os.path.join(pdir, local))
        attachments.append({"파일명": name, "파일": local, "원본주소": url, "성공": ok})
        time.sleep(0.2)
    if attachments:
        text += "\n\n[첨부파일]\n" + "\n".join(a["파일"] for a in attachments)
        body_html += "\n<h3>첨부파일</h3>\n<ul>" + "".join(
            f'<li><a href="{a["파일"]}">{a["파일명"]}</a></li>' for a in attachments) + "</ul>"

    with open(os.path.join(pdir, "본문.txt"), "w", encoding="utf-8") as f:
        f.write(f"제목: {post['제목']}\n작성일: {post['작성일시']}\n작성자: {post['이름']}\n"
                f"원본: {post['원본주소']}\n\n{text}\n")
    with open(os.path.join(pdir, "본문.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{post['제목']}</title>
<style>body{{max-width:760px;margin:24px auto;padding:0 16px;font-family:'Malgun Gothic',sans-serif;line-height:1.6}}
img{{max-width:100%}} .meta{{color:#666;font-size:14px;border-bottom:1px solid #ddd;padding-bottom:8px}}</style>
</head><body><h1>{post['제목']}</h1>
<p class="meta">{board_name} · {post['작성일시']} · {post['이름']} · 조회수 {post['조회수']}<br>
원본: <a href="{post['원본주소']}">{post['원본주소']}</a></p>
{body_html}
</body></html>""")

    post.update({"폴더": f"게시글/{folder}", "사진수": len(files), "첨부수": len(attachments),
                 "실패": sum(not f["성공"] for f in files + attachments)})
    with open(os.path.join(pdir, "정보.json"), "w", encoding="utf-8") as f:
        json.dump({**post, "게시판": board_name, "본문": text, "본문HTML": body_html,
                   "파일": files, "첨부파일": attachments}, f, ensure_ascii=False, indent=2)
    return post


def main():
    board, board_name, out_root = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_root, exist_ok=True)
    posts = list_posts(board)
    print(f"총 {len(posts)}개 글")
    for i, p in enumerate(posts, 1):
        print(f"[{i}/{len(posts)}] {p['번호']} {p['제목']}")
        try:
            backup_post(p, board_name, out_root)
        except Exception as e:
            print(f"   ! 실패: {e}")
            p["오류"] = str(e)
        time.sleep(0.3)

    cols = ["번호", "공지", "제목", "이름", "날짜", "조회수", "사진수", "첨부수", "실패", "원본주소", "폴더", "오류"]
    with open(os.path.join(out_root, "목록.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(posts)
    with open(os.path.join(out_root, "목록.json"), "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("완료")


if __name__ == "__main__":
    main()
