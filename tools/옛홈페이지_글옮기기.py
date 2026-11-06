"""옛 홈페이지(hanareum.or.kr) 백업 → 새 홈페이지 content/posts, content/uploads 변환.

사용법: python convert_old.py <저장소폴더> <게시판이름>=<백업폴더> ...
  각 백업폴더 아래 게시글/*/정보.json 을 읽는다.
글 ID 는 old-<게시판코드>-<옛 글번호> 로 정해서 여러 번 돌려도 같은 글을 덮어쓴다.
"""
import base64
import io
import json
import os
import re
import sys
from glob import glob

from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image, ImageOps

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_W = 1600
BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "blockquote"}
BUDGET = re.compile(r"예산|결산|후원금품")
PRESS = re.compile(r"^\s*[\[(]\s*([^\])]{1,30}?)\s*[\])]\s*(.+)$")


def category_of(board, title):
    if board in ("행사자료", "사진자료", "이달의행사"):
        return "활동 소식"
    if board == "보도자료":
        return "언론 보도"
    if board == "공지사항":
        return "예산·결산 공고" if BUDGET.search(title) else "공지"
    if board == "100세시대":
        return "공지"
    raise ValueError(board)


def norm_date(info):
    for v in (info.get("작성일시"), info.get("날짜")):
        m = re.match(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})", str(v or ""))
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def body_from_html(html, photo_no):
    """본문 HTML → 새 홈페이지 본문 글. 사진 자리는 [사진N] 한 줄."""
    soup = BeautifulSoup(html or "", "html.parser")
    for c in soup.find_all(string=lambda s: s.__class__.__name__ == "Comment"):
        c.extract()
    for t in soup.find_all(["script", "style"]):
        t.decompose()
    out = []

    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                out.append(str(ch).replace("\xa0", " ").replace("\r", "").replace("\n", " "))
            elif isinstance(ch, Tag):
                if ch.name == "img":
                    n = photo_no.get(ch.get("src", ""))
                    if n:
                        out.append(f"\n\n[사진{n}]\n\n")
                    continue
                if ch.name == "h3" and ch.get_text(strip=True) == "첨부파일":
                    return True  # 백업 스크립트가 붙인 첨부 목록부터는 버림
                block = ch.name in BLOCK
                if block:
                    out.append("\n")
                if walk(ch):
                    return True
                if block:
                    out.append("\n")
                if ch.name in ("td", "th"):
                    out.append(" ")
        return False

    walk(soup)
    text = "".join(out)
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in text.split("\n")]
    # 빈 줄 하나 이상 = 문단 구분, 이어진 줄 = 문단 안 줄바꿈
    paras, cur = [], []
    for l in lines:
        if l:
            if re.fullmatch(r"\[사진\d+\]", l):
                if cur:
                    paras.append("\n".join(cur)); cur = []
                paras.append(l)
            else:
                cur.append(l)
        elif cur:
            paras.append("\n".join(cur)); cur = []
    if cur:
        paras.append("\n".join(cur))
    return "\n\n".join(paras).strip()


def video_link(html):
    """본문에 박힌 영상(iframe/embed) 주소. 유튜브는 보기 주소로 바꾼다."""
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup.find_all(["iframe", "embed", "object"]):
        src = t.get("src") or t.get("data") or ""
        if not src:
            p = t.find("param", attrs={"name": re.compile("movie|src", re.I)})
            src = p.get("value", "") if p else ""
        if src.startswith("//"):
            src = "https:" + src
        m = re.search(r"youtube(?:-nocookie)?\.com/(?:embed|v)/([\w-]{6,})", src)
        if m:
            return "https://www.youtube.com/watch?v=" + m.group(1)
        if re.match(r"https?://", src) and "hanareum.or.kr" not in src:
            return src
    return ""


def save_photo(src, dst):
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if getattr(im, "is_animated", False):
            im.seek(0)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    data = buf.getvalue()
    if not (os.path.exists(dst) and open(dst, "rb").read() == data):
        with open(dst, "wb") as f:
            f.write(data)
    return len(data)


def copy_file(src, dst):
    data = open(src, "rb").read()
    if not (os.path.exists(dst) and open(dst, "rb").read() == data):
        with open(dst, "wb") as f:
            f.write(data)
    return len(data)


def convert(repo, board, folder, report):
    posts_dir = os.path.join(repo, "content", "posts")
    entries = []
    for info_path in sorted(glob(os.path.join(folder, "게시글", "*", "정보.json"))):
        pdir = os.path.dirname(info_path)
        info = json.load(open(info_path, encoding="utf-8"))
        code = info["원본주소"].rstrip("/").split("/")[-2]
        pid = f"old-{code}-{info['id']}"
        title = re.sub(r"\s+", " ", info["제목"]).strip()
        if re.search(r"게시판\s*입니다\.?$", title):  # 게시판 소개용 글
            report["skipped"].append(title)
            continue
        date = norm_date(info)
        cat = category_of(board, title)
        up_rel = f"content/uploads/{pid}"
        up_dir = os.path.join(repo, *up_rel.split("/"))
        os.makedirs(up_dir, exist_ok=True)

        photos, files, photo_no, size = [], [], {}, 0
        for x in info.get("파일", []):
            src = os.path.join(pdir, *x["파일"].split("/"))
            if not x.get("성공") or not os.path.exists(src):
                report["missing"].append(f"{pid} {x['파일']}")
                continue
            ext = os.path.splitext(src)[1].lower()
            if ext in IMG_EXT:
                n = len(photos) + 1
                name = f"{n}.jpg"
                try:
                    size += save_photo(src, os.path.join(up_dir, name))
                except Exception as e:  # 깨진 사진
                    report["missing"].append(f"{pid} {x['파일']} ({e})")
                    continue
                photos.append(f"{up_rel}/{name}")
                photo_no[x["파일"]] = n
            else:
                name = f"file{len(files) + 1}{ext}"
                size += copy_file(src, os.path.join(up_dir, name))
                files.append({"name": os.path.basename(x.get("원본주소", name)).split("?")[0] or name, "path": f"{up_rel}/{name}"})
        # 본문에 직접 박힌 그림(data:image/...;base64,...)
        for m in re.finditer(r'src="(data:image/[a-z+]+;base64,([A-Za-z0-9+/=\s]+))"', info.get("본문HTML", "")):
            if m.group(1) in photo_no:
                continue
            tmp = os.path.join(up_dir, "_tmp")
            try:
                with open(tmp, "wb") as f:
                    f.write(base64.b64decode(m.group(2)))
                n = len(photos) + 1
                size += save_photo(tmp, os.path.join(up_dir, f"{n}.jpg"))
                photos.append(f"{up_rel}/{n}.jpg")
                photo_no[m.group(1)] = n
            except Exception as e:
                report["missing"].append(f"{pid} data-image ({e})")
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        for x in info.get("첨부파일", []) or []:
            src = os.path.join(pdir, *x["파일"].split("/"))
            if not x.get("성공") or not os.path.exists(src):
                report["missing"].append(f"{pid} {x['파일']}")
                continue
            ext = os.path.splitext(src)[1].lower()
            name = f"file{len(files) + 1}{ext}"
            size += copy_file(src, os.path.join(up_dir, name))
            files.append({"name": x.get("파일명") or name, "path": f"{up_rel}/{name}"})
        if not os.listdir(up_dir):
            os.rmdir(up_dir)

        body = body_from_html(info.get("본문HTML", ""), photo_no)
        post = {"id": pid, "category": cat, "title": title, "date": date}
        link = video_link(info.get("본문HTML", ""))
        if cat == "언론 보도":
            m = PRESS.match(title)
            if m:
                post["press"], post["title"] = m.group(1).strip(), m.group(2).strip()
            if not link:
                urls = re.findall(r"https?://(?![^\s/]*hanareum\.or\.kr)[^\s<>\"')\]]+", info.get("본문", "") + " " + info.get("본문HTML", ""))
                urls = [u for u in urls if not re.search(r"\.(jpe?g|png|gif|bmp|webp)$", u, re.I)]
                link = urls[0] if urls else ""
        if link:
            post["link"] = link
            report["links"] += 1
        post["body"] = body
        if photos:
            post["photo"] = photos[0]
            post["photos"] = photos
        if files:
            post["files"] = files
        post["source"] = info["원본주소"]

        with open(os.path.join(posts_dir, pid + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(post, f, ensure_ascii=False, indent=2)
            f.write("\n")
        entry = {"id": pid, "category": post["category"], "title": post["title"], "date": date}
        if photos:
            entry["photo"] = photos[0]
        if post.get("press"):
            entry["press"] = post["press"]
        entries.append(entry)
        report["count"][board] = report["count"].get(board, 0) + 1
        report["bytes"] += size
        if not date:
            report["nodate"].append(pid)
        if not body and not photos and not files:
            report["empty"].append(f"{pid} {title}")
    return entries


def main():
    repo = sys.argv[1]
    report = {"count": {}, "bytes": 0, "links": 0, "skipped": [], "missing": [], "nodate": [], "empty": []}
    new = []
    for arg in sys.argv[2:]:
        board, folder = arg.split("=", 1)
        new += convert(repo, board, folder, report)
    idx_path = os.path.join(repo, "content", "posts", "index.json")
    old = json.load(open(idx_path, encoding="utf-8")).get("items", [])
    ids = {e["id"] for e in new}
    items = [e for e in old if e.get("id") not in ids] + new
    items.sort(key=lambda e: (e.get("date", ""), e["id"]), reverse=True)
    with open(idx_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"items": items}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({**report, "MB": round(report["bytes"] / 1048576, 1), "index": len(items)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
