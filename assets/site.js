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

// 하위 메뉴(LNB): 지금 보고 있는 구역 표시
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.lnb a[href^="#"]'));
  if (!links.length || !('IntersectionObserver' in window)) return;
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

// 소식 그리기 (assets/news.js 의 NEWS 데이터 사용)
(function () {
  if (!window.NEWS) return;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function isBudget(t) { return /예산|결산|후원금품/.test(t); }
  function pickThumb(t) {
    if (/김장|반찬|급식|도시락/.test(t)) return ['t2', 'meal'];
    if (/선물|후원|나눔/.test(t)) return ['t3', 'gift'];
    if (/나들이|산림|문화/.test(t)) return ['t1', 'leaf'];
    if (/교육|모임/.test(t)) return ['t4', 'people'];
    return ['t1', 'hands'];
  }
  function icon(name) {
    var ns = 'http://www.w3.org/2000/svg';
    var s = document.createElementNS(ns, 'svg'); s.setAttribute('class', 'icon'); s.setAttribute('aria-hidden', 'true');
    var u = document.createElementNS(ns, 'use'); u.setAttribute('href', 'assets/icons.svg#i-' + name); s.appendChild(u);
    return s;
  }

  document.querySelectorAll('[data-news]').forEach(function (ul) {
    var kind = ul.dataset.news;
    var items = (window.NEWS[kind] || []).slice(0, Number(ul.dataset.limit) || Infinity);
    var asCards = ul.dataset.view === 'cards';
    items.forEach(function (n) {
      var li = el('li');
      var time = el('time', null, n.date.replace(/-/g, '.')); time.dateTime = n.date;
      if (asCards) {
        var p = pickThumb(n.title);
        var card = el('div', 'card-news');
        var th = el('div', 'thumb ' + p[0]); th.appendChild(icon(p[1]));
        var body = el('div', 'body'); body.appendChild(el('strong', null, n.title)); body.appendChild(time);
        card.appendChild(th); card.appendChild(body); li.appendChild(card);
      } else {
        var t = el('span', 't');
        if (kind === 'notice') t.appendChild(el('span', 'chip ' + (isBudget(n.title) ? 'budget' : 'notice'), isBudget(n.title) ? '공고' : '공지'));
        t.appendChild(document.createTextNode(n.title));
        li.appendChild(t); li.appendChild(time);
      }
      ul.appendChild(li);
    });
  });
})();
