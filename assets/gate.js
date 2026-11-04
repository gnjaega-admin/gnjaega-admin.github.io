// 준비 중 화면: 공개 전까지 일반 방문자에게는 '준비 중' 화면만 보여줌
// - 미리보기 주소(?preview=비밀값)로 한 번 들어오면 이 브라우저에서는 실제 화면을 보여줌
// - 비밀값 자체는 여기 없고, 맞는지 확인하는 지문(SHA-256)만 있음
// - ?preview=off 로 들어오면 미리보기를 끔
(function () {
  var KEY = 'previewOk';
  var HASH = 'd1170035b32a1ddfcbfa63e41228ec674bb204770941e4b32b036eeed6cdb5b2';
  var root = document.documentElement;
  var q = new URLSearchParams(location.search).get('preview');
  var ok = false;
  try {
    if (q === 'off') localStorage.removeItem(KEY);
    ok = localStorage.getItem(KEY) === HASH;
  } catch (e) {}
  if (!ok) root.classList.add('locked');

  function cleanUrl() { history.replaceState(null, '', location.pathname + location.hash); }
  if (q === 'off') { cleanUrl(); return; }
  if (!q || ok || !(window.crypto && crypto.subtle)) return;
  crypto.subtle.digest('SHA-256', new TextEncoder().encode(q)).then(function (buf) {
    var hex = Array.prototype.map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
    if (hex !== HASH) return;
    try { localStorage.setItem(KEY, HASH); } catch (e) {}
    root.classList.remove('locked');
    cleanUrl();
  });
})();
