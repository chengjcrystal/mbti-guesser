"""
ui.py: mbti radar
Gradio handles all layout. CSS only touches colors, fonts, and custom HTML blocks.
The result card (slice the pack, flip, wide view, export) is client-side js in
HEAD_JS; every value inside the card is rendered server-side from the real
prediction, and the characters are drawn by sprites.js.
"""

import html
import json
import os
import pathlib
import random
import re
import gradio as gr
import finishes as F
import pack_art
import foil_art
import game as G
from app import predict_mbti
from questions import BY_ID, NO_SOCIAL, NOT_SURE, QUESTIONS, STEP_TITLES, STEPS, answer_ids, chip_ids, is_shown, required_ids, step_questions

# beta testing shortcut: start the app with  MBTI_DEV=1 python3 ui.py  and a small bar shows up
# above the quiz that jumps straight to the result page. it isn't there unless that env var is set,
# so the public space never shows it
DEV = os.environ.get("MBTI_DEV", "").strip() == "1"

CSS = (pathlib.Path(__file__).parent / "styles.css").read_text()

# gradio 6.18 styles every button with .gradio-container-x button (three-ish classes deep), which
# beats a plain .start-btn. repeating the class on a button selector wins on any gradio version
_BTN_CLASSES = "radar-toggle|start-btn|rules-block|rules-close|rv-tool"
CSS = re.sub(rf"(?<![\w-])\.({_BTN_CLASSES})(?![\w-])", r"button.\1.\1.\1.\1", CSS)
# follow-up questions are shown by flags on the quiz wrapper (set by the head script), not by the server:
CSS += f"\n:root {{ --sparkle: {foil_art.sparkle_tile_css(1)}; --sparkle-faint: {foil_art.sparkle_tile_css(0.4)}; }}\n"
# a chip reveals its questions, and "no social media" hides the follower and story ones
CSS += "\n.cond-col { display: none !important; }\n"
for _q in QUESTIONS:
    if _q.get("show_if"):
        for _c in ([_q["show_if"]] if isinstance(_q["show_if"], str) else _q["show_if"]):
            CSS += f".console.chip-{_c} .cond-col.cc-{_c} {{ display: flex !important; }}\n"
# the quiz steps are all in the page; the flag on .console (set from the step indicator, see the
# head script) says which one shows. no flag yet means step 1.
CSS += "\n.step-col { display: none !important; }\n.console:not([class*=\"on-step-\"]) .step-col.step-1 { display: flex !important; }\n"
for _s in STEPS:
    CSS += f".console.on-step-{_s} .step-col.step-{_s} {{ display: flex !important; }}\n"
CSS += """
#f-spam_friends_count { display: none !important; }
.console.has-spam #f-spam_friends_count { display: block !important; }
.console.no-social #f-followers, .console.no-social #f-story_frequency,
.console.no-social #f-social_media_checkboxes, .console.no-social #f-spam_friends_count { display: none !important; }
"""
SPRITES_JS = (pathlib.Path(__file__).parent / "sprites.js").read_text()

# fonts load from the head, since an @import inside gradio's injected stylesheet is ignored by the browser
FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Silkscreen:wght@400;700&family=Rubik:wght@400;500;600&display=swap">'
)

HEAD_JS = FONT_LINKS + "<script>\n" + SPRITES_JS + "\n</script>\n" + """
<script>
// ── the result card ──────────────────────────────────────────────────────────
// slice the pack open, tap the card to flip it, swap to the wide layout, or
// export the wide card as a png. all of it works off the #rv wrapper.
function mbtiRv() { return document.getElementById('rv'); }

// drag along the dashed line to cut the pack. a plain tap works too.
function mbtiSliceStart(e) {
  var z = e.currentTarget;
  z.setPointerCapture(e.pointerId);
  z._x0 = e.clientX; z._moved = false; z._max = 0;
}
function mbtiSliceMove(e) {
  var z = e.currentTarget;
  if (z._x0 == null) return;
  var r = z.getBoundingClientRect();
  var p = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
  if (Math.abs(e.clientX - z._x0) > 6) z._moved = true;
  z._max = Math.max(z._max, p);
  z.style.setProperty('--cut', (z._max * 100) + '%');
  if (z._max >= 0.9) { z._x0 = null; mbtiSlice(); }
}
function mbtiSliceEnd(e) {
  var z = e.currentTarget;
  if (z._x0 == null) return;
  var moved = z._moved;
  z._x0 = null;
  if (!moved) mbtiSlice();
  else z.style.setProperty('--cut', '0%');   // let go halfway and the blade slides back
}
function mbtiSlice() {
  var w = mbtiRv();
  if (!w || w.classList.contains('slicing')) return;
  w.classList.add('slicing');
  setTimeout(function () { w.classList.add('sliced'); mbtiFit(); setTimeout(mbtiFit, 650); }, 520);
}
function mbtiFlip() {
  var f = document.getElementById('flip1');
  if (f) f.classList.toggle('flipped');
}
function mbtiLayout() {
  var w = mbtiRv();
  if (!w) return;
  var wide = w.getAttribute('data-layout') !== 'wide';
  w.setAttribute('data-layout', wide ? 'wide' : 'card');
  if (wide) mbtiWho();
  mbtiFit();
  var b = document.getElementById('layoutBtn');
  if (b) b.textContent = wide ? 'card view' : 'wide view';
}
function mbtiTypes(open) {   // the gallery of all 16 types, in place of the pack / card
  var w = mbtiRv();
  if (!w) return;
  if (open && !w.classList.contains('sliced')) return;   // your own type first
  if (open) w.setAttribute('data-view', 'all'); else w.removeAttribute('data-view');
  mbtiFit();
  w.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (open) {
    var mine = w.querySelector('.tcard.mine');
    if (mine) setTimeout(function () { mine.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 350);
  }
}
// sizes the card so the card, the buttons under it and the retake button all fit on
// one screen. it only ever shrinks (a tall window keeps the full size), and not below 55%.
function mbtiHeroSync() {
  // the title banner steps aside (on a short screen, see the css) while the card is showing
  var w = mbtiRv(), h = document.querySelector('.mbti-hero');
  if (h) h.classList.toggle('stepped-aside', !!w && w.classList.contains('sliced') && w.getAttribute('data-layout') !== 'wide' && w.getAttribute('data-view') !== 'all');
}
function mbtiFit() {
  mbtiHeroSync();
  var w = mbtiRv();
  var f = document.getElementById('flip1');
  if (!w || !f) return;
  f.style.transform = ''; f.style.marginBottom = '';
  if (window.innerWidth < 700) return;   // on a phone the page just scrolls, a shrunken card would be too small to read
  if (!w.classList.contains('sliced') || w.getAttribute('data-layout') === 'wide' || w.getAttribute('data-view') === 'all') return;
  var again = document.querySelector('.again-row');
  var panel = document.getElementById('exportPanel');
  var fr = f.getBoundingClientRect();
  var top = fr.top + window.scrollY;
  var end = (again ? again.getBoundingClientRect().bottom : fr.bottom) + window.scrollY;
  var below = end - (fr.bottom + window.scrollY) - (panel && panel.classList.contains('open') ? panel.offsetHeight + 14 : 0);
  var s = Math.max(0.55, Math.min(1, (window.innerHeight - top - below - 20) / fr.height));
  if (s < 1) {
    // scale from the top centre and pull the space it no longer takes back up
    f.style.transformOrigin = 'top center';
    f.style.transform = 'scale(' + s + ')';
    f.style.marginBottom = (-(fr.height * (1 - s))) + 'px';
  }
}
(function () {
  var t = null;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(mbtiFit, 120); });
})();
// tilt: the card leans toward the pointer and the shine slides with it, so a foil card
// can be turned to catch the light. this only sets a few css variables on .rv, the css does the rest
(function () {
  var MAX = 13;   // degrees of lean at the very edge of the card
  var calm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var VARS = ['--rx', '--ry', '--ra', '--shine', '--sx'];
  var pending = null, queued = false;
  function clamp(v) { return Math.max(0, Math.min(1, v)); }
  function rest() {
    var rv = document.getElementById('rv');
    if (rv) VARS.forEach(function (k) { rv.style.removeProperty(k); });
  }
  function paint() {
    queued = false;
    var rv = document.getElementById('rv');
    if (!rv || !pending) return;
    var dx = (pending.x - 0.5) * 2, dy = (pending.y - 0.5) * 2, m = Math.sqrt(dx * dx + dy * dy);
    rv.style.setProperty('--rx', m ? (-dy / m).toFixed(3) : '0');
    rv.style.setProperty('--ry', m ? (dx / m).toFixed(3) : '1');
    rv.style.setProperty('--ra', (Math.min(m, 1) * MAX).toFixed(2) + 'deg');
    rv.style.setProperty('--shine', (75 - 50 * pending.x).toFixed(1));   // 50 is where the shine sits at rest
    rv.style.setProperty('--sx', ((pending.x - 0.5) * 64).toFixed(1));   // one band period is 64px
  }
  document.addEventListener('pointermove', function (e) {
    if (calm) return;
    var rv = document.getElementById('rv');
    if (!rv || !rv.classList.contains('sliced')) return;
    var card = e.target.closest ? e.target.closest('.flip, .wide-card') : null;
    if (!card) { pending = null; rest(); return; }
    var r = card.getBoundingClientRect();
    pending = { x: clamp((e.clientX - r.left) / r.width), y: clamp((e.clientY - r.top) / r.height) };
    if (!queued) { queued = true; requestAnimationFrame(paint); }
  });
  // a finger lifting, or the mouse leaving the window, lets the card settle back
  ['pointerup', 'pointercancel'].forEach(function (t) {
    document.addEventListener(t, function (e) { if (e.pointerType !== 'mouse') { pending = null; rest(); } });
  });
  document.documentElement.addEventListener('mouseleave', function () { pending = null; rest(); });
})();

// the mystery cards on the landing page show a different dark silhouette on every visit, so no single mascot
// becomes "the" mascot. picked here in the browser, redrawn with the same sprite code the cards use
(function () {
  var CODES = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP','ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'];
  var pick = CODES[Math.floor(Math.random() * CODES.length)];
  function paint() {
    if (!window.mbtiSprites || !window.mbtiSprites[pick]) return;
    document.querySelectorAll('.landing canvas[data-landing]:not([data-picked])').forEach(function (cv) {
      cv.setAttribute('data-sprite', pick);
      cv.setAttribute('data-drawn', '1');
      window.mbtiSprites[pick]().render(cv, 7);
      cv.setAttribute('data-picked', '1');
    });
  }
  new MutationObserver(paint).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', paint);
})();

// the landing page button: reveal the quiz. it's only a class on the body, css does the rest
function mbtiStart() {
  document.body.classList.add('started');
  window.scrollTo({ top: 0 });
}

function mbtiPack() {   // back to a sealed pack
  var w = mbtiRv();
  if (!w) return;
  w.classList.remove('slicing', 'sliced');
  var f = document.getElementById('flip1');
  if (f) f.classList.remove('flipped');
  var z = document.getElementById('sliceZone');
  if (z) z.style.setProperty('--cut', '0%');
}

function mbtiWrapText(c, text, x, y, maxW, lh) {
  var words = text.split(' '), line = '';
  for (var i = 0; i < words.length; i++) {
    var t = line + words[i] + ' ';
    if (c.measureText(t).width > maxW && line) { c.fillText(line, x, y); line = words[i] + ' '; y += lh; }
    else line = t;
  }
  c.fillText(line, x, y);
  return y + lh;
}

// the name box under the tools row. the name and today's date are printed on the
// wide card and on the exported png, all in the browser, nothing gets sent anywhere.
function mbtiToday() {
  return new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function mbtiWhoLine() {
  var i = document.getElementById('exportName');
  var name = i ? i.value.trim() : '';
  return (name ? name + ' · ' : '') + mbtiToday();
}
function mbtiWho() {
  var line = mbtiWhoLine().toUpperCase();
  document.querySelectorAll('.wide-who').forEach(function (el) { el.textContent = line; });
  try { localStorage.setItem('mbtiRadarName', (document.getElementById('exportName') || {}).value || ''); } catch (e) {}
}
function mbtiExportPanel() {
  var p = document.getElementById('exportPanel');
  if (!p) return;
  var open = !p.classList.contains('open');
  p.classList.toggle('open', open);
  if (open) mbtiShareInit();
  var i = document.getElementById('exportName');
  if (open && i) {
    try { if (!i.value) i.value = localStorage.getItem('mbtiRadarName') || ''; } catch (e) {}
    mbtiWho();
    setTimeout(function () { i.focus(); p.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 60);
  }
}

// draws the wide card onto a canvas by hand and downloads it. this is the
// shareable version, so it has everything on it: character, radar, stats.
function mbtiRenderCard(done) {
  var w = mbtiRv();
  if (!w) return;
  var d = JSON.parse(w.getAttribute('data-card'));
  var PLUM = '#4A3B5C', CREAM = '#EDE6D3', SOFT = '#6B5D7D';
  var draw = function () {
    var W = 1600, H = 1310, M = 40, DY = 22, DK = '#2b2140';
    var cv = document.createElement('canvas'); cv.width = W + 2 * M; cv.height = H + DY + 2 * M;
    var c = cv.getContext('2d');
    c.imageSmoothingEnabled = false;
    var rr = function (x, y, w, h, r) {
      c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
      c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
    };
    var foil = function (x, y, w, h) {
      var g = c.createLinearGradient(x, y, x + w, y + h);
      [[0, '#F3DC8E'], [0.35, '#C9A24F'], [0.55, '#F6E5A6'], [0.8, '#B98F3E'], [1, '#EBCF7B']].forEach(function (k) { g.addColorStop(k[0], k[1]); });
      return g;
    };
    // the sheen over the art window, the same diagonal streak as on the card
    var sheen = function (x, y, S) {
      var cx0 = x + S / 2, cy0 = y + S / 2, dx = 0.906 * S * 0.664, dy = 0.423 * S * 0.664;
      var g = c.createLinearGradient(cx0 - dx, cy0 - dy, cx0 + dx, cy0 + dy);
      g.addColorStop(0.08, 'rgba(255,255,255,0)'); g.addColorStop(0.14, 'rgba(255,170,210,.34)');
      g.addColorStop(0.26, 'rgba(255,255,255,.62)'); g.addColorStop(0.34, 'rgba(255,255,255,.62)');
      g.addColorStop(0.3401, 'rgba(140,230,255,.38)'); g.addColorStop(0.44, 'rgba(140,230,255,.38)');
      g.addColorStop(0.4401, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      c.fillStyle = g; c.fillRect(x, y, S, S);
    };
    // the finish decides the look: common is the family color only, holo adds the gold rim and one
    // still shine, rainbow has a still rainbow rim and rainbow foil bands over the character
    var fin = d.finish || 'common';
    var RB = ['#E86A6A', '#F0A35E', '#F3D66B', '#8FCB7A', '#6FA8DC', '#A98BD9'];
    var rainbowFill = function (x, y, w, h) {
      var g = c.createLinearGradient(x, y, x + w, y + h), n = 6 * Math.max(2, Math.round((w + h) / 190));
      for (var k = 0; k < n; k++) { var col = RB[k % 6]; g.addColorStop(k / n, col); g.addColorStop((k + 1) / n - 0.0001, col); }
      return g;
    };
    // the fill for a rim: gold on holo, rainbow on rainbow, the family color on a common card
    var rimFill = function (x, y, w, h) {
      return fin === 'holo' ? foil(x, y, w, h) : fin === 'rainbow' ? rainbowFill(x, y, w, h) : d.familyColor;
    };
    // the rainbow foil over the character: hard diagonal bands, drawn still in the saved image
    var rainbowBands = function (x, y, S) {
      c.save(); c.beginPath(); c.rect(x, y, S, S); c.clip();
      var w = 31, T = S * 2;
      for (var a = -S, k = 0; a < S * 2; a += w, k++) {
        c.fillStyle = 'rgba(' + [[238,143,143],[243,185,132],[245,225,146],[172,217,155],[147,190,230],[193,170,226]][k % 6].join(',') + ',.32)';
        c.beginPath(); c.moveTo(x + a - T, y + T); c.lineTo(x + a + w - T, y + T); c.lineTo(x + a + w + T, y - T); c.lineTo(x + a + T, y - T); c.closePath(); c.fill();
      }
      c.restore();
    };
    // a double rim around a window
    var rim = function (x, y, S) {
      rr(x - 14, y - 14, S + 28, S + 28, 8); c.fillStyle = rimFill(x - 14, y - 14, S + 28, S + 28); c.fill();
      c.strokeStyle = DK; c.lineWidth = 4; c.stroke();
    };
    // the card: an outer rim on holo and rainbow, a band in the family color, then the cream face
    if (fin === 'common') {
      rr(3, 3, cv.width - 6, cv.height - 6, 43); c.fillStyle = d.familyColor; c.fill();
    } else {
      rr(0, 0, cv.width, cv.height, 46); c.fillStyle = rimFill(0, 0, cv.width, cv.height); c.fill();
      rr(14, 14, cv.width - 28, cv.height - 28, 36); c.fillStyle = d.familyColor; c.fill();
    }
    c.strokeStyle = DK; c.lineWidth = 6; c.stroke();
    c.strokeStyle = DK; c.lineWidth = 6;
    rr(38, 38, cv.width - 76, cv.height - 76, 20);
    var face = c.createLinearGradient(0, 38, 0, cv.height - 38); face.addColorStop(0, '#F6EFDC'); face.addColorStop(1, CREAM);
    c.fillStyle = face; c.fill(); c.stroke();
    c.translate(M, M);

    // header: family tag on the left, dex number on the right
    c.textBaseline = 'middle'; c.font = '700 26px Silkscreen, monospace';
    var tagW = c.measureText(d.family.toUpperCase()).width + 36;
    rr(48, 43, tagW, 44, 6); c.fillStyle = d.familyColor; c.fill(); c.strokeStyle = DK; c.lineWidth = 4; c.stroke();
    c.fillStyle = DK; c.fillText(d.family.toUpperCase(), 66, 66);
    if (fin !== 'common') {   // the finish tag next to the family pill
      var ft = (d.finishLabel || fin).toUpperCase(), fw = c.measureText(ft).width + 32, fx = 48 + tagW + 16;
      rr(fx, 43, fw, 44, 6); c.fillStyle = fin === 'holo' ? '#F3DC8E' : rainbowFill(fx, 43, fw, 44); c.fill(); c.strokeStyle = DK; c.lineWidth = 4; c.stroke();
      c.fillStyle = DK; c.fillText(ft, fx + 16, 66);
    }
    c.fillStyle = SOFT; c.textAlign = 'right'; c.fillText('NO. ' + String(d.dex).padStart(2, '0') + ' / 16', W - 48, 66); c.textAlign = 'left';

    // left pane: the character on a little scene
    var px = 48, py = 118, S = 720;
    rim(px, py, S);
    var g = c.createLinearGradient(0, py, 0, py + S);
    g.addColorStop(0, '#BFE3E6'); g.addColorStop(0.62, '#BFE3E6'); g.addColorStop(0.62, '#A5BE7E'); g.addColorStop(1, '#A5BE7E');
    c.fillStyle = g; c.fillRect(px, py, S, S);
    var sp = document.createElement('canvas');
    window.mbtiSprites[d.code]().render(sp, 20);   // the grid is 36 wide, so 20x fills the pane
    c.drawImage(sp, px, py, S, S);
    if (fin === 'holo') sheen(px, py, S);
    if (fin === 'rainbow') rainbowBands(px, py, S);
    c.strokeStyle = DK; c.lineWidth = 8; c.strokeRect(px, py, S, S);

    // right pane: the radar
    var rx = 832, ry = 118;
    rim(rx, ry, S);
    c.fillStyle = '#ffffff'; c.fillRect(rx, ry, S, S);
    c.strokeStyle = DK; c.lineWidth = 8; c.strokeRect(rx, ry, S, S);
    if (fin === 'holo') { c.save(); c.globalAlpha = 0.7; sheen(rx, ry, S); c.restore(); }
    var cx = rx + S / 2, cy = ry + S / 2 + 10, R = 268, n = d.stats.length;
    var pt = function (i, r) { var a = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
    c.lineWidth = 2; c.strokeStyle = '#D9CFC0';
    [1, 0.66, 0.33].forEach(function (k) {
      c.beginPath(); for (var i = 0; i < n; i++) { var p = pt(i, R * k); i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]); } c.closePath(); c.stroke();
    });
    for (var i = 0; i < n; i++) { var e = pt(i, R); c.beginPath(); c.moveTo(cx, cy); c.lineTo(e[0], e[1]); c.stroke(); }
    var tracePoly = function () {
      c.beginPath();
      d.stats.forEach(function (s, i) { var p = pt(i, R * s.radar / 100); i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]); });
      c.closePath();
    };
    tracePoly();
    if (fin === 'rainbow') {   // the shape fills with bold rainbow stripes leaning the same way as the foil
      c.save(); c.clip();
      var bw = 34, big = R * 3;
      for (var a2 = -big, k2 = 0; a2 < big; a2 += bw, k2++) {
        c.fillStyle = RB[k2 % 6];
        c.beginPath(); c.moveTo(cx + a2 - big, cy + big); c.lineTo(cx + a2 + bw - big, cy + big); c.lineTo(cx + a2 + bw + big, cy - big); c.lineTo(cx + a2 + big, cy - big); c.closePath(); c.fill();
      }
      c.restore();
    } else {
      c.fillStyle = fin === 'holo' ? 'rgba(201,162,79,.30)' : 'rgba(74,59,92,.18)'; c.fill();
    }
    tracePoly(); c.strokeStyle = PLUM; c.lineWidth = 6; c.stroke();
    d.stats.forEach(function (s, i) {
      var p = pt(i, R * s.radar / 100);
      c.beginPath(); c.arc(p[0], p[1], 13, 0, 7); c.fillStyle = s.color; c.fill(); c.lineWidth = 4; c.stroke();
      // labels sit just above or below their own corner so the radar can fill the pane
      var l = pt(i, R);
      c.font = '700 22px Silkscreen, monospace'; c.fillStyle = SOFT; c.textAlign = 'center';
      c.fillText(s.name.toUpperCase(), l[0], l[1] + ((i === 0 || i === 1 || i === 4) ? -24 : 34));
    });
    c.textAlign = 'left';

    // everything below the windows sits a little lower to clear the gold rims
    c.translate(0, DY);

    // under the character: the name, then the flavor line on a gold strip
    c.fillStyle = PLUM; c.font = '46px "Press Start 2P", monospace'; c.fillText(d.code + '-' + d.suffix, 48, 880);
    c.fillStyle = SOFT; c.font = '700 28px Silkscreen, monospace'; c.fillText(d.title.toUpperCase(), 48, 944);
    var sg = c.createLinearGradient(48, 0, 768, 0); sg.addColorStop(0, '#F3DC8E'); sg.addColorStop(0.5, '#F9EDBE'); sg.addColorStop(1, '#F3DC8E');
    rr(48, 972, 720, 50, 6); c.fillStyle = fin === 'common' || fin === 'rainbow' ? '#FFFDF9' : sg; c.fill();
    if (fin === 'rainbow') { c.save(); rr(48, 972, 720, 50, 6); c.clip(); rainbowBands(48, 972, 720); c.globalAlpha = 0.4; sparkles(48, 972, 720); c.restore(); }
    rr(48, 972, 720, 50, 6); c.strokeStyle = DK; c.lineWidth = 4; c.stroke();
    c.fillStyle = '#362B47'; c.font = 'italic 25px Rubik, sans-serif'; c.textAlign = 'center';
    // pixel sparkles (pluses and dots) tiled over a window, the same tile the page uses on the back of a rainbow card
    var sparkles = function (x, y, S) {
      c.save(); c.beginPath(); c.rect(x, y, S, S); c.clip();
      var T = 182, u = T / 84;
      var plus = function (ox, oy, arm, col) { c.fillStyle = col; c.fillRect(ox - arm * u, oy - u, arm * 2 * u, 2 * u); c.fillRect(ox - u, oy - arm * u, 2 * u, arm * 2 * u); };
      for (var tx = 0; tx < S; tx += T) for (var ty = 0; ty < S; ty += T) {
        var ox = x + tx, oy = y + ty;
        plus(ox + 12 * u, oy + 14 * u, 4, '#FFFFFF');
        plus(ox + 64 * u, oy + 52 * u, 3, RB[4]);
        plus(ox + 22 * u, oy + 62 * u, 2, RB[5]);
        c.fillStyle = RB[2]; c.fillRect(ox + 40 * u, oy + 36 * u, 3 * u, 3 * u);
        plus(ox + 72 * u, oy + 26 * u, 2, '#FFFFFF');
      }
      c.restore();
    };
    c.fillText(d.blurb, 408, 997); c.textAlign = 'left';
    c.fillStyle = '#362B47'; c.font = '500 25px Rubik, sans-serif';
    var y = mbtiWrapText(c, d.desc, 48, 1070, 700, 36);
    c.fillStyle = SOFT; c.font = 'italic 21px Rubik, sans-serif';
    mbtiWrapText(c, d.suffix + '-identity: ' + d.identity, 48, y + 8, 700, 30);

    // under the radar: the five stats
    d.stats.forEach(function (s, i) {
      var yy = 872 + i * 50;
      c.fillStyle = SOFT; c.font = '700 21px Silkscreen, monospace';
      var label = (s.name + ' (' + s.letter + ')').toUpperCase();
      c.fillText(label, 832, yy);
      if (s.soft) { c.fillStyle = '#8C6E8C'; c.font = '700 13px Silkscreen, monospace'; c.fillText('CLOSE CALL', 832 + c.measureText(label).width + 10, yy + 22); c.font = '700 21px Silkscreen, monospace'; }
      c.fillStyle = '#ffffff'; c.fillRect(1120, yy - 12, 340, 24);
      c.fillStyle = s.color; c.fillRect(1120, yy - 12, 340 * s.pct / 100, 24);
      c.strokeStyle = PLUM; c.lineWidth = 3; c.strokeRect(1120, yy - 12, 340, 24);
      c.fillStyle = PLUM; c.font = '700 24px Silkscreen, monospace'; c.textAlign = 'right';
      c.fillText(String(s.pct), 1552, yy); c.textAlign = 'left';
    });

    // footer: whose card it is and when, then the brand
    c.fillStyle = 'rgba(74,59,92,.35)'; c.fillRect(48, H - 98, W - 96, 3);
    c.fillStyle = PLUM; c.font = '700 26px Silkscreen, monospace'; c.textAlign = 'left';
    c.fillText(mbtiWhoLine().toUpperCase(), 48, H - 48);
    c.fillStyle = 'rgba(74,59,92,.55)'; c.font = '16px "Press Start 2P", monospace'; c.textAlign = 'right';
    c.fillText('MBTI RADAR', W - 48, H - 48); c.textAlign = 'left';

    cv.toBlob(function (blob) { done(blob, d); });
  };
  // the canvas can only use the pixel fonts once they have actually loaded
  Promise.all([
    document.fonts.load('46px "Press Start 2P"'),
    document.fonts.load('700 26px Silkscreen'),
    document.fonts.load('500 25px Rubik'),
  ]).then(draw, draw);
}

function mbtiFileName(d) { return 'mbti-radar-' + d.code + '-' + d.suffix + '.png'; }
function mbtiNote(msg) {
  var n = document.getElementById('exportNote');
  if (!n) return;
  if (!n._orig) n._orig = n.textContent;
  n.textContent = msg;
  clearTimeout(n._t);
  n._t = setTimeout(function () { n.textContent = n._orig; }, 3200);
}
// save the png to the device
function mbtiExport() {
    if (fin === 'rainbow') { rainbowBands(rx, ry, S); sparkles(rx, ry, S); }
  mbtiRenderCard(function (blob, d) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = mbtiFileName(d);
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
    mbtiNote('saved to your downloads');
  });
}
// the phone's own share sheet, with the card attached as an image
function mbtiShare() {
  mbtiRenderCard(function (blob, d) {
    var file = new File([blob], mbtiFileName(d), { type: 'image/png' });
    var data = { files: [file], title: 'MBTI Radar',
      text: 'i got ' + d.code + '-' + d.suffix + ', ' + d.title + ', on MBTI Radar. try it: https://huggingface.co/spaces/chengjcrystal/mbti-radar' };
    if (navigator.canShare && navigator.canShare(data)) {
      navigator.share(data).catch(function () {});
    } else {
      mbtiExport();
    }
  });
}
// the card as an image on the clipboard, ready to paste into a chat
function mbtiCopy() {
  mbtiRenderCard(function (blob) {
    try {
      navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]).then(
        function () { mbtiNote('copied, paste it anywhere'); },
        function () { mbtiNote('could not copy, try save image instead'); });
    } catch (e) { mbtiNote('could not copy, try save image instead'); }
  });
}
// only offer the share sheet and copy where the browser can do them
function mbtiShareInit() {
  var canShare = !!(navigator.canShare && navigator.share);
  var canCopy = !!(navigator.clipboard && window.ClipboardItem);
  var s = document.getElementById('nativeShareBtn'), c = document.getElementById('copyBtn');
  if (s) s.style.display = canShare ? '' : 'none';
  if (c) c.style.display = canCopy ? '' : 'none';
}

// hide the live radar: kept in this browser, so it stays put between visits
var mbtiHR = false;
function mbtiRadarHidden() {
  try { return localStorage.getItem('mbtiHideRadar') === '1'; } catch (e) { return mbtiHR; }
}
function mbtiRadarApply() {
  var on = mbtiRadarHidden();
  var c = document.querySelector('.console');
  if (c) c.classList.toggle('radar-hidden', on);
  document.querySelectorAll('.radar-toggle').forEach(function (b) { b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
}
function mbtiRadar() {
  mbtiHR = !mbtiRadarHidden();
  try { localStorage.setItem('mbtiHideRadar', mbtiHR ? '1' : '0'); } catch (e) {}
  mbtiRadarApply();
}
</script>
<script>

function mbtiRules(force) {
  var p = document.getElementById('rules-panel');
  var b = document.getElementById('rules-block');
  if (!p) return;
  var open = (typeof force === 'boolean') ? force : !p.classList.contains('open');
  p.classList.toggle('open', open);
  if (b) {
    b.classList.toggle('active', open);
    b.setAttribute('aria-expanded', open ? 'true' : 'false');
    b.classList.remove('hit'); void b.offsetWidth; b.classList.add('hit');
  }
}
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') mbtiRules(false);
});

// a blocked Next click renders a fresh "still needed" callout; bring it into
// view since it can land below the fold on a long card. live updates while
// fixing answers re-render it without data-fresh, so they never re-scroll.
(function () {
  new MutationObserver(function (muts) {
    muts.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        var c = n.matches('.need-callout[data-fresh]') ? n : n.querySelector('.need-callout[data-fresh]');
        if (c) c.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();

// follow-up questions show and hide right here in the page. asking the server
// to toggle them re-mounted the whole radio and its neighbours on every click,
// which is what made them flicker. this only sets flags on the quiz wrapper, and css does the rest.
(function () {
  var NO_SOCIAL = ["doesn't use social media", "not sure"];
  function flag(name, on) {
    var root = document.querySelector('.console');
    if (root) root.classList.toggle(name, on);   // toggle is a no-op when it is already right
  }
  function sync() {
    highlight();
    if (window.mbtiRadarApply) mbtiRadarApply();
    if (window.mbtiHeroSync) mbtiHeroSync();
    var r = document.querySelector('#f-posting_frequency input[type=radio]:checked');
    var label = r ? (r.closest('label') ? r.closest('label').innerText.trim() : r.value) : '';
    flag('no-social', NO_SOCIAL.indexOf(label) >= 0);
    flag('has-spam', !!document.querySelector('#f-social_media_checkboxes input[type=checkbox]:checked'));
    // the "quiet chat" question waits until the group chat part is settled
    var picked = function (id) { var i = document.querySelector('#f-' + id + ' input[type=checkbox]'); return !!(i && i.checked); };
    var typed = function (sel) { var e = document.querySelector(sel); return !!(e && e.value.trim()); };
    flag('chat-done', picked('chat_choice_read')
      || (picked('chat_choice_reply') && typed('#f-chat_reply textarea'))
      || (picked('chat_choice_ask') && typed('#f-chat_final textarea')));
    // the texts slider starts at 0 (no answer), with no thumb showing, until it has been moved
    var sl = document.querySelector('#f-text_length_slider');
    if (sl) sl.classList.toggle('unset', (sl.querySelector('input[type=range]') || {}).value === '0');
    // the chips act like a radio, but the server only unticks the old one after a round trip.
    // going by the one clicked last keeps the wrong panel from flashing open in between.
    document.querySelectorAll('.chip-row').forEach(function (row) {
      var on = Array.prototype.filter.call(row.querySelectorAll('.read-chip'), function (c) {
        var i = c.querySelector('input[type=checkbox]'); return i && i.checked;
      });
      var win = on.length > 1 ? (on.filter(function (c) { return c.id === row._last; })[0] || on[0]) : on[0];
      row.querySelectorAll('.read-chip').forEach(function (c) { flag('chip-' + c.id.replace(/^f-/, ''), c === win); });
    });
  }
  // the fields the "still needed" callout links to get the pink highlight
  function highlight() {
    var want = {};
    document.querySelectorAll('.need-callout a[href^="#f-"]').forEach(function (a) { want[a.getAttribute('href').slice(1)] = 1; });
    document.querySelectorAll('.needs-answer').forEach(function (el) { if (!want[el.id]) el.classList.remove('needs-answer'); });
    Object.keys(want).forEach(function (id) {
      var el = document.getElementById(id);
      if (el && !el.classList.contains('needs-answer')) el.classList.add('needs-answer');
    });
  }
  document.addEventListener('change', sync, true);
  document.addEventListener('input', sync, true);
  document.addEventListener('click', function (e) {
    var chip = e.target.closest && e.target.closest('.read-chip');
    if (chip && chip.closest('.chip-row')) chip.closest('.chip-row')._last = chip.id;
    setTimeout(sync, 0);
  }, true);
  new MutationObserver(highlight).observe(document.body, { childList: true, subtree: true });
  // which quiz step shows comes from the "STEP n OF 6" indicator the server updates
  var lastStep = null;
  function syncStep() {
    var ind = document.querySelector('.step-indicator span');
    var m = ind && /STEP\\s+(\\d+)/i.exec(ind.textContent);
    var root = document.querySelector('.console');
    if (!root || !m) return;
    if (!root.classList.contains('on-step-' + m[1])) {
      root.className = root.className.replace(/\\bon-step-\\d+\\b/g, '').trim();
      root.classList.add('on-step-' + m[1]);
      if (lastStep !== null) {
        var top = root.getBoundingClientRect().top + window.scrollY - 16;
        if (window.scrollY > top) window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
      }
      lastStep = m[1];
    }
  }
  var stepTick = null;
  new MutationObserver(function () {
    if (stepTick) return;
    stepTick = requestAnimationFrame(function () { stepTick = null; syncStep(); });
  }).observe(document.body, { childList: true, subtree: true, characterData: true });
  syncStep();
  // retaking starts over, so the rulebook shouldn't still be hanging open
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('#retake-btn, #home-btn') && window.mbtiRules) mbtiRules(false);
  }, true);
  // retake resets values without a click on the field itself
  setInterval(sync, 300);
})();

// gradio only re-fits a textarea's height to its own content on typing, so
// resizing the window (which rewraps placeholder/typed text into a
// different line count at the *old* fixed height) leaves it scroll-locked
// until the next keystroke. re-measure every textarea ourselves whenever
// the layout width could have changed.
(function () {
  function mbtiFitTextareas() {
    document.querySelectorAll('.gradio-container textarea').forEach(function (t) {
      if (!t.offsetParent) return;   // on a step that isn't showing, scrollHeight is 0 and would squash it
      t.style.height = 'auto';
      t.style.height = t.scrollHeight + 'px';
    });
  }
  var timer = null;
  window.addEventListener('resize', function () {
    clearTimeout(timer);
    timer = setTimeout(mbtiFitTextareas, 150);
  });
  if (window.ResizeObserver) {
    new ResizeObserver(function () {
      clearTimeout(timer);
      timer = setTimeout(mbtiFitTextareas, 150);
    }).observe(document.body);
  }
})();
</script>
"""

def hero_scene_svg():
    """
    a full-viewport pixel-game landscape wallpaper: softened classic-handheld-game
    palette (dusty blue/teal/mauve mountains, sage grass, warm dirt), plus the
    app's own trait icons (star, heart) floating in the sky as a brand callback.
    fixed piece of art, not a repeating pattern. canvas is close to a viewport's
    own proportions so the "cover" crop doesn't have to zoom in hard on one corner.
    """
    W, H = 1200, 900
    grass_y, dirt_y = 560, 720

    clouds = [(120, 110, 1.4), (520, 70, 1.1), (880, 150, 1.3), (1080, 90, 1.0)]
    cloud_svg = "".join(f'''
    <g transform="translate({cx},{cy}) scale({s})">
      <rect x="0" y="10" width="58" height="16" rx="8" fill="#FFFDF9"/>
      <rect x="13" y="0" width="32" height="18" rx="8" fill="#FFFDF9"/>
      <rect x="-9" y="13" width="28" height="11" rx="6" fill="#FFFDF9"/>
    </g>''' for cx, cy, s in clouds)

    mountains = [
        (10, grass_y, 300, 230, "#7B93B8"),
        (260, grass_y, 340, 300, "#6E9B96"),
        (560, grass_y, 300, 220, "#8C6E8C"),
        (820, grass_y, 340, 310, "#7B93B8"),
        (1090, grass_y, 300, 240, "#6E9B96"),
    ]
    mtn_svg = ""
    for bx, by, w, h, color in mountains:
        peak_x, peak_y = bx + w / 2, by - h
        mtn_svg += f'<polygon points="{bx},{by} {peak_x},{peak_y} {bx+w},{by}" fill="{color}"/>'
        cap_w, cap_h = w * 0.24, h * 0.22
        mtn_svg += (f'<polygon points="{peak_x-cap_w/2:.0f},{peak_y+cap_h:.0f} '
                    f'{peak_x:.0f},{peak_y:.0f} {peak_x+cap_w/2:.0f},{peak_y+cap_h:.0f}" fill="#FFFDF9"/>')

    icon_spots = [(190, 200, "star", "#C9A876", 1.6), (990, 160, "star", "#C9A876", 1.3), (640, 90, "heart", "#D9A0A6", 1.5)]
    icon_svg = ""
    for x, y, shape, color, s in icon_spots:
        colored_icon = ICONS[shape].replace("currentColor", color)
        icon_svg += f'<g transform="translate({x},{y}) scale({s})">{colored_icon}</g>'

    flowers = [60, 170, 320, 470, 610, 760, 880, 1010, 1130]
    flower_svg = "".join(f'''
    <g transform="translate({fx},{grass_y+70})">
      <rect x="-4" y="-11" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-11" y="-4" width="8" height="8" fill="#FFFDF9"/>
      <rect x="3" y="-4" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-4" y="3" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-2" y="-2" width="4" height="4" fill="#C9A876"/>
    </g>''' for fx in flowers)

    rocks = [(50, dirt_y+55, 18), (200, dirt_y+75, 13), (370, dirt_y+45, 16), (540, dirt_y+70, 11),
             (700, dirt_y+50, 18), (860, dirt_y+78, 13), (1000, dirt_y+48, 16), (1140, dirt_y+72, 11)]
    rock_svg = "".join(f'<ellipse cx="{rx}" cy="{ry}" rx="{rr}" ry="{rr*0.7:.0f}" fill="#5C4A38"/>' for rx, ry, rr in rocks)

    return f'''
    <svg width="100%" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" style="display:block">
      <rect x="0" y="0" width="{W}" height="{grass_y}" fill="#A3DBD8"/>
      {cloud_svg}
      {mtn_svg}
      {icon_svg}
      <rect x="0" y="{grass_y}" width="{W}" height="{dirt_y-grass_y}" fill="#8FA06E"/>
      {flower_svg}
      <rect x="0" y="{dirt_y}" width="{W}" height="{H-dirt_y}" fill="#A67C52"/>
      {rock_svg}
    </svg>
    '''


# ── type data ─────────────────────────────────────────────────────────────────
MBTI_DESCRIPTIONS = {
    "INTJ": ("the architect",    "strategic, private, always three steps ahead. you probably already know what they're going to say."),
    "INTP": ("the logician",     "you live in your head and love a rabbit hole. you argue for fun and call it curiosity."),
    "ENTJ": ("the commander",    "a natural leader, extremely sure of yourself, and not always gentle about it."),
    "ENTP": ("the debater",      "you argue for fun, get bored easily, and always find the counterpoint nobody else raised."),
    "INFJ": ("the advocate",     "intense and private, and somehow you know what people are thinking before they do."),
    "INFP": ("the mediator",     "idealistic and emotional. you write in your notes app at 2am and feel everything deeply."),
    "ENFJ": ("the protagonist",  "you make everyone feel seen, over-commit, and check in on people before they ask."),
    "ENFP": ("the campaigner",   "energetic and all over the place, and somehow still the most magnetic person in the room."),
    "ISTJ": ("the logistician",  "reliable to a fault. you show love through acts of service and keep everyone else on schedule."),
    "ISFJ": ("the defender",     "you take care of everyone and forget yourself. you remember everyone's coffee order."),
    "ESTJ": ("the executive",    "you have a spreadsheet for everything. you get things done, no vibes required."),
    "ESFJ": ("the consul",       "genuinely warm, and you like a little approval. you throw the best parties and stress-clean before guests arrive."),
    "ISTP": ("the virtuoso",     "quiet but extremely competent. not big on feelings, big on fix-it energy."),
    "ISFP": ("the adventurer",   "gentle and artistic, you keep your real thoughts to yourself. excellent taste, and you won't brag about it."),
    "ESTP": ("the entrepreneur", "impulsive and charismatic, you thrive on chaos you created."),
    "ESFP": ("the entertainer",  "the most fun person in the room. no plans, all vibes."),
}

# one line on what each character is, shown under the type name on the card
CREATURE_BLURBS = {
    "INTJ": "Owl with a crest gem. Sees three steps ahead.",
    "INTP": "Drifting cloud with three thoughts orbiting.",
    "ENTJ": "Crowned lion. Leads whether or not you asked.",
    "ENTP": "Fox with a lightning tail and one raised brow.",
    "INFJ": "Calm deer, glowing antlers, a moon on the brow.",
    "INFP": "Dreamy bunny with butterfly wings.",
    "ENFJ": "Songbird with a sun crest, mid-song.",
    "ENFP": "Puppy, confetti, a tail that never stops.",
    "ISTJ": "Turtle with a shell built from neat tiles.",
    "ISFJ": "Bear cub with a heart on its shield.",
    "ESTJ": "Bulldog in a tie, badge polished.",
    "ESFJ": "Penguin in a scarf, waving at you.",
    "ISTP": "Raccoon with goggles and a wrench for a tail.",
    "ISFP": "Chameleon wearing a flower, tail in a curl.",
    "ESTP": "Gecko in shades with a gold chain.",
    "ESFP": "Parrot in a party plume.",
}

IDENTITY_DESCRIPTIONS = {
    "A": "confident and even-keeled, you don't lose sleep over what you can't control.",
    "T": "self-aware with a perfectionist streak, you replay things more than you'd like to admit.",
}

# spoke order matches the printed type code (E/I, N/S, T/F, J/P, then A/T) so
# the pentagon and stat rows read in the same order as "ENFP-A" above them.
# "outward" is the named trait the spoke grows toward; a low reading just
# means the opposite pole, same as the axis itself, nothing invented here.
SPOKES = [
    ("E_I", "Energy",    "E", "#8FA06E", "bolt"),
    ("N_S", "Vision",    "N", "#7B93B8", "star"),
    ("T_F", "Empathy",   "F", "#D9A0A6", "heart"),
    ("J_P", "Freedom",   "P", "#C9A876", "swirl"),
    ("A_T", "Assurance", "A", "#6E9B96", "shield"),
]

ICONS = {
    "bolt": '<polygon points="9,1 3,11 8,11 6,17 15,7 9,7" fill="currentColor"/>',
    "star": '<polygon points="9,1 11,7 17,7 12,11 14,17 9,13 4,17 6,11 1,7 7,7" fill="currentColor"/>',
    "heart": '<path d="M9,16 C2,10 3,3 8,3 C9,3 9,4 9,4 C9,4 9,3 10,3 C15,3 16,10 9,16 Z" fill="currentColor"/>',
    "swirl": '<path d="M9,2 C13,2 16,5 16,9 C16,13 13,15 10,15 C7,15 6,13 6,11 C6,9 7.5,8 9.5,8.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',
    "shield": '<path d="M9,1 L16,4 V9 C16,13 13,16 9,17 C5,16 2,13 2,9 V4 Z" fill="currentColor"/>',
}

FAMILY_NAMES = {"NT": "ANALYST", "NF": "DIPLOMAT", "SJ": "SENTINEL", "SP": "EXPLORER"}

TYPE_INDEX = {code: i + 1 for i, code in enumerate(sorted(MBTI_DESCRIPTIONS.keys()))}


def _point(i, n, r, cx, cy):
    import math
    angle = math.radians(-90 + i * (360 / n))
    return cx + r * math.cos(angle), cy + r * math.sin(angle)


def _pentagon_svg(stats, size=120, show_labels=False, fill_container=False,
                  pad=1.55, r_frac=0.32, label_off=0.14, label_size=0.036, tight=False):
    """
    the shape itself is always drawn at `size` -- fixed relative to a
    cx,cy centered in that square. labels need extra room on top of that:
    the widest one ("ASSURANCE") reaches further out than `size` alone
    leaves room for, so the canvas the shape sits in is padded wider
    (mostly horizontal, since labels read left-to-right off side spokes;
    a little vertical for the top spoke's label) whenever labels are on.
    """
    cx = cy = size / 2
    r_max = size * r_frac if show_labels else size * 0.42
    n = len(stats)
    dot_r = max(4, size * 0.028)
    # tight: labels sit just above or below their own point instead of out to
    # the side, so the pentagon can take nearly the whole width. the result
    # card uses this to make the radar as big as it can be.
    if tight and show_labels:
        r_max = size * 0.43
        canvas_w, canvas_h = size * 1.12, size * 1.06
    else:
        canvas_w = size * pad if show_labels else size
        canvas_h = size * 1.1 if show_labels else size
    ox, oy = (canvas_w - size) / 2, (canvas_h - size) / 2
    cx, cy = cx + ox, cy + oy
    rings = ""
    for frac in (1, 0.66, 0.33):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * frac, cx, cy) for i in range(n)))
        rings += f'<polygon points="{pts}" fill="none" stroke="#D9CFC0" stroke-width="1"></polygon>'
    spokes = ""
    for i in range(n):
        x, y = _point(i, n, r_max, cx, cy)
        spokes += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#D9CFC0" stroke-width="1"></line>'
    # an ambiguous axis draws at the center (no lean either way) instead of
    # its raw score -- that score is either already near-neutral (a real
    # near-tie) or was forced ambiguous because nothing eligible has been
    # answered yet, in which case plotting it for real would draw a
    # confident-looking point the axis hasn't earned.
    shape_pct = [0 if is_ambiguous else pct for _, pct, _, _, is_ambiguous in stats]
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * (shape_pct[i] / 100), cx, cy) for i in range(n)))
    poly = f'<polygon class="radar-shape" points="{data_pts}" fill="#4A3B5C" fill-opacity="0.18" stroke="#4A3B5C" stroke-width="2.5"></polygon>'
    dots = ""
    for i, (name, pct, color, icon, is_ambiguous) in enumerate(stats):
        dot_color = "#C7BFAE" if is_ambiguous else color
        x, y = _point(i, n, r_max * (shape_pct[i] / 100), cx, cy)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r:.1f}" fill="{dot_color}" stroke="#4A3B5C" stroke-width="1.5"></circle>'
    labels = ""
    if show_labels:
        for i, (name, pct, color, icon, is_ambiguous) in enumerate(stats):
            if tight:
                # the top three points get their label above, the two bottom ones below
                x, y = _point(i, n, r_max, cx, cy)
                y += -size * 0.045 if i in (0, 1, 4) else size * 0.06
                anchor = "middle"
            else:
                x, y = _point(i, n, r_max + size * label_off, cx, cy)
                # anchor points away from the shape (right side grows rightward,
                # left side grows leftward) so long labels like "assurance"
                # read outward instead of back over the pentagon.
                if x > cx + 2:
                    anchor = "start"
                elif x < cx - 2:
                    anchor = "end"
                else:
                    anchor = "middle"
            labels += (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
                       f'font-family="Silkscreen, monospace" font-size="{max(8, size*label_size):.0f}" '
                       f'font-weight="700" fill="#6B5D7D">{name.upper()}</text>')
    width_attr = "100%" if fill_container else f"{canvas_w:.0f}"
    height_part = "" if fill_container else f' height="{canvas_h:.0f}"'
    return (f'<svg width="{width_attr}"{height_part} viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}" '
            f'preserveAspectRatio="xMidYMid meet">{rings}{spokes}{poly}{dots}{labels}</svg>')


def confidence_bars_html(stats):
    """
    per-axis reading, always on screen next to the pentagon -- the shape
    alone requires cross-referencing five points against a five-sided
    outline, the bars just say the same numbers in a form you can read
    at a glance without doing that math yourself.
    """
    rows = ""
    for name, pct, color, icon, is_ambiguous in stats:
        if is_ambiguous:
            rows += f"""
    <div class="conf-row conf-row-ambiguous">
      <span class="conf-name">{name}</span>
      <div class="conf-track"><div class="conf-fill" style="width:0%"></div></div>
      <span class="conf-pct">?</span>
    </div>"""
        else:
            rows += f"""
    <div class="conf-row">
      <span class="conf-name">{name}</span>
      <div class="conf-track"><div class="conf-fill" style="width:{pct}%;background:{color}"></div></div>
      <span class="conf-pct">{pct}</span>
    </div>"""
    return f'<div class="conf-bars">{rows}</div>'


def live_head_html(axis_results=None):
    """the panel's title row, with the type code so far on the right: a letter once
    a stat is clear enough to call, a "?" until then (same order as the result card)."""
    letters = []
    for axis, *_ in SPOKES:
        r = (axis_results or {}).get(axis)
        letters.append("?" if not r or r.get("is_ambiguous") else r["winner"])
    spans = "".join(f'<span class="{"lc-open" if l == "?" else "lc-set"}">{l}</span>' for l in letters[:4])
    tail = f'<span class="{"lc-open" if letters[4] == "?" else "lc-set"}">{letters[4]}</span>'
    return f'''<div class="live-head"><div class="card-eyebrow">Live Radar</div><div class="live-code">{spans}<i>-</i>{tail}</div></div>'''


def loading_panel_html():
    """shown the instant a Next/submit click fires, before the (slow) real
    classifier call returns -- so the wait reads as "working" instead of a
    frozen page."""
    return """
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Radar</div>
      <div class="live-status loading"><span class="mbti-spinner"></span> reading your answers…</div>
    </div>
    """


def empty_progress_html():
    """starting state, before step 1 has been submitted: nothing to read yet."""
    stats = [(name, 0, color, icon, True) for _, name, _, color, icon in SPOKES]
    pentagon = _pentagon_svg(stats, size=340, show_labels=True, fill_container=True)
    return f"""
    <div class="live-panel-inner">
      {live_head_html()}
      <div class="live-status">answer step 1 to start your read</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
      {confidence_bars_html(stats)}
    </div>
    """


EYE_SVG = ('<svg class="rt-eye" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true">'
           '<path d="M1.5 9S4.5 3.5 9 3.5 16.5 9 16.5 9 13.5 14.5 9 14.5 1.5 9 1.5 9z"/><circle cx="9" cy="9" r="2.3"/><path class="rt-slash" d="M3 15L15 3"/></svg>')


def step_indicator_html(current, total):
    pct = round(current / total * 100)
    return f"""
    <div class="step-indicator">
      <div class="step-top">
        <span>STEP {current} OF {total}</span>
        <button type="button" class="radar-toggle" onclick="mbtiRadar()" aria-pressed="false" title="hide the live radar so it can't sway your answers">{EYE_SVG}<b class="rt-hide">hide radar</b><b class="rt-show">show radar</b></button>
      </div>
      <div class="step-bar-track"><div class="step-bar-fill" style="width:{pct}%"></div></div>
    </div>
    """


def _extract_stats(axis_results):
    stats = []
    for axis_key, name, outward, color, icon in SPOKES:
        r = axis_results.get(axis_key, {})
        pct = round(r.get("scores", {}).get(outward, 50))
        stats.append((name, pct, color, icon, bool(r.get("is_ambiguous"))))
    return stats


def ai_read_html(text, axis_results):
    """
    the differentiator, on screen: the answers the model just read, in the
    person's own words, each with the way it leaned and how hard. nothing here
    is a lookup table, it is the real model output for what was typed, updating
    step to step.
    """
    if not axis_results:
        return ""

    names = {k: name for k, name, *_ in SPOKES}
    reads = [(rd["pct"], axis_key, rd) for axis_key, r in axis_results.items() for rd in r.get("reads", [])]
    reads.sort(key=lambda t: -t[0])

    rows, seen = "", set()
    for pct, axis_key, rd in reads:
        if rd["raw"] in seen:
            continue
        seen.add(rd["raw"])
        raw = rd["raw"] if len(rd["raw"]) <= 90 else rd["raw"][:90].rsplit(" ", 1)[0] + "…"
        rows += (f'<div class="ai-read-item"><span class="ai-quote">&ldquo;{html.escape(raw)}&rdquo;</span>'
                 f'<span class="ai-lean">leans <b>{rd["key"]}</b> on {names[axis_key]}, {pct}%</span></div>')
        if len(seen) >= 3:
            break
    if not rows:
        return ""

    confident = {k: r for k, r in axis_results.items() if not r.get("is_ambiguous")}
    if confident:
        axis_key, r = max(confident.items(), key=lambda kv: kv[1]["confidence"])
        read_line = f'so far the surest read is <b>{r["winner"]}</b> on {names[axis_key]} ({round(r["confidence"])}%)'
    else:
        read_line = "still gathering signal, nothing decisive yet"

    return f"""
    <div class="ai-read">
      <div class="ai-read-label">What The Model Just Read</div>
      {rows}
      <div class="ai-read-line">{read_line}</div>
    </div>
    """


def live_pentagon_html(axis_results, text=""):
    """
    real partial read: whatever's been answered through this step, classified
    for real against all 5 axes (the shared-blob design means even one field
    already moves every axis, not just "its own"). refines each step, no
    fabricated numbers at any point.
    """
    stats = _extract_stats(axis_results)
    pentagon = _pentagon_svg(stats, size=340, show_labels=True, fill_container=True)
    return f"""
    <div class="live-panel-inner">
      {live_head_html(axis_results)}
      <div class="live-status">reading your answers so far</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
      {confidence_bars_html(stats)}
      {ai_read_html(text, axis_results)}
    </div>
    """


def run_partial(answers):
    try:
        mbti_type, axis_results, text = predict_mbti(answers, photo_results=None)
    except Exception as e:
        print(f"partial prediction error: {e}")
        return empty_progress_html()

    if axis_results is None:
        return empty_progress_html()

    return live_pentagon_html(axis_results, text)


FAMILY_PLURALS = {"NT": "analysts", "NF": "diplomats", "SJ": "sentinels", "SP": "explorers"}
FAMILY_COLORS = {"NT": "#7B93B8", "NF": "#8FA06E", "SJ": "#6E9B96", "SP": "#C9A876"}


def _family_key(code):
    return ("N" + code[2]) if code[1] == "N" else ("S" + code[3])


def all_types_html(mine=None):
    """the gallery: all 16 types with their pixel characters, grouped by family."""
    groups = ""
    for fam in ("NT", "NF", "SJ", "SP"):
        cards = ""
        for code in sorted(c for c in MBTI_DESCRIPTIONS if _family_key(c) == fam):
            title, desc = MBTI_DESCRIPTIONS[code]
            you = ' mine' if code == mine else ""
            tag = '<span class="tcard-you">you</span>' if code == mine else ""
            cards += f"""
        <div class="tcard{you}" style="--fam:{FAMILY_COLORS[fam]}"><div class="tband"><div class="tbody">
          <div class="tcard-top"><span class="tcard-no">NO. {TYPE_INDEX[code]:02d}</span>{tag}</div>
          <div class="artwin sm"><div class="tstage"><canvas data-sprite="{code}" width="252" height="252"></canvas></div></div>
          <div class="tcode">{code}</div>
          <div class="ttitle">{title}</div>
          <div class="tblurb">{CREATURE_BLURBS[code]}</div>
          <div class="tdesc">{desc}</div>
        </div></div></div>"""
        groups += f"""
      <div class="tgroup">
        <div class="tgroup-head"><span class="family-swatch" style="background:{FAMILY_COLORS[fam]}"></span>{FAMILY_PLURALS[fam]}</div>
        <div class="tgrid">{cards}</div>
      </div>"""
    return f"""
  <div class="types-page">
    <div class="types-bar">
      <span class="types-title">all 16 type mascots</span>
      <button class="rv-tool" onclick="mbtiTypes(false)">&larr; back</button>
    </div>
    {groups}
    <div class="types-foot"><button class="rv-tool" onclick="mbtiTypes(false)">&larr; back to your result</button></div>
  </div>"""


RAINBOW_DEFS = foil_art.stripes_defs()   # the diagonal stripe fill for the radar shape on a rainbow card
ROTATE_SVG = ('<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true">'
              '<path d="M3 9a6 6 0 0 1 10-4.5"/><path d="M13 1.5v3.5H9.5"/><path d="M15 9a6 6 0 0 1-10 4.5"/><path d="M5 16.5V13h3.5"/></svg>')
SHARE_SVG = ('<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true">'
             '<path d="M9 11V2"/><path d="M5.5 5.5L9 2l3.5 3.5"/><path d="M3 9v7h12V9"/></svg>')
SAVE_SVG = ('<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true">'
            '<path d="M9 2v9"/><path d="M5.5 7.5L9 11l3.5-3.5"/><path d="M3 12v4h12v-4"/></svg>')
COPY_SVG = ('<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true">'
            '<rect x="6" y="6" width="9" height="9"/><path d="M12 3H3v9"/></svg>')


def build_reveal_html(mbti_type, axis_results, finish="common"):
    core, suffix = mbti_type.split("-")
    core_display = core  # always four real letters: the answer is one of the 16 types
    title, desc = MBTI_DESCRIPTIONS[core_display]
    identity_desc = IDENTITY_DESCRIPTIONS[suffix]

    n_s = core_display[1] if len(core_display) > 1 else "N"
    t_f = core_display[2] if len(core_display) > 2 else "F"
    j_p = core_display[3] if len(core_display) > 3 else "J"

    family_key = ("N" if n_s == "N" else "S") + (t_f if n_s == "N" else j_p)
    family_name, family_color = FAMILY_NAMES.get(family_key, "UNPLACED"), {
        "NT": "#7B93B8", "NF": "#8FA06E", "SJ": "#6E9B96", "SP": "#C9A876"
    }.get(family_key, "#8C6E8C")

    # on the final card every axis has a real answer, so none of them is drawn
    # as an empty spoke: a close call still gets its lean on the radar
    stats = [(name, pct, color, icon, False) for name, pct, color, icon, _ in _extract_stats(axis_results)]
    pentagon = _pentagon_svg(stats, size=340, show_labels=True, fill_container=True, label_size=0.032, tight=True)

    # the pentagon spoke always grows toward "outward" so the shape stays
    # readable, but the row below names the actual winner with THAT letter's own
    # confidence. an axis that was a close call still names its letter and is
    # tagged as one.
    stat_rows = ""
    card_stats = []
    for (axis_key, name, outward, color, icon), (_, radar_pct, *_rest) in zip(SPOKES, stats):
        r = axis_results.get(axis_key, {})
        letter = r.get("winner", outward)
        num = round(r.get("confidence", 50))
        close = bool(r.get("is_ambiguous"))
        soft = ' <span class="stat-soft">close call</span>' if close else ""
        card_stats.append({"name": name, "letter": letter, "pct": num, "radar": radar_pct, "color": color, "soft": close})
        stat_rows += f'''
    <div class="stat-row">
      <svg class="stat-icon" viewBox="0 0 18 18" style="color:{color}">{ICONS[icon]}</svg>
      <span class="stat-name">{name} <span class="stat-letter">({letter})</span>{soft}</span>
      <span class="stat-bar"><i style="width:{num}%;background:{color}"></i></span>
      <span class="stat-num">{num}</span>
    </div>'''

    avg_spread = sum(abs(p - 50) for _, p, _, _, _ in stats) / len(stats)
    if avg_spread > 30:
        rarity, rarity_color = "RARE", "#D9A0A6"
    elif avg_spread > 15:
        rarity, rarity_color = "UNCOMMON", "#8FA06E"
    else:
        rarity, rarity_color = "MIXED SIGNAL", "#C9A876"

    index = TYPE_INDEX.get(core_display, 0)
    code = f"{core_display}-{suffix}"
    close_names = [s["name"] for s in card_stats if s["soft"]]
    close_note = ("close call on " + ", ".join(close_names)) if close_names else "a clear read on every stat"
    if not F.is_finish(finish):
        finish = "common"
    sprite = f'<canvas data-sprite="{core_display}" width="252" height="252"></canvas>'
    finish_tag = f'<span class="finish-tag">{F.FINISHES[finish]["label"]}</span>' if finish != "common" else ""

    # the export button redraws the wide card from this, so it carries everything
    card_data = html.escape(json.dumps({
        "code": core_display, "suffix": suffix, "title": title, "family": family_name,
        "familyColor": family_color, "dex": index, "desc": desc, "identity": identity_desc,
        "blurb": CREATURE_BLURBS[core_display],
        "finish": finish, "finishLabel": F.FINISHES[finish]["label"],
        "stats": card_stats,
    }), quote=True)

    top_row = f"""
        <div class="rcard-top">
          <div class="rcard-tags">
            <div class="family-badge"><span class="family-label">{family_name}</span></div>
            {finish_tag}
          </div>
          <span class="card-index">NO. {index:02d} / 16</span>
        </div>"""
    name_block = f"""
        <div class="rname">
          <span class="rcode">{code}</span>
          <span class="rtitle">{title}</span>
        </div>"""
    blurb_strip = f'<div class="rblurb">{CREATURE_BLURBS[core_display]}</div>'
    art_window = f'<div class="artwin art"><div class="rstage">{sprite}</div></div>'
    radar_window = f'<div class="artwin"><div class="rradar">{pentagon}</div></div>'

    return f"""
{RAINBOW_DEFS}<div class="rv" id="rv" data-layout="card" data-finish="{finish}" style="--fam:{family_color}" data-card="{card_data}">

  <div class="pack-stage" id="packStage">
    <div class="rpack" id="pack1">
      <div class="rpack-top">{pack_art.top_piece()}</div>
      <div class="rpack-body">{pack_art.body_piece()}</div>
      <div class="slice-zone" id="sliceZone" role="button" tabindex="0" aria-label="Slice the pack open"
           onpointerdown="mbtiSliceStart(event)" onpointermove="mbtiSliceMove(event)"
           onpointerup="mbtiSliceEnd(event)" onpointercancel="mbtiSliceEnd(event)"
           onkeydown="if (event.key === 'Enter' || event.key === ' ') {{ event.preventDefault(); mbtiSlice(); }}">
        <div class="slice-line"></div>
        <div class="slice-cut"></div>
        <div class="slice-blade">&#9986;</div>
      </div>
    </div>
    <div class="rpack-hint">drag across the dashed line to slice it open</div>
  </div>

  <div class="card-scene">
    <div class="flip" id="flip1" onclick="mbtiFlip()" title="tap to flip">
      <div class="flip-in">
        <div class="face front"><div class="fband"><div class="fbody">
          {top_row}
          {name_block}
          {art_window}
          {blurb_strip}
          <div class="flavor-bar">{desc}</div>
          <div class="identity-bar"><b>{suffix}-identity:</b> {identity_desc}</div>
          <div class="rhint">{ROTATE_SVG}<span>tap to flip &middot; your radar</span></div>
        </div></div></div>
        <div class="face back"><div class="fband"><div class="fbody">
          <div class="rcard-top">
            <div class="rcard-tags"><span class="card-index">YOUR RADAR</span>{finish_tag}</div>
            <span class="card-index">{code}</span>
          </div>
          {radar_window}
          <div class="stat-rows">{stat_rows}</div>
          <div class="rarity-row"><span class="rarity-tag" style="background:{rarity_color}">{rarity}</span><span class="rclose">{close_note}</span></div>
          <div class="rhint">{ROTATE_SVG}<span>tap to flip &middot; the mascot</span></div>
        </div></div></div>
      </div>
    </div>

    <div class="wide-card" id="wide1"><div class="fband"><div class="fbody">
      {top_row}
      <div class="wide-row">
        {art_window}
        {radar_window}
      </div>
      {name_block}
      {blurb_strip}
      <div class="wide-stats stat-rows">{stat_rows}</div>
      <div class="flavor-bar">{desc}</div>
      <div class="identity-bar"><b>{suffix}-identity:</b> {identity_desc}</div>
      <div class="wide-foot"><span class="wide-who"></span><span>MBTI RADAR</span></div>
    </div></div></div>

    <div class="rv-tools">
      <button class="rv-tool" id="layoutBtn" onclick="mbtiLayout()">wide view</button>
      <button class="rv-tool has-ico" id="shareBtn" onclick="mbtiExportPanel()">{SHARE_SVG}<span>share</span></button>
      <button class="rv-tool" onclick="mbtiPack()">open another pack</button>
      <button class="rv-tool" onclick="mbtiTypes(true)">all 16 mascots</button>
    </div>

    <div class="export-panel" id="exportPanel">
      <label class="export-label" for="exportName">name on the card <span>(optional)</span></label>
      <input id="exportName" type="text" maxlength="40" autocomplete="name" placeholder="your full name" oninput="mbtiWho()">
      <div class="export-actions">
        <button class="rv-tool has-ico" id="nativeShareBtn" onclick="mbtiShare()">{SHARE_SVG}<span>share</span></button>
        <button class="rv-tool has-ico" id="copyBtn" onclick="mbtiCopy()">{COPY_SVG}<span>copy image</span></button>
        <button class="rv-tool has-ico" onclick="mbtiExport()">{SAVE_SVG}<span>save image</span></button>
      </div>
      <p class="export-note" id="exportNote">your name and today's date get printed on the card. it stays in your browser, nothing is sent or saved.</p>
    </div>
  </div>
  {all_types_html(core_display)}
</div>
"""


# each rule pairs a plain-language headline (the whole story, for a friend
# just skimming) with a detail line underneath (the real mechanism, for
# anyone who keeps reading) -- same text serves both readers, just at two
# depths.
HOW_IT_WORKS_RULES = [
    ("bolt", "no dice, no randomness",
     "Every card comes from a real language model actually reading what you typed.",
     "A zero-shot NLI classifier (<code>facebook/bart-large-mnli</code>) compares your answers against a short description of each trait and scores how well they match."),
    ("star", "five stats, five separate reads",
     "Energy, Vision, Empathy, Freedom, and Assurance each get their own pass.",
     "Every question is written for particular stats, and a stat only reads the answers meant for it. Your humor tag or your music taste can't sneak a number onto a stat they say nothing about."),
    ("swirl", "close calls still get an answer",
     "The live radar shows “?” for a stat until two real answers have spoken to it. Your final card always names a full type.",
     "When your answers lean both ways, the card still picks a side and tags that stat a close call, so you can see where the read was thin."),
    ("heart", "photos count for a quarter",
     "Drop in a photo and DeepFace and OpenCV read expression, face count, and eye contact as small adjustments.",
     "A photo is weighted at 25% of the read. With no photo, text carries all of it."),
    ("shield", "tested on 16 snippets",
     "16 hand-written test snippets confirm the classifier reads clearly stated traits correctly.",
     "Mean confidence is over 97% on unambiguous text (see <code>eval_axes.py</code>). There's no labeled dataset of real people, so real-world accuracy is unknown. Treat it as a heuristic sketch."),
]


def _landing_card(finish, pos):
    """one big card for the spread. it's the real result card markup (so the finishes look exactly
    like they will when you pull them), but the mascot is a dark silhouette and every word about
    who it is stays a question mark. only the finish is on show."""
    label = F.FINISHES[finish]["label"]
    tag = f'<span class="finish-tag">{label}</span>' if finish != "common" else ""
    return f'''
    <div class="rv lc lc-{pos} sliced" data-finish="{finish}" style="--fam:#8C6E8C">
      <div class="card-scene"><div class="face"><div class="fband"><div class="fbody">
        <div class="rcard-top">
          <div class="rcard-tags"><div class="family-badge"><span class="family-label">???</span></div>{tag}</div>
          <span class="card-index">NO. ?? / {len(MBTI_DESCRIPTIONS)}</span>
        </div>
        <div class="rname"><span class="rcode">????-?</span><span class="rtitle">your type mascot</span></div>
        <div class="artwin art"><div class="rstage"><canvas data-landing data-sprite="ENFP" width="252" height="252"></canvas></div></div>
        <div class="rblurb">???</div>
      </div></div></div></div>
    </div>'''


def landing_html():
    """the first screen. it sells the finishes, not the mascots: three big cards fanned out (all with the
    mascot hidden), what each finish looks like, and how often it shows up. you always get the mascot that
    is you, the chase is pulling the holo and the rainbow."""
    ids = F.FINISH_IDS
    # common up front. holo goes on the left because its shine sits toward the middle of the card, and the
    # rainbow (bands all over) goes on the right, so both show what makes them special from behind the front card
    cards = _landing_card(ids[1], "far") + _landing_card(ids[2], "mid") + _landing_card(ids[0], "front")
    odds = "".join(
        f'<div class="odds-pill odds-{f}"><b>{F.FINISHES[f]["label"]}</b><span>{F.ODDS[f]}%</span></div>' for f in ids)
    return f'''
  <div class="landing">
    <h2 class="landing-title">meet your type mascot</h2>
    <p class="landing-sub">you get the one that's you. the question is which finish you pull.</p>
    <div class="landing-fan">{cards}</div>
    <p class="landing-odds-title">your odds in every pack</p>
    <div class="landing-odds">{odds}</div>
    <p class="landing-first">you get {F.TOTAL_PACKS} packs to chase the rare ones.</p>
    <button class="start-btn" type="button" onclick="mbtiStart()">{STAR_SVG}<span>earn your first pack</span></button>
    <p class="landing-note">answer a short quiz, open your pack, meet your mascot.</p>
  </div>'''


STAR_SVG = ('<svg viewBox="0 0 40 40" aria-hidden="true"><polygon points="20,4 24,15 36,15 26,22 30,34 20,26 10,34 14,22 4,15 16,15" '
            'fill="#C9A876" stroke="#4A3B5C" stroke-width="3" stroke-linejoin="round"/></svg>')


def rules_block_svg():
    """a pixel '?' item block, the kind you bump from below for a coin."""
    glyph = ["01110", "10001", "00001", "00110", "00100", "00000", "00100"]
    px = "".join(
        f'<rect x="{10 + c * 4}" y="{7 + r * 4}" width="4" height="4" fill="#4A3B5C"/>'
        for r, row in enumerate(glyph) for c, v in enumerate(row) if v == "1"
    )
    rivets = "".join(f'<rect x="{x}" y="{y}" width="3" height="3" fill="#4A3B5C"/>' for x, y in [(4, 4), (33, 4), (4, 33), (33, 33)])
    return f"""<svg viewBox="0 0 40 40" width="46" height="46" shape-rendering="crispEdges">
      <rect x="1" y="1" width="38" height="38" fill="#C9A876" stroke="#4A3B5C" stroke-width="2"/>
      <rect x="3" y="3" width="34" height="3" fill="#EDE6D3" opacity="0.7"/>
      {rivets}{px}
    </svg>"""


def rules_block_html():
    return f"""<button class="rules-block" id="rules-block" onclick="mbtiRules()" aria-label="How it works" aria-expanded="false">
      {rules_block_svg()}
      <span class="rules-block-label">how it works</span>
    </button>"""


def how_it_works_html():
    rows = ""
    for icon, headline, plain, detail in HOW_IT_WORKS_RULES:
        rows += f"""
    <div class="rule-row">
      <svg class="rule-icon" viewBox="0 0 18 18">{ICONS[icon]}</svg>
      <div class="rule-copy">
        <div class="rule-headline">{headline}</div>
        <div class="rule-plain">{plain}</div>
        <div class="rule-detail">{detail}</div>
      </div>
    </div>"""

    return f"""
<div class="rules-panel" id="rules-panel">
  <div class="rules-panel-clip">
    <div class="rulebook-card">
      <button class="rules-close" onclick="mbtiRules(false)" aria-label="Close">x</button>
      <div class="rulebook-head">
        <svg width="26" height="26" viewBox="0 0 40 40">
          <polygon points="20,4 24,15 36,15 26,22 30,34 20,26 10,34 14,22 4,15 16,15"
                    fill="#C9A876" stroke="#4A3B5C" stroke-width="2.5" stroke-linejoin="round"/>
        </svg>
        <div>
          <div class="rulebook-title">behind the cards</div>
          <div class="rulebook-sub">what happens between your answers and the type pack</div>
        </div>
      </div>
      <div class="rule-grid">{rows}</div>
    </div>
  </div>
</div>
"""


def run_prediction(*values):
    data = dict(zip(ALL_FIELD_NAMES + ["photo"], values))
    photo = data.pop("photo")
    # generator: the photo analysis + classifier call below can take a
    # while, so the button flips to a disabled loading label the instant
    # it's clicked instead of just sitting there looking unresponsive.
    yield gr.update(), gr.update(), gr.update(), gr.update(value="Reading your type…", interactive=False)

    photo_results = None
    if photo is not None:
        try:
            from photo_analysis import analyze_photo
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis error: {e}")
        finally:
            # the promise on the page: it's read once, then deleted
            try:
                os.remove(photo)
            except OSError:
                pass

    reset_btn = gr.update(value="open your type pack ↗", interactive=True)

    try:
        mbti_type, axis_results, _text = predict_mbti(data, photo_results=photo_results)
    except Exception as e:
        print(f"prediction error: {e}")
        yield (
            '<div class="result-empty">having trouble right now, give it a moment and try again.</div>',
            gr.update(visible=True), gr.update(visible=False), reset_btn,
        )
        return

    if axis_results is None:
        yield (
            '<div class="result-empty">fill in at least a few fields to get a read.</div>',
            gr.update(visible=True), gr.update(visible=False), reset_btn,
        )
        return
    yield build_reveal_html(mbti_type, axis_results, F.pull_finish(1)), gr.update(visible=False), gr.update(visible=True), reset_btn


# ── theme ─────────────────────────────────────────────────────────────────────
theme = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#F7F3EA", c100="#EDE6D3", c200="#DED0AE", c300="#CBB989",
        c400="#B69C6E", c500="#C9A876", c600="#9C8460", c700="#7C6A4E",
        c800="#5C4E3B", c900="#4A3B5C", c950="#2E2440",
    ),
    secondary_hue="emerald",
    neutral_hue="stone",
    font=gr.themes.GoogleFont("Rubik"),
    font_mono=gr.themes.GoogleFont("Silkscreen"),
).set(
    # every color below also sets its _dark twin to the same value: this
    # theme is a fixed cream/plum look, not one that should reflow when the
    # os is in dark mode, so nothing here is allowed to diverge between the
    # two.
    body_background_fill="#FFFDF9",
    body_background_fill_dark="#FFFDF9",
    block_background_fill="#EDE6D3",
    block_background_fill_dark="#EDE6D3",
    block_border_color="#4A3B5C",
    block_border_color_dark="#4A3B5C",
    block_border_width="2px",
    block_radius="8px",
    block_shadow="none",
    block_label_text_size="sm",
    block_label_text_weight="600",
    block_label_text_color="#362B47",
    block_label_text_color_dark="#362B47",
    block_label_background_fill="transparent",
    block_label_background_fill_dark="transparent",
    block_label_border_width="0px",
    block_label_padding="0px",
    block_label_margin="0px",
    block_label_radius="0px",
    block_label_shadow="none",
    block_title_text_color="#362B47",
    block_title_text_color_dark="#362B47",
    block_title_background_fill="transparent",
    block_title_background_fill_dark="transparent",
    input_background_fill="#FFFFFF",
    input_background_fill_dark="#FFFFFF",
    input_border_color="#4A3B5C",
    input_border_color_dark="#4A3B5C",
    input_border_color_focus="#8FA06E",
    input_border_color_focus_dark="#8FA06E",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(143,160,110,0.25)",
    input_radius="4px",
    checkbox_background_color="#FFFFFF",
    checkbox_background_color_dark="#FFFFFF",
    checkbox_border_color="#4A3B5C",
    checkbox_border_color_dark="#4A3B5C",
    checkbox_border_color_selected="#4A3B5C",
    checkbox_border_color_selected_dark="#4A3B5C",
    checkbox_background_color_selected="#8FA06E",
    checkbox_background_color_selected_dark="#8FA06E",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_background_fill_dark="#FFFFFF",
    checkbox_label_background_fill_hover="#F7F3EA",
    checkbox_label_background_fill_hover_dark="#F7F3EA",
    checkbox_label_background_fill_selected="#8FA06E",
    checkbox_label_background_fill_selected_dark="#8FA06E",
    checkbox_label_border_color="#4A3B5C",
    checkbox_label_border_color_dark="#4A3B5C",
    checkbox_label_border_color_hover="#4A3B5C",
    checkbox_label_border_color_hover_dark="#4A3B5C",
    checkbox_label_border_color_selected="#4A3B5C",
    checkbox_label_border_color_selected_dark="#4A3B5C",
    checkbox_label_text_color="#6B5D7D",
    checkbox_label_text_color_dark="#6B5D7D",
    checkbox_label_text_color_selected="#FFFFFF",
    checkbox_label_text_color_selected_dark="#FFFFFF",
    button_primary_background_fill="#4A3B5C",
    button_primary_background_fill_dark="#4A3B5C",
    button_primary_background_fill_hover="#8FA06E",
    button_primary_background_fill_hover_dark="#8FA06E",
    button_primary_text_color="#EDE6D3",
    button_primary_text_color_dark="#EDE6D3",
    button_primary_border_color="transparent",
    button_primary_border_color_dark="transparent",
    button_large_radius="6px",
    button_large_padding="14px 32px",
    slider_color="#8FA06E",
    slider_color_dark="#8FA06E",
    border_color_primary="#4A3B5C",
    border_color_primary_dark="#4A3B5C",
    color_accent="#8FA06E",
    color_accent_soft="#F7F3EA",
    color_accent_soft_dark="#F7F3EA",
    link_text_color="#8FA06E",
    link_text_color_dark="#8FA06E",
    body_text_color="#362B47",
    body_text_color_dark="#362B47",
    body_text_color_subdued="#6B5D7D",
    body_text_color_subdued_dark="#6B5D7D",
)




# ── wizard step handlers ────────────────────────────────────────────────────
# the quiz itself lives in questions.py. everything below is built from it, so
# steps, required answers and the "answered so far" lists never drift apart.
TOTAL_STEPS = len(STEPS)
LAST_STEP = STEPS[-1]

STEP_NAMES = {s: answer_ids(s) for s in STEPS}
STEP_REQUIRED = {s: required_ids(s) for s in STEPS}


def _cumulative_names(step):
    return [n for s in STEPS if s <= step for n in STEP_NAMES[s]]


CUM_NAMES = {s: _cumulative_names(s) for s in STEPS}
ALL_FIELD_NAMES = CUM_NAMES[LAST_STEP]

# required answers: name -> (label used in the callout, kind, what to do when empty)
REQUIRED = {
    q["id"]: (
        q["short"],
        "pick" if q["kind"] in ("checks", "radio") else ("reply" if q["kind"] == "msg" or q.get("min") == "reply" else "text"),
        q["hint"],
    )
    for q in QUESTIONS if q.get("required")
}


def _is_substantial(text, min_chars=8):
    """
    catches the "typed a single letter to get past a required field" case --
    not a judgment of quality, just a floor: too short, or too little
    actual variety in the characters (a repeated key mashed a few times),
    isn't enough for the model to read anything real off of.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    if len(set(stripped.lower().replace(" ", ""))) <= 2:
        return False
    return True


def _problem(name, value):
    _label, kind, empty_hint = REQUIRED[name]
    if kind == "reply":
        # a real reply can be very short ("ok", "lol"), so no length or
        # variety floor here, just that something was written
        return None if value and value.strip() else empty_hint
    if kind == "text":
        if not value or not value.strip():
            return empty_hint
        if not _is_substantial(value):
            return "add a few more words so the model has something to read"
        return None
    return None if value else empty_hint


def _step_problems(step, data):
    problems = []
    for name in STEP_REQUIRED[step]:
        q = BY_ID[name]
        if not is_shown(q, data):
            continue   # only asked once its chip is ticked
        if q.get("hide_if_no_social") and data.get("posting_frequency") in (NO_SOCIAL, NOT_SURE):
            continue
        if q["kind"] == "msg":
            # a typed reply or one of its chips both count
            why = None if any(data.get(c["id"]) for c in q["chips"]) or (data.get(name) or "").strip() else q["hint"]
        elif q["kind"] == "pick":
            why = None if any(data.get(c["id"]) for c in q["chips"]) else q["hint"]
        elif q["kind"] == "slider":
            # the slider starts at 0, which isn't an answer, so it has to be moved
            why = None if (data.get(name) or 0) >= 1 else q["hint"]
        else:
            why = _problem(name, data.get(name))
        if why:
            problems.append((name, REQUIRED[name][0], why))
    return problems


def need_block_svg():
    """the "?" block's warning twin: a pixel "!" block in blush."""
    glyph = ["00100", "00100", "00100", "00100", "00100", "00000", "00100"]
    px = "".join(
        f'<rect x="{10 + c * 4}" y="{6 + r * 4}" width="4" height="4" fill="#4A3B5C"/>'
        for r, row in enumerate(glyph) for c, v in enumerate(row) if v == "1"
    )
    return f"""<svg viewBox="0 0 40 40" width="40" height="40" shape-rendering="crispEdges">
      <rect x="1" y="1" width="38" height="38" fill="#D9A0A6" stroke="#4A3B5C" stroke-width="2"/>
      <rect x="3" y="3" width="34" height="3" fill="#F3DDD9" opacity="0.8"/>{px}
    </svg>"""


def need_callout_html(problems, fresh=False):
    n = len(problems)
    title = "1 answer still needed" if n == 1 else f"{n} answers still needed"
    items = "".join(
        f'<li><a href="#f-{name}" onclick="var e=document.getElementById(\'f-{name}\');'
        f'if(e){{e.scrollIntoView({{behavior:\'smooth\',block:\'center\'}});}}return false;">{label}</a>'
        f'<span>: {why}</span></li>'
        for name, label, why in problems
    )
    return f"""
    <div class="need-callout" role="alert"{' data-fresh="1"' if fresh else ''}>
      <div class="need-icon">{need_block_svg()}</div>
      <div class="need-body">
        <div class="need-title">{title}</div>
        <ul>{items}</ul>
      </div>
    </div>"""


def callout_update(problems, fresh=False):
    """the "still needed" callout. the highlight on each field is drawn client-side
    from the links inside it (see the head script), so no field has to be re-rendered."""
    if problems:
        return gr.update(value=need_callout_html(problems, fresh), visible=True)
    return gr.update(value="", visible=False)


def _problem_key(problems):
    # what the callout says right now, so an unchanged callout isn't re-rendered on every keystroke
    return "a:" + "|".join(f"{name}:{why}" for name, _label, why in problems)


def make_next_handler(step):
    names = CUM_NAMES[step]

    def handler(*values):
        data = dict(zip(names, values))
        problems = _step_problems(step, data)
        if problems:
            yield (gr.skip(),) * 3 + (callout_update(problems, fresh=True), _problem_key(problems))
            return
        # generator so the loading state reaches the page before the (slow)
        # classifier call starts; the real result replaces it in the second yield.
        yield (loading_panel_html(), gr.skip(), gr.update(value="Loading…", interactive=False), callout_update([]), "")
        panel = run_partial(data)
        yield (panel, step_indicator_html(step + 1, TOTAL_STEPS),
               gr.update(value="Next →", interactive=True), gr.skip(), gr.skip())

    return handler


def _input_names(step):
    return [n for n in STEP_REQUIRED[step] if BY_ID[n]["kind"] != "pick"]


def _chips_upto(step):
    # a question can be revealed by a chip on an earlier page, so its answer counts here too
    return [cid for s in STEPS if s <= step for cid in chip_ids(s)]


def make_refresh_handler(step):
    names = _input_names(step) + _chips_upto(step)

    def refresh(attempted, *values):
        # only live-update once they've actually hit Next and been told what's missing
        if not attempted:
            return gr.skip(), gr.skip()
        problems = _step_problems(step, dict(zip(names, values)))
        key = _problem_key(problems)
        if key == attempted:
            return gr.skip(), gr.skip()   # same callout as already showing
        return callout_update(problems), key

    return refresh


# ── layout ────────────────────────────────────────────────────────────────────
def scene_html(q):
    """a scene-setter above a scenario question: a label, the setup, and optional chat bubbles."""
    rows = ""
    for i, (who, text) in enumerate(q.get("bubbles") or []):
        if text is None:
            # someone who saw it and said nothing
            rows += f'<div class="scenario-seen">seen by {who}</div>'
            continue
        name = f'<span class="bubble-name">{who}</span>' if who else ""
        # two-person scenes alternate sides, a group thread keeps everyone on the left
        side = " reply" if (i % 2 and not q.get("thread")) else ""
        rows += f'<div class="scenario-bubble{side}">{name}{text}</div>'
    thread = " thread" if q.get("thread") else ""
    bubble_html = f'<div class="scenario-bubbles{thread}">{rows}</div>' if rows else ""
    return f"""
    <div class="scenario">
      <div class="scenario-kicker">{q["kicker"]}</div>
      <div class="scenario-setup">{q["setup"]}</div>
      {bubble_html}
    </div>"""


# the photo step, in plain words for someone who has never heard of a classifier
PHOTO_INTRO_HTML = """
<div class="photo-intro">
  <div class="photo-title">your profile photo <span class="photo-optional">optional</span></div>
  <p class="photo-sub">use your instagram profile photo, or your favorite photo of yourself. pick the one you'd want people to see, since a random photo gives a random read.</p>
  <details class="why-photo">
    <summary>what is this photo needed for?</summary>
    <div class="why-body">
      <p><b>what it looks at.</b> a small program checks four things in the picture: the expression on your face, whether you're on your own or with other people, whether you're looking at the camera, and what's behind you (a party, outdoors, your room). people usually pick photos that match how they see themselves, so these are small clues about you.</p>
      <p><b>how much it counts.</b> very little. it only nudges two of the five stats, energy and empathy, and what you wrote counts for far more. skipping the photo works fine.</p>
      <p><b>is it saved?</b> no. the photo is used once, while your result is being made, and then it's deleted. it isn't stored, shared, or linked to your name, and it isn't sent to any other company. the checks run on this app's own server.</p>
    </div>
  </details>
</div>
"""


def _section(title, legend=True):
    tag = '<span class="req-legend">required</span>' if legend else ""
    return gr.HTML(f'<span class="section-label">{title}{tag}</span>')


def build_component(q):
    """one gradio input for one question in the registry."""
    kind = q["kind"]
    common = dict(
        label=q["label"],
        elem_id=f"f-{q['id']}",
        elem_classes=["req"] if q.get("required") else [],
    )
    if kind == "checks":
        return gr.CheckboxGroup(choices=q["choices"], info=q.get("info"), **common)
    if kind == "radio":
        return gr.Radio(choices=q["choices"], info=q.get("info"), **common)
    if kind == "msg":
        return gr.Textbox(
            lines=1, max_lines=4, scale=4, show_label=False, placeholder=q.get("placeholder"),
            **{**common, "elem_classes": common["elem_classes"] + ["composer-box"]},
        )
    if kind == "text":
        return gr.Textbox(
            placeholder=q.get("placeholder"), info=q.get("info"),
            lines=q.get("lines", 1), max_lines=q.get("max_lines", 8),
            **common,
        )
    if kind == "slider":
        # 0 is "not answered yet": it starts there so the slider has to be moved, even to land on 3
        return gr.Slider(minimum=0, maximum=5, step=1, value=0, info=q.get("info"), **common)
    if kind == "image":
        return gr.Image(
            show_label=False, type="filepath", sources=["upload"], height=190,
            placeholder="drop your photo here, or click to choose one",
            elem_classes=["photo-upload-wrap"],
        )
    raise ValueError(f"unknown question kind: {kind}")


def build_question(q):
    """lay out one question from the registry inside the current step."""
    if q["kind"] == "scene":
        gr.HTML(scene_html(q), elem_classes=[q["extra_class"]] if q.get("extra_class") else [])
        return
    if q["kind"] == "pick":
        # a row of pills, pick one
        gr.HTML(f'<div class="composer-label">{q["label"]}{"<i class=req-star></i>" if q.get("required") else ""}</div>')
        with gr.Row(elem_classes=["chip-row"], elem_id=f"f-{q['id']}"):
            for chip in q["chips"]:
                C[chip["id"]] = gr.Checkbox(label=chip["label"], elem_id=f"f-{chip['id']}", elem_classes=["read-chip"], container=False)
        return
    if q["kind"] == "msg":
        # a small phone-thread look: the text bar with a send arrow, and the
        # options beside it as chips
        gr.HTML(f'<div class="composer-label">{q["label"]}{"<i class=req-star></i>" if q.get("required") else ""}</div>')
        with gr.Column(elem_classes=["composer"]):
            C[q["id"]] = build_component(q)
            if q["chips"]:
                with gr.Row(elem_classes=["chip-row"]):
                    for chip in q["chips"]:
                        C[chip["id"]] = gr.Checkbox(label=chip["label"], elem_id=f"f-{chip['id']}", elem_classes=["read-chip"], container=False)
        return
    if q["kind"] == "image":
        gr.HTML(PHOTO_INTRO_HTML)
    C[q["id"]] = build_component(q)


C = {}
cond_cols = {}


def _conds(q):
    cond = q["show_if"]
    return [cond] if isinstance(cond, str) else list(cond)

with gr.Blocks(title="MBTI Radar", css=CSS, theme=theme, head=HEAD_JS) as demo:

    gr.HTML(f"""
    <div class="hero-scene">{hero_scene_svg()}</div>
    """, elem_classes=["flush-html", "tuck"])
    gr.HTML(f"""
    <div class="mbti-hero">
      <h1 class="hero-title">MBTI Radar</h1>
      {rules_block_html()}
    </div>
    """, elem_classes=["flush-html"])
    gr.HTML(how_it_works_html(), elem_classes=["flush-html", "tuck"])

    if DEV:
        with gr.Row(elem_classes=["dev-bar"]):
            dev_type = gr.Dropdown(choices=sorted(MBTI_DESCRIPTIONS), value="ENFJ", label="dev: type", scale=2)
            dev_finish = gr.Dropdown(choices=F.FINISH_IDS, value="common", label="dev: finish", scale=2)
            dev_btn = gr.Button("dev: jump to result", scale=2)

    # the landing page shows first. the quiz is already in the page, hidden by css until the button is pressed
    gr.HTML(landing_html(), elem_classes=["flush-html", "landing-page"])

    with gr.Column(elem_classes=["main-content", "quiz-page"]) as form_page:
        with gr.Row(elem_classes=["console"]):

            with gr.Column(elem_classes=["form-col"]):
                step_indicator = gr.HTML(step_indicator_html(1, TOTAL_STEPS), elem_classes=["step-indicator-wrap"])

                # set once a Next click has been blocked, so the callout and
                # field highlights then follow along as the answers get fixed
                attempted = {s: gr.State("") for s in STEPS if STEP_REQUIRED[s]}
                callouts, step_cols, back_btns, next_btns = {}, {}, {}, {}

                for s in STEPS:
                    with gr.Column(elem_classes=["step-col", f"step-{s}"]) as col:
                        step_cols[s] = col
                        with gr.Group(elem_classes=["mbti-card"]):
                            _section(STEP_TITLES[s], legend=bool(STEP_REQUIRED[s]))
                            qs = step_questions(s)
                            i = 0
                            while i < len(qs):
                                q = qs[i]
                                if q.get("show_if"):
                                    # a run of questions that only appear once a chip is ticked
                                    group = []
                                    for x in qs[i:]:
                                        if x.get("show_if") != q["show_if"]:
                                            break
                                        group.append(x)
                                    with gr.Column(elem_classes=["cond-col", q.get("panel", "")] + [f"cc-{c}" for c in _conds(q)]) as cond_col:
                                        for x in group:
                                            build_question(x)
                                    i += len(group)
                                elif q.get("reveal"):
                                    # hidden until what it waits on is done (see the flags in the head script)
                                    with gr.Column(elem_classes=["reveal-col", f"rv-{q['reveal']}"]):
                                        build_question(q)
                                    i += 1
                                else:
                                    build_question(q)
                                    i += 1
                        if STEP_REQUIRED[s]:
                            callouts[s] = gr.HTML("", visible=False, elem_classes=["need-wrap"])
                        if s == 1:
                            next_btns[s] = gr.Button("Next →", variant="primary", size="lg")
                        elif s == LAST_STEP:
                            with gr.Row(elem_classes=["nav-row"]):
                                back_btns[s] = gr.Button("← Back", variant="secondary")
                                submit_btn = gr.Button("open your type pack ↗", variant="primary", size="lg")
                        else:
                            with gr.Row(elem_classes=["nav-row"]):
                                back_btns[s] = gr.Button("← Back", variant="secondary")
                                next_btns[s] = gr.Button("Next →", variant="primary")

            with gr.Column(elem_classes=["live-col"]):
                with gr.Group(elem_classes=["mbti-card"]):
                    progress_panel = gr.HTML(empty_progress_html())

    with gr.Column(elem_classes=["main-content", "reveal-page-inner"], visible=False) as reveal_page:
        output = gr.HTML("")
        with gr.Row(elem_classes=["again-row"]):
            again_btn = gr.Button("↺ retake the quiz", size="sm", elem_id="retake-btn")
            home_btn = gr.Button("⌂ back to start", size="sm", elem_id="home-btn")

    # ── wiring ──
    for s in STEPS[:-1]:
        next_btns[s].click(
            fn=make_next_handler(s),
            inputs=[C[name] for name in CUM_NAMES[s]],
            outputs=[progress_panel, step_indicator, next_btns[s], callouts[s], attempted[s]],
            show_progress="hidden",
        )

    # once a Next has been blocked, the callout follows along as the answers get fixed
    for s in STEPS:
        if not STEP_REQUIRED[s]:
            continue
        refresh = make_refresh_handler(s)
        refresh_io = dict(
            fn=refresh,
            inputs=[attempted[s], *[C[n] for n in _input_names(s)], *[C[rid] for rid in _chips_upto(s)]],
            outputs=[callouts[s], attempted[s]],
            show_progress="hidden",
        )
        for name in _input_names(s) + chip_ids(s):
            C[name].change(**refresh_io)

    for s in STEPS:
        for q in step_questions(s):
            if q["kind"] not in ("pick", "msg") or not q["chips"]:
                continue
            # the pills act like a radio: ticking one clears the others
            ids = [c["id"] for c in q["chips"]]
            has_text = q["kind"] == "msg"   # a composer with chips also goes quiet when one is ticked
            # (the questions a pill reveals are shown by css, see the flags in the head script)
            for i, cid in enumerate(ids):
                def on_chip(*vals, i=i, has_text=has_text):
                    new = [vals[i] if j == i else (False if vals[i] else vals[j]) for j in range(len(vals))]
                    # only touch the pills that actually changed, so nothing else re-renders
                    out = [gr.skip() if new[j] == vals[j] else gr.update(value=new[j]) for j in range(len(vals))]
                    if has_text:
                        out = [gr.update(interactive=not any(new), value="" if any(new) else gr.skip())] + out
                    return out
                C[cid].change(fn=on_chip, inputs=[C[x] for x in ids],
                              outputs=([C[q["id"]]] if has_text else []) + [C[x] for x in ids],
                              show_progress="hidden", trigger_mode="always_last")

    for s in STEPS[1:]:
        back_btns[s].click(
            fn=lambda s=s: step_indicator_html(s - 1, TOTAL_STEPS),
            outputs=[step_indicator],
            show_progress="hidden",
        )

    def submit_handler(*values):
        data = dict(zip(ALL_FIELD_NAMES + ["photo"], values))
        problems = _step_problems(LAST_STEP, data)
        if problems:
            yield (gr.skip(),) * 4 + (callout_update(problems, fresh=True), _problem_key(problems))
            return
        for i, out in enumerate(run_prediction(*values)):
            yield tuple(out) + ((callout_update([]), "") if i == 0 else (gr.skip(), gr.skip()))

    submit_btn.click(
        fn=submit_handler,
        inputs=[C[name] for name in ALL_FIELD_NAMES] + [C["photo"]],
        outputs=[output, form_page, reveal_page, submit_btn, callouts[LAST_STEP], attempted[LAST_STEP]],
        show_progress="hidden",
    )

    def again_reset_pages():
        return gr.update(visible=True), gr.update(visible=False)  # form_page, reveal_page

    def again_reset_panels():
        return step_indicator_html(1, TOTAL_STEPS), empty_progress_html()

    # every answer goes back to blank. the steps are only hidden with css now, so
    # they can be written to freely (they used to be dropped from the page when hidden)
    RESET_VALUE = {"checks": list, "radio": lambda: None, "text": str, "msg": str, "slider": lambda: 0}
    RESET_IDS = [n for s in STEPS for n in STEP_NAMES[s] if n in BY_ID and BY_ID[n]["kind"] in RESET_VALUE]
    RESET_IDS += [c for s in STEPS for c in chip_ids(s)]
    reset_states = [attempted[s] for s in STEPS if s in attempted]

    def again_reset_fields():
        blank = [(False if n not in BY_ID else RESET_VALUE[BY_ID[n]["kind"]]()) for n in RESET_IDS]
        return blank + [None] + [""] * len(reset_states)   # photo, callout states

    # retake wipes every answer and goes back to the quiz. back to start does the same wipe, then shows the landing page
    def wire_reset(btn, js=None):
        extra = {"js": js} if js else {}
        btn.click(
            fn=again_reset_pages, outputs=[form_page, reveal_page], show_progress="hidden", **extra,
        ).then(
            fn=again_reset_panels, outputs=[step_indicator, progress_panel], show_progress="hidden",
        ).then(
            fn=again_reset_fields,
            outputs=[C[n] for n in RESET_IDS] + [C["photo"]] + reset_states,
            show_progress="hidden",
        )

    wire_reset(again_btn)
    wire_reset(home_btn, js="() => { document.body.classList.remove('started'); window.scrollTo({ top: 0 }); }")

if DEV:
    # a made up read for whichever type was picked, so the result page has real looking numbers on it
    def _fake_read(code):
        letters = list(code) + [random.choice("AT")]
        read = {}
        for (key, _name, outward, _color, _icon), win in zip(SPOKES, letters):
            conf = random.randint(56, 92)
            read[key] = {"winner": win, "confidence": conf,
                         "scores": {outward: conf if win == outward else 100 - conf},
                         "is_ambiguous": conf < 62}
        return f"{code}-{letters[4]}", read

    def dev_jump(code, finish):
        mbti_type, read = _fake_read(code)
        return build_reveal_html(mbti_type, read, finish), gr.update(visible=False), gr.update(visible=True)

    with demo:
        dev_btn.click(fn=dev_jump, inputs=[dev_type, dev_finish], outputs=[output, form_page, reveal_page], show_progress="hidden",
                      js="(t, f) => { window.mbtiStart && mbtiStart(); return [t, f]; }")

if __name__ == "__main__":
    demo.launch(share=False, favicon_path="favicon.svg")
