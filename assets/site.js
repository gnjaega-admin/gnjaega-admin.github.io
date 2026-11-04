// 글자 크기 조절: 선택 값은 이 브라우저에만 저장(개인정보 아님, 저장 실패해도 동작)
(function () {
  var root = document.documentElement;
  var KEY = 'fontSize';
  function apply(level) {
    root.classList.remove('fs-1', 'fs-2');
    if (level > 0) root.classList.add('fs-' + level);
    document.querySelectorAll('[data-fs]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(Number(b.dataset.fs) === level));
    });
  }
  var saved = 0;
  try { saved = Number(localStorage.getItem(KEY)) || 0; } catch (e) {}
  apply(saved);
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-fs]');
    if (!b) return;
    var level = Number(b.dataset.fs);
    apply(level);
    try { localStorage.setItem(KEY, String(level)); } catch (err) {}
  });
})();

// 모바일 전체 메뉴
(function () {
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('gnb');
  if (!btn || !nav) return;
  function set(open) {
    nav.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', String(open));
    btn.querySelector('use').setAttribute('href', 'assets/icons.svg#i-' + (open ? 'close' : 'menu'));
    btn.querySelector('.label').textContent = open ? '닫기' : '전체메뉴';
  }
  btn.addEventListener('click', function () { set(!nav.classList.contains('is-open')); });
  nav.addEventListener('click', function (e) { if (e.target.closest('a')) set(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('is-open')) { set(false); btn.focus(); } });
})();

// 하위 메뉴(LNB) 탭: data-tabs 가 있는 페이지는 고른 항목의 내용만 보여줌
(function () {
  var content = document.querySelector('.content[data-tabs]');
  if (!content) return;
  var links = Array.prototype.slice.call(document.querySelectorAll('.lnb a[href^="#"]'));
  var ids = links.map(function (a) { return a.getAttribute('href').slice(1); });
  function show(id, scroll) {
    if (ids.indexOf(id) < 0) id = ids[0];
    ids.forEach(function (x) { var s = document.getElementById(x); if (s) s.hidden = x !== id; });
    links.forEach(function (a) {
      var on = a.getAttribute('href') === '#' + id;
      a.classList.toggle('is-active', on);
      if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    if (scroll) document.querySelector('.sub-layout').scrollIntoView();
  }
  links.forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var id = a.getAttribute('href').slice(1);
      history.replaceState(null, '', '#' + id);
      show(id, true);
    });
  });
  window.addEventListener('hashchange', function () { show(location.hash.slice(1), true); });
  show(location.hash.slice(1), !!location.hash);
})();

// 하위 메뉴(LNB): 지금 보고 있는 구역 표시
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.lnb a[href^="#"]'));
  if (!links.length || document.querySelector('.content[data-tabs]') || !('IntersectionObserver' in window)) return;
  var map = {};
  links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
  function activate(id) {
    links.forEach(function (a) { a.classList.remove('is-active'); a.removeAttribute('aria-current'); });
    if (map[id]) { map[id].classList.add('is-active'); map[id].setAttribute('aria-current', 'location'); }
  }
  activate(links[0].getAttribute('href').slice(1));
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) { if (en.isIntersecting) activate(en.target.id); });
  }, { rootMargin: '-30% 0px -60% 0px' });
  Object.keys(map).forEach(function (id) { var s = document.getElementById(id); if (s) io.observe(s); });
})();

// 소식 그리기
// - 업무관리 "홈페이지 게시" 결재를 거쳐 올라온 글: content/posts/index.json 과 content/posts/{게시ID}.json
// - 이전 홈페이지에서 옮긴 제목: assets/news.js 의 window.NEWS
(function () {
  var lists = document.querySelectorAll('[data-news]');
  var postBox = document.getElementById('post');
  if (!lists.length && !postBox) return;

  var KIND = { '공지': 'notice', '예산·결산 공고': 'notice', '활동 소식': 'activity', '언론 보도': 'press' };
  var ID_RE = /^[A-Za-z0-9_-]{1,80}$/;

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function isBudget(n) { return n.category === '예산·결산 공고' || /예산|결산|후원금품/.test(n.title); }
  function dot(d) { return String(d || '').replace(/-/g, '.'); }
  function icon(name) {
    var ns = 'http://www.w3.org/2000/svg';
    var s = document.createElementNS(ns, 'svg'); s.setAttribute('class', 'icon'); s.setAttribute('aria-hidden', 'true');
    var u = document.createElementNS(ns, 'use'); u.setAttribute('href', 'assets/icons.svg#i-' + name); s.appendChild(u);
    return s;
  }
  function pickThumb(t) {
    if (/김장|반찬|급식|도시락/.test(t)) return ['t2', 'meal'];
    if (/선물|후원|나눔/.test(t)) return ['t3', 'gift'];
    if (/나들이|산림|문화/.test(t)) return ['t1', 'leaf'];
    if (/교육|모임/.test(t)) return ['t4', 'people'];
    return ['t1', 'hands'];
  }
  // 게시 파일은 이 사이트의 content/uploads/ 안에 있는 것만 사용
  function upload(path) { path = String(path || ''); return /^content\/uploads\/[^?#]+$/.test(path) && path.indexOf('..') < 0 ? path : ''; }
  function safeLink(u) { return /^https?:\/\//i.test(u || '') ? u : ''; }
  function byDateDesc(a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; }
  function getJson(url) { return fetch(url, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }

  function loadLists() {
    var legacy = window.NEWS || {};
    var base = { notice: (legacy.notice || []).slice(), activity: (legacy.activity || []).slice(), press: (legacy.press || []).slice() };
    return getJson('content/posts/index.json').then(function (data) {
      (data.items || []).forEach(function (n) { var k = KIND[n.category]; if (k && ID_RE.test(n.id || '')) base[k].push(n); });
      Object.keys(base).forEach(function (k) { base[k].sort(byDateDesc); });
      return base;
    }).catch(function () { return base; });
  }

  function renderLists(lists) {
    document.querySelectorAll('[data-news]').forEach(function (ul) {
      var kind = ul.dataset.news;
      var items = (lists[kind] || []).slice(0, Number(ul.dataset.limit) || Infinity);
      var asCards = ul.dataset.view === 'cards';
      ul.textContent = '';
      if (!items.length) ul.appendChild(el('li', 'news-empty', '아직 올라온 글이 없습니다.'));
      items.forEach(function (n) {
        var li = el('li');
        var time = el('time', null, dot(n.date)); time.dateTime = n.date;
        var href = n.id ? 'post.html?id=' + encodeURIComponent(n.id) : '';
        if (asCards) {
          var card = el(href ? 'a' : 'div', 'card-news');
          if (href) card.href = href;
          var th, photo = upload(n.photo);
          if (photo) {
            th = el('div', 'thumb has-photo');
            var img = el('img'); img.src = photo; img.alt = ''; img.loading = 'lazy';
            th.appendChild(img);
          } else {
            var p = pickThumb(n.title);
            th = el('div', 'thumb ' + p[0]); th.appendChild(icon(p[1]));
          }
          var body = el('div', 'body'); body.appendChild(el('strong', null, n.title)); body.appendChild(time);
          card.appendChild(th); card.appendChild(body); li.appendChild(card);
        } else {
          var t = el(href ? 'a' : 'span', 't');
          if (href) t.href = href;
          if (kind === 'notice') t.appendChild(el('span', 'chip ' + (isBudget(n) ? 'budget' : 'notice'), isBudget(n) ? '공고' : '공지'));
          t.appendChild(document.createTextNode(n.title));
          li.appendChild(t); li.appendChild(time);
        }
        ul.appendChild(li);
      });
    });
  }

  function notFound() {
    postBox.textContent = '';
    postBox.appendChild(el('p', null, '글을 찾을 수 없습니다. 삭제되었거나 아직 게시되지 않은 글입니다.'));
    var back = el('a', 'btn btn-primary', '소식 목록으로'); back.href = 'news.html'; postBox.appendChild(back);
  }

  function renderPost(n) {
    postBox.textContent = '';
    document.title = n.title + ' | 서울시 강남구 재가노인복지기관';
    var head = el('header', 'post-head');
    head.appendChild(el('span', 'chip ' + (isBudget(n) ? 'budget' : 'notice'), n.category));
    head.appendChild(el('h2', null, n.title));
    var t = el('time', null, dot(n.date)); t.dateTime = n.date; head.appendChild(t);
    postBox.appendChild(head);

    if (n.place || n.partner) {
      var dl = el('dl', 'info-list post-info');
      [['일시', dot(n.date)], ['장소', n.place], ['함께한 곳', n.partner]].forEach(function (x) {
        if (x[1]) { dl.appendChild(el('dt', null, x[0])); dl.appendChild(el('dd', null, x[1])); }
      });
      postBox.appendChild(dl);
    }

    var body = el('div', 'post-body');
    String(n.body || '').split(/\n{2,}/).forEach(function (para) {
      var p = el('p');
      para.split('\n').forEach(function (line, i) { if (i) p.appendChild(el('br')); p.appendChild(document.createTextNode(line)); });
      body.appendChild(p);
    });
    postBox.appendChild(body);

    var link = safeLink(n.link);
    if (link) { var a = el('a', 'btn btn-light', '기사 원문 보기'); a.href = link; a.rel = 'noopener'; postBox.appendChild(a); }

    var photos = (n.photos || []).map(upload).filter(String);
    if (photos.length) {
      var g = el('div', 'post-photos');
      photos.forEach(function (src) { var img = el('img'); img.src = src; img.alt = n.title + ' 사진'; img.loading = 'lazy'; g.appendChild(img); });
      postBox.appendChild(g);
    }
    var files = (n.files || []).filter(function (f) { return upload(f.path); });
    if (files.length) {
      postBox.appendChild(el('h3', null, '첨부파일'));
      var ul = el('ul', 'post-files');
      files.forEach(function (f) {
        var li = el('li'); var a2 = el('a'); a2.href = upload(f.path); a2.setAttribute('download', f.name || '');
        a2.appendChild(icon('doc')); a2.appendChild(document.createTextNode(f.name || '첨부파일')); li.appendChild(a2); ul.appendChild(li);
      });
      postBox.appendChild(ul);
    }
    var back2 = el('a', 'btn btn-primary', '소식 목록으로'); back2.href = 'news.html'; back2.style.marginTop = '32px';
    postBox.appendChild(back2);
  }

  if (lists.length) loadLists().then(renderLists);
  if (postBox) {
    var id = new URLSearchParams(location.search).get('id') || '';
    if (!ID_RE.test(id)) notFound();
    else getJson('content/posts/' + id + '.json').then(renderPost).catch(notFound);
  }
})();

// 첫 화면 알림 팝업: content/popups.json 에서 게시 기간(start~end) 안의 항목만 보여줌
// - "오늘 하루 보지 않기"는 이 브라우저에만 날짜를 저장(개인정보 아님, 저장 실패해도 동작)
(function () {
  var dlg = document.querySelector('dialog[data-popup]');
  if (!dlg || typeof dlg.showModal !== 'function') return;
  var KEY = 'popupHide';
  var ID_RE = /^[A-Za-z0-9_-]{1,80}$/;
  function today() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  try { if (localStorage.getItem(KEY) === today()) return; } catch (e) {}

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function upload(path) { path = String(path || ''); return /^content\/uploads\/[^?#]+$/.test(path) && path.indexOf('..') < 0 ? path : ''; }
  // 링크는 이 사이트 안의 페이지 또는 https 주소만 허용
  function safeLink(u) { u = String(u || ''); return /^[A-Za-z0-9_-]+\.html([?#][A-Za-z0-9_=&#-]*)?$/.test(u) || /^https:\/\//i.test(u) ? u : ''; }

  fetch('content/popups.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (data) {
    var now = today();
    var items = (data.items || []).filter(function (p) {
      return ID_RE.test(p.id || '') && p.title && (!p.start || p.start <= now) && (!p.end || now <= p.end);
    }).slice(0, 5);
    if (!items.length) return;

    var idx = 0;
    var box = el('div', 'popup-body');
    var nav = el('div', 'popup-nav');
    var prev = el('button', 'popup-arrow', '이전'); prev.type = 'button';
    var count = el('span', 'popup-count'); count.setAttribute('aria-live', 'polite');
    var next = el('button', 'popup-arrow', '다음'); next.type = 'button';
    nav.appendChild(prev); nav.appendChild(count); nav.appendChild(next);
    var foot = el('div', 'popup-foot');
    var hide = el('button', 'popup-hide', '오늘 하루 보지 않기'); hide.type = 'button';
    var close = el('button', 'btn btn-primary popup-close', '닫기'); close.type = 'button';
    foot.appendChild(hide); foot.appendChild(close);

    function show(i) {
      idx = (i + items.length) % items.length;
      var p = items[idx];
      box.textContent = '';
      var img = upload(p.image);
      if (img) { var im = el('img', 'popup-img'); im.src = img; im.alt = p.alt || ''; box.appendChild(im); }
      var h = el('h2', null, p.title); h.id = 'popup-title'; box.appendChild(h);
      String(p.text || '').split(/\n{2,}/).forEach(function (para) {
        if (!para.trim()) return;
        var pe = el('p');
        para.split('\n').forEach(function (line, k) { if (k) pe.appendChild(el('br')); pe.appendChild(document.createTextNode(line)); });
        box.appendChild(pe);
      });
      var link = safeLink(p.link);
      if (link) { var a = el('a', 'btn btn-light', p.linkText || '자세히 보기'); a.href = link; if (/^https:/i.test(link)) a.rel = 'noopener'; box.appendChild(a); }
      count.textContent = (idx + 1) + ' / ' + items.length;
    }

    dlg.setAttribute('aria-labelledby', 'popup-title');
    dlg.appendChild(box);
    if (items.length > 1) dlg.appendChild(nav);
    dlg.appendChild(foot);
    prev.addEventListener('click', function () { show(idx - 1); });
    next.addEventListener('click', function () { show(idx + 1); });
    close.addEventListener('click', function () { dlg.close(); });
    hide.addEventListener('click', function () { try { localStorage.setItem(KEY, today()); } catch (e) {} dlg.close(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
    show(0);
    if (document.documentElement.classList.contains('locked')) return; // 준비 중 화면일 때는 띄우지 않음
    dlg.showModal();
    close.focus();
  }).catch(function () {});
})();
