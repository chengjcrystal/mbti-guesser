/*
 sprites.js: the 16 type characters, drawn in the browser.

 each one is a small pixel grid with a dark outline and three shades per
 color (light, base, dark) so it reads like an old handheld sprite. any
 <canvas data-sprite="ENFP"> that shows up on the page gets drawn, which is
 how the result card gets its character after gradio swaps the html in.
*/
(function () {
/* ---------- tiny pixel engine ---------- */
const N = 36, OX = 2, OY = 4; // a little headroom above the 32px body so crests and plumes are never clipped
const OUT = '#2b2140';
const DARKK = '#2b2140';

function tone(hex, f) {
  const c = parseInt(hex.slice(1), 16);
  let r = c >> 16, g = (c >> 8) & 255, b = c & 255;
  const t = f > 0 ? 255 : 0, a = Math.abs(f);
  const m = (v) => Math.round(v + (t - v) * a);
  return `rgb(${m(r)},${m(g)},${m(b)})`;
}

class Sprite {
  constructor(pal) {
    this.pal = pal;
    this.g = Array.from({ length: N }, () => Array(N).fill(null));
  }
  set(x, y, m, t = 1) {
    x = Math.round(x) + OX; y = Math.round(y) + OY;
    if (x < 0 || y < 0 || x >= N || y >= N) return;
    this.g[y][x] = { m, t };
  }
  shadeAt(d, x, y) {
    // d runs about -1 (top-left) to 1 (bottom-right). two dithered edges give the DS-era three-tone look
    const hi = 0.30, lo = -0.42;
    const chk = (x + y) % 2 === 0;
    if (d > hi + 0.07) return 0;
    if (d > hi - 0.07) return chk ? 0 : 1;
    if (d < lo - 0.07) return 2;
    if (d < lo + 0.07) return chk ? 2 : 1;
    return 1;
  }
  ell(cx, cy, rx, ry, m, o = {}) {
    for (let y = Math.floor(cy - ry - 1); y <= Math.ceil(cy + ry + 1); y++)
      for (let x = Math.floor(cx - rx - 1); x <= Math.ceil(cx + rx + 1); x++) {
        const dx = (x - cx) / rx, dy = (y - cy) / ry;
        if (dx * dx + dy * dy <= 1) this.set(x, y, m, o.flat ? 1 : this.shadeAt((dx + dy) / 2, x, y));
      }
  }
  rect(x0, y0, w, h, m, o = {}) {
    for (let y = y0; y < y0 + h; y++)
      for (let x = x0; x < x0 + w; x++) {
        const dx = (x - (x0 + w / 2 - 0.5)) / (w / 2), dy = (y - (y0 + h / 2 - 0.5)) / (h / 2);
        this.set(x, y, m, o.flat ? 1 : this.shadeAt((dx + dy) / 2, x, y));
      }
  }
  poly(pts, m, o = {}) {
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = (x1 - x0) / 2 || 1, ry = (y1 - y0) / 2 || 1;
    for (let y = y0; y <= y1; y++)
      for (let x = x0; x <= x1; x++) {
        let inside = false;
        for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
          const [xi, yi] = pts[i], [xj, yj] = pts[j];
          if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
        }
        if (inside) this.set(x, y, m, o.flat ? 1 : this.shadeAt(((x - cx) / rx + (y - cy) / ry) / 2, x, y));
      }
  }
  line(x0, y0, x1, y1, m, th = 1, t = 1) {
    const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) || 1;
    for (let i = 0; i <= n; i++) {
      const x = x0 + (x1 - x0) * i / n, y = y0 + (y1 - y0) * i / n;
      for (let a = 0; a < th; a++) for (let b = 0; b < th; b++) this.set(x + a, y + b, m, t);
    }
  }
  px(list, m, t = 1) { list.forEach(([x, y]) => this.set(x, y, m, t)); }

  // shared face bits
  eyeDot(x, y) { this.rect(x, y, 2, 3, 'k', { flat: true }); this.set(x, y, 'e', 1); }
  eyeBig(x, y) { this.rect(x, y, 4, 4, 'e', { flat: true }); this.rect(x + 1, y + 1, 2, 3, 'k', { flat: true }); this.set(x + 1, y + 1, 'e', 1); }
  eyeSleep(x, y, w = 3) { for (let i = 0; i < w; i++) this.set(x + i, y + (i === 1 ? 1 : 0), 'k', 1); }
  eyeSharp(x, y, dir) { this.rect(x, y + 1, 3, 2, 'k', { flat: true }); this.set(dir > 0 ? x + 2 : x, y, 'k', 1); this.set(dir > 0 ? x + 1 : x + 1, y, 'k', 1); }
  cheeks(x1, x2, y) { this.rect(x1, y, 2, 1, 'p', { flat: true }); this.rect(x2, y, 2, 1, 'p', { flat: true }); }

  render(cv, scale = 7) {
    const P = this.pal, S = N * scale;
    cv.width = S; cv.height = S;
    const c = cv.getContext('2d');
    c.clearRect(0, 0, S, S);
    // ground shadow
    c.fillStyle = 'rgba(43,33,64,.22)';
    c.beginPath(); c.ellipse((16 + OX) * scale, (29.2 + OY) * scale, 8.5 * scale, 1.7 * scale, 0, 0, Math.PI * 2); c.fill();
    const colorOf = (cell) => {
      if (cell.m === 'k') return DARKK;
      if (cell.m === 'e') return '#ffffff';
      if (cell.m === 'p') return '#f29ab0';
      const base = P[cell.m] || '#888888';
      return cell.t === 0 ? tone(base, -0.30) : cell.t === 2 ? tone(base, 0.32) : base;
    };
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const cell = this.g[y][x];
      if (cell) { c.fillStyle = colorOf(cell); c.fillRect(x * scale, y * scale, scale, scale); }
    }
    // outline: any empty pixel touching a filled one (4-neighbour)
    c.fillStyle = OUT;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      if (this.g[y][x]) continue;
      const n = (yy, xx) => yy >= 0 && xx >= 0 && yy < N && xx < N && this.g[yy][xx];
      if (n(y - 1, x) || n(y + 1, x) || n(y, x - 1) || n(y, x + 1)) c.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}

/* ---------- the 16 species ---------- */
const SP = {};

SP.INTJ = () => { // owl with a crest gem
  const s = new Sprite({ b: '#5A5BA8', d: '#40417F', a: '#F2C14E', w: '#DAD8F2', g: '#6FE0D0' });
  s.ell(7.5, 20, 3, 7.5, 'd'); s.ell(24.5, 20, 3, 7.5, 'd');
  s.ell(16, 19.5, 8.5, 9, 'b');
  s.ell(16, 22.5, 5.5, 6, 'w');
  [[14, 20], [15, 21], [16, 20], [17, 21], [18, 20], [14, 24], [15, 25], [16, 24], [17, 25], [18, 24]].forEach(([x, y]) => s.set(x, y, 'd', 1));
  s.ell(16, 12.5, 8.5, 6.5, 'b');
  s.poly([[8, 9], [7, 3], [13, 8]], 'd'); s.poly([[24, 9], [25, 3], [19, 8]], 'd');
  s.ell(12, 12, 4, 4, 'w', { flat: true }); s.ell(20, 12, 4, 4, 'w', { flat: true });
  s.eyeBig(10, 10); s.eyeBig(18, 10);
  s.poly([[15, 14], [17, 14], [16, 17]], 'a', { flat: true });
  s.line(16, 8, 16, 6, 'a'); s.ell(16, 4.5, 1.6, 1.6, 'g', { flat: true });
  s.rect(11, 28, 3, 1, 'a', { flat: true }); s.rect(18, 28, 3, 1, 'a', { flat: true });
  return s;
};

SP.INTP = () => { // ghostly cloud with three orbiting orbs
  const s = new Sprite({ b: '#8F8CE3', a: '#6FE0D0', w: '#EDEBFF', o: '#F2C14E' });
  s.ell(16, 16, 10.5, 10, 'b');
  for (let i = 0; i < 4; i++) s.ell(9 + i * 4.6, 25.5 + (i % 2 ? 0 : 0.8), 2.6, 2.6 + (i % 2), 'b');
  s.ell(16, 19, 7, 5.5, 'w');
  s.eyeSleep(9, 14, 4); s.eyeSleep(19, 14, 4);
  s.rect(9, 12, 4, 1, 'k', { flat: true }); s.rect(19, 12, 4, 1, 'k', { flat: true });
  s.rect(15, 19, 2, 1, 'k', { flat: true });
  s.ell(4.5, 8, 2.3, 2.3, 'a', { flat: true }); s.ell(27.5, 10, 2, 2, 'o', { flat: true }); s.ell(24.5, 3.5, 1.6, 1.6, 'a', { flat: true });
  s.line(3, 5, 4, 5, 'w'); s.line(1, 12, 2, 12, 'w');
  return s;
};

SP.ENTJ = () => { // lion with a crown mane
  const s = new Sprite({ m: '#C2453D', b: '#E5AC5E', w: '#F7E5BC', a: '#F2C14E' });
  s.ell(16, 15.5, 12.5, 12, 'm');
  for (let i = 0; i < 5; i++) s.poly([[6 + i * 5, 6], [8 + i * 5, 0 + (i % 2 ? 2 : 0)], [10 + i * 5, 6]], 'm');
  s.ell(16, 22, 7, 6.5, 'b');
  s.ell(16, 17, 8, 7.5, 'b');
  s.ell(9, 9, 2.6, 2.6, 'b', { flat: true }); s.ell(23, 9, 2.6, 2.6, 'b', { flat: true });
  s.ell(16, 20, 4.5, 3.4, 'w');
  s.eyeSharp(10, 14, 1); s.eyeSharp(19, 14, -1);
  s.poly([[15, 18], [17, 18], [16, 19.5]], 'k', { flat: true });
  s.px([[14, 21], [15, 22], [16, 22], [17, 22], [18, 21]], 'k');
  s.rect(9, 27, 4, 2, 'b'); s.rect(19, 27, 4, 2, 'b');
  s.poly([[13, 3], [16, 0], [19, 3], [16, 5]], 'a', { flat: true });
  return s;
};

SP.ENTP = () => { // fox with a lightning tail
  const s = new Sprite({ b: '#E27F3A', w: '#FBEBD0', a: '#F7D23E', d: '#8B4A24' });
  s.poly([[22, 25], [30, 19], [26, 16], [31, 8], [24, 12], [26, 15], [20, 22]], 'a');
  s.ell(16, 21, 7.5, 7, 'b'); s.ell(16, 23, 4.5, 5, 'w');
  s.ell(16, 13, 8.5, 6.5, 'b');
  s.poly([[8, 10], [7, 2], [14, 8]], 'b'); s.poly([[24, 10], [25, 2], [18, 8]], 'b');
  s.poly([[9, 9], [9, 5], [12, 8]], 'd', { flat: true }); s.poly([[23, 9], [23, 5], [20, 8]], 'd', { flat: true });
  s.ell(16, 16.5, 5.5, 3.4, 'w');
  s.eyeDot(11, 12); s.eyeDot(19, 12);
  s.rect(10, 10, 4, 1, 'k', { flat: true }); s.rect(18, 9, 4, 1, 'k', { flat: true });
  s.px([[15, 16], [16, 16]], 'k'); s.px([[14, 18], [15, 19], [16, 19], [17, 19], [18, 18], [19, 17]], 'k');
  s.rect(10, 27, 3, 2, 'd'); s.rect(19, 27, 3, 2, 'd');
  return s;
};

SP.INFJ = () => { // deer with glowing antlers and a moon mark
  const s = new Sprite({ b: '#B9D2A4', w: '#F1F5DD', a: '#7FE6CB', d: '#6B8F5C', g: '#F2E58A' });
  s.line(11, 8, 8, 3, 'a', 1); s.line(8, 3, 6, 2, 'a', 1); s.line(9, 5, 11, 3, 'a', 1);
  s.line(21, 8, 24, 3, 'a', 1); s.line(24, 3, 26, 2, 'a', 1); s.line(23, 5, 21, 3, 'a', 1);
  s.ell(16, 21.5, 7.5, 6.5, 'b'); s.ell(16, 23, 4, 4.5, 'w');
  s.rect(10, 26, 3, 3, 'b'); s.rect(19, 26, 3, 3, 'b');
  s.ell(16, 13.5, 7.5, 6.5, 'b');
  s.ell(8.5, 11, 3, 1.8, 'b'); s.ell(23.5, 11, 3, 1.8, 'b');
  s.ell(16, 17, 4, 2.6, 'w');
  s.eyeSleep(11, 13, 3); s.eyeSleep(18, 13, 3);
  s.px([[15, 16], [16, 16]], 'k');
  s.px([[16, 9], [15, 10], [15, 11], [16, 12], [17, 11]], 'g', 1); s.set(17, 10, 'b', 1);
  s.px([[4, 6], [27, 5], [3, 12], [28, 13]], 'g');
  return s;
};

SP.INFP = () => { // dreamy bunny with butterfly wings
  const s = new Sprite({ b: '#F3D9E8', w: '#FFFFFF', a: '#C7B4F0', d: '#B98BC9', g: '#F2E58A' });
  s.ell(6.5, 17, 5, 6.5, 'a'); s.ell(25.5, 17, 5, 6.5, 'a');
  s.px([[5, 16], [6, 18], [4, 19], [26, 16], [25, 18], [27, 19]], 'w');
  s.ell(16, 21, 7, 6.5, 'b'); s.ell(16, 23, 4, 4, 'w');
  s.ell(16, 13, 7.5, 6.5, 'b');
  s.ell(10.5, 4.5, 2.4, 6.2, 'b'); s.ell(21.5, 4.5, 2.4, 6.2, 'b');
  s.ell(10.5, 5.5, 1.1, 4, 'a', { flat: true }); s.ell(21.5, 5.5, 1.1, 4, 'a', { flat: true });
  s.eyeBig(10, 12); s.eyeBig(18, 12);
  s.set(13, 13, 'g', 1); s.set(21, 13, 'g', 1);
  s.cheeks(8, 22, 17);
  s.px([[15, 17], [16, 17]], 'k'); s.px([[15, 18], [16, 19], [17, 18]], 'k');
  s.rect(11, 27, 3, 2, 'w'); s.rect(18, 27, 3, 2, 'w');
  return s;
};

SP.ENFJ = () => { // songbird with a sun crest, mid-song
  const s = new Sprite({ b: '#F6C453', w: '#FDEBB6', a: '#F08A5D', d: '#C58A22' });
  s.ell(16, 20, 9, 8, 'b'); s.ell(16, 22, 5.5, 5.5, 'w');
  s.ell(6, 19, 3.6, 5.5, 'd'); s.ell(26, 19, 3.6, 5.5, 'd');
  s.poly([[13, 27], [16, 30], [19, 27]], 'a', { flat: true });
  s.ell(16, 11.5, 7.5, 6.5, 'b');
  s.poly([[12, 6], [10, 0], [14, 4]], 'a'); s.poly([[16, 5], [16, -1], [17, 5]], 'a'); s.poly([[20, 6], [22, 0], [18, 4]], 'a');
  s.eyeDot(11, 10); s.eyeDot(19, 10);
  s.cheeks(8, 22, 14);
  s.poly([[13, 13], [19, 13], [16, 15]], 'a', { flat: true });
  s.rect(14, 15, 4, 2, 'k', { flat: true }); s.px([[15, 16], [16, 16]], 'p');
  s.px([[4, 8], [27, 6], [2, 13], [29, 12]], 'a');
  s.rect(11, 28, 3, 1, 'a', { flat: true }); s.rect(18, 28, 3, 1, 'a', { flat: true });
  return s;
};

SP.ENFP = () => { // puppy with confetti and a wagging tail
  const s = new Sprite({ b: '#F1A65B', w: '#FCE8C8', d: '#B9682B', a: '#F2607B', c: '#5FC9E0', y: '#F7D23E' });
  s.line(24, 24, 28, 17, 'b', 2); s.line(28, 17, 27, 14, 'b', 2);
  s.px([[30, 15], [31, 18], [30, 21]], 'y');
  s.ell(16, 21.5, 8, 7, 'b'); s.ell(16, 23, 4.5, 5, 'w');
  s.ell(16, 13.5, 8.5, 7, 'b');
  s.ell(6.5, 15, 3, 6, 'd'); s.ell(25.5, 15, 3, 6, 'd');
  s.ell(16, 17.5, 5.5, 3.6, 'w');
  s.eyeDot(11, 11.5); s.eyeDot(19, 11.5);
  s.poly([[14, 15], [18, 15], [16, 17]], 'k', { flat: true });
  s.line(16, 17, 16, 18, 'k'); s.px([[13, 18], [14, 19], [18, 19], [19, 18]], 'k');
  s.rect(15, 19, 3, 3, 'a', { flat: true });
  s.cheeks(8, 22, 16);
  s.px([[3, 4], [8, 2], [24, 3], [28, 6]], 'c'); s.px([[5, 8], [27, 9], [12, 1], [20, 1]], 'a'); s.px([[2, 10], [29, 3]], 'y');
  s.rect(10, 27, 4, 2, 'w'); s.rect(18, 27, 4, 2, 'w');
  return s;
};

SP.ISTJ = () => { // turtle with a tiled shell
  const s = new Sprite({ b: '#5E8F7B', h: '#A9CBA0', d: '#3F6656', a: '#E5D9A0' });
  s.ell(16, 20, 12.5, 9, 'b');
  for (let x = 6; x <= 26; x += 5) s.line(x, 13, x, 27, 'd');
  for (let y = 15; y <= 25; y += 5) s.line(5, y, 27, y, 'd');
  s.ell(16, 14, 8, 3, 'b', { flat: true });
  s.ell(16, 8.5, 6, 5.5, 'h');
  s.rect(9, 5, 1, 1, 'h', { flat: true });
  s.rect(9, 8, 5, 1, 'a', { flat: true }); s.rect(18, 8, 5, 1, 'a', { flat: true }); s.rect(14, 8, 4, 1, 'a', { flat: true });
  s.eyeDot(12, 6); s.eyeDot(19, 6);
  s.px([[15, 11], [16, 11], [17, 11]], 'k');
  s.rect(6, 27, 5, 2, 'h'); s.rect(21, 27, 5, 2, 'h');
  return s;
};

SP.ISFJ = () => { // bear cub with a heart shield
  const s = new Sprite({ b: '#C9A27E', w: '#F0DEC2', d: '#8F6B48', a: '#6E9B96', h: '#F29AB0' });
  s.ell(16, 21, 8.5, 7.5, 'b'); s.ell(6.5, 21, 3, 4.5, 'b'); s.ell(25.5, 21, 3, 4.5, 'b');
  s.poly([[11, 17], [21, 17], [21, 24], [16, 29], [11, 24]], 'a');
  s.px([[13, 20], [14, 20], [18, 20], [19, 20]], 'h', 1); s.rect(13, 21, 7, 2, 'h', { flat: true }); s.rect(14, 23, 5, 1, 'h', { flat: true }); s.set(16, 24, 'h', 1);
  s.ell(16, 12, 8, 6.8, 'b');
  s.ell(9, 6, 3, 3, 'b'); s.ell(23, 6, 3, 3, 'b'); s.ell(9, 6, 1.4, 1.4, 'd', { flat: true }); s.ell(23, 6, 1.4, 1.4, 'd', { flat: true });
  s.ell(16, 15, 4.6, 3.4, 'w');
  s.eyeDot(11, 10); s.eyeDot(19, 10);
  s.poly([[15, 13], [17, 13], [16, 14.5]], 'k', { flat: true });
  s.px([[14, 16], [15, 17], [16, 17], [17, 17], [18, 16]], 'k');
  s.cheeks(8, 22, 14);
  s.rect(10, 28, 4, 1, 'd', { flat: true }); s.rect(18, 28, 4, 1, 'd', { flat: true });
  return s;
};

SP.ESTJ = () => { // bulldog with a tie and badge
  const s = new Sprite({ b: '#B5A08A', w: '#E9DCCB', d: '#7A6A58', a: '#D24B4B', g: '#F2C14E' });
  s.ell(16, 21, 10, 7.5, 'b'); s.ell(6, 21, 2.6, 5, 'b'); s.ell(26, 21, 2.6, 5, 'b');
  s.poly([[14, 17], [18, 17], [19, 20], [16, 27], [13, 20]], 'a', { flat: true });
  s.rect(9, 20, 3, 3, 'g', { flat: true }); s.set(10, 21, 'd', 1);
  s.ell(16, 12.5, 9.5, 6.8, 'b');
  s.poly([[7, 9], [5, 14], [10, 12]], 'd'); s.poly([[25, 9], [27, 14], [22, 12]], 'd');
  s.ell(16, 17, 6.5, 4, 'w');
  s.ell(11, 18, 3, 2.6, 'w'); s.ell(21, 18, 3, 2.6, 'w');
  s.px([[12, 19], [20, 19]], 'e');
  s.rect(9, 9, 5, 1, 'k', { flat: true }); s.rect(18, 9, 5, 1, 'k', { flat: true }); s.set(13, 10, 'k', 1); s.set(18, 10, 'k', 1);
  s.eyeDot(10, 11); s.eyeDot(20, 11);
  s.rect(14, 14, 4, 2, 'k', { flat: true });
  s.px([[12, 19], [13, 20], [14, 20], [17, 20], [18, 20], [19, 19]], 'k'); s.px([[12, 20], [20, 20]], 'w');
  s.rect(9, 28, 4, 1, 'd', { flat: true }); s.rect(19, 28, 4, 1, 'd', { flat: true });
  return s;
};

SP.ESFJ = () => { // penguin in a scarf, waving
  const s = new Sprite({ b: '#3F4C73', w: '#F4F1E8', a: '#E0645C', o: '#F2A950' });
  s.ell(16, 19, 9.5, 10, 'b'); s.ell(16, 21.5, 6.2, 7.5, 'w');
  s.ell(6, 19, 2.8, 6, 'b'); s.line(26, 12, 29, 7, 'b', 3);
  s.ell(16, 11, 8, 6.2, 'b'); s.ell(16, 13.5, 5.5, 4, 'w');
  s.rect(7, 15, 18, 3, 'a'); s.rect(20, 17, 3, 6, 'a'); s.px([[20, 23], [22, 23]], 'a');
  s.eyeBig(11, 8); s.eyeBig(17, 8);
  s.poly([[14, 12], [18, 12], [16, 14]], 'o', { flat: true });
  s.cheeks(8, 22, 12);
  s.rect(10, 28, 4, 1, 'o', { flat: true }); s.rect(18, 28, 4, 1, 'o', { flat: true });
  return s;
};

SP.ISTP = () => { // raccoon tinkerer with goggles and a wrench tail
  const s = new Sprite({ b: '#7A7F93', w: '#E5E3EA', d: '#3F4256', a: '#F2C14E', m: '#9AA3B8' });
  s.line(24, 26, 29, 19, 'm', 3); s.rect(27, 15, 4, 4, 'm', { flat: true }); s.rect(28, 15, 2, 2, 'd', { flat: true });
  s.ell(16, 21, 7.5, 7, 'b'); s.ell(16, 23, 4.2, 4.8, 'w');
  s.ell(16, 13, 8.5, 6.8, 'b');
  s.poly([[8, 9], [8, 2], [13, 7]], 'b'); s.poly([[24, 9], [24, 2], [19, 7]], 'b');
  s.rect(8, 11, 16, 4, 'd', { flat: true }); s.eyeDot(11, 12); s.eyeDot(19, 12);
  s.set(12, 12, 'e', 1); s.set(20, 12, 'e', 1);
  s.rect(9, 3, 14, 3, 'a', { flat: true }); s.rect(10, 4, 5, 1, 'd', { flat: true }); s.rect(17, 4, 5, 1, 'd', { flat: true });
  s.ell(16, 17, 3.6, 2.6, 'w');
  s.px([[15, 16], [16, 16]], 'k'); s.px([[15, 18], [16, 18], [17, 18]], 'k');
  s.rect(10, 27, 3, 2, 'd'); s.rect(19, 27, 3, 2, 'd');
  return s;
};

SP.ISFP = () => { // chameleon with a flower and a curled tail
  const s = new Sprite({ b: '#8CC58A', w: '#E6F2B0', d: '#4F8B5C', a: '#F2607B', y: '#F7D23E' });
  s.ell(24, 25, 6, 4.5, 'b'); s.ell(24, 25, 3.2, 2.2, 'w', { flat: true }); s.ell(24, 25, 1.4, 1.2, 'b', { flat: true });
  s.ell(15, 21, 9, 6.5, 'b'); s.ell(15, 23.5, 6, 3.5, 'w');
  s.line(8, 19, 6, 26, 'b', 2); s.line(20, 26, 21, 28, 'b', 2);
  s.ell(14, 12.5, 8.5, 7, 'b');
  s.ell(9, 8, 3.4, 3.4, 'b'); s.ell(9, 8, 2, 2, 'e', { flat: true }); s.eyeDot(9, 7);
  s.ell(20, 8, 3.4, 3.4, 'b'); s.ell(20, 8, 2, 2, 'e', { flat: true }); s.eyeDot(19, 7);
  s.px([[11, 16], [12, 17], [13, 17], [14, 17], [15, 17], [16, 16]], 'k');
  s.px([[10, 12], [11, 12], [17, 12], [18, 12]], 'd');
  [[14, 3], [13, 4], [15, 4], [14, 5], [12, 3], [16, 3], [14, 2]].forEach(([x, y]) => s.set(x, y, 'a', 1)); s.set(14, 4, 'y', 1);
  s.rect(9, 27, 4, 2, 'd'); s.rect(17, 27, 4, 2, 'd');
  return s;
};

SP.ESTP = () => { // gecko in sunglasses with a gold chain
  const s = new Sprite({ b: '#4FB6C8', w: '#D8F2F3', d: '#2F7F92', a: '#F2C14E' });
  s.poly([[22, 26], [30, 22], [31, 27], [24, 29]], 'b');
  s.ell(16, 20.5, 8.5, 7.5, 'b'); s.ell(16, 23, 5, 5, 'w');
  s.poly([[10, 6], [12, 1], [14, 5], [16, 0], [18, 5], [20, 1], [22, 6]], 'd');
  s.ell(16, 12, 9.5, 6.5, 'b');
  s.rect(7, 9, 8, 4, 'k', { flat: true }); s.rect(17, 9, 8, 4, 'k', { flat: true }); s.rect(15, 10, 2, 1, 'k', { flat: true });
  s.px([[8, 10], [9, 10], [18, 10], [19, 10]], 'e');
  s.px([[11, 16], [12, 17], [13, 17], [14, 17], [15, 17], [16, 17], [17, 17], [18, 16], [19, 15]], 'k');
  s.px([[9, 20], [10, 21], [12, 22], [14, 23], [16, 23], [18, 23], [20, 22], [22, 21], [23, 20]], 'a');
  s.ell(16, 25.5, 1.6, 1.6, 'a', { flat: true });
  s.ell(6, 22, 2.6, 2.4, 'b'); s.ell(26, 22, 2.6, 2.4, 'b');
  s.rect(9, 27, 4, 2, 'd'); s.rect(19, 27, 4, 2, 'd');
  return s;
};

SP.ESFP = () => { // parrot with a party plume
  const s = new Sprite({ b: '#E85D75', w: '#FBD6DC', d: '#A93450', a: '#F7D23E', c: '#5FC9E0', g: '#7FD08A', o: '#F2A950' });
  s.poly([[22, 26], [26, 30], [24, 24]], 'c'); s.poly([[20, 27], [21, 31], [23, 26]], 'g');
  s.ell(6.5, 19, 4, 7, 'd'); s.ell(25.5, 19, 4, 7, 'd');
  s.ell(16, 20, 8.5, 8, 'b'); s.ell(16, 22, 5, 5.5, 'w');
  s.ell(16, 11.5, 7.8, 6.5, 'b');
  [['a', 9, 5, 10, -1], ['c', 13, 4, 13, -2], ['g', 16, 4, 16, -3], ['o', 19, 4, 19, -2], ['c', 23, 5, 22, -1]].forEach(([m, x1, y1, x2, y2]) => { s.line(x1, y1, x2, y2, m, 2); });
  s.ell(11.5, 10.5, 2.6, 2.6, 'e', { flat: true }); s.ell(20.5, 10.5, 2.6, 2.6, 'e', { flat: true });
  [[11, 9], [11, 10], [11, 11], [10, 10], [12, 10], [20, 9], [20, 10], [20, 11], [19, 10], [21, 10]].forEach(([x, y]) => s.set(x, y, 'k', 1));
  s.poly([[13, 13], [19, 13], [16, 18]], 'o', { flat: true }); s.px([[15, 14], [16, 14]], 'a');
  s.cheeks(7, 23, 14);
  s.px([[3, 4], [28, 3], [2, 11], [29, 10]], 'a'); s.px([[5, 1], [26, 1]], 'c');
  s.rect(11, 28, 3, 1, 'a', { flat: true }); s.rect(18, 28, 3, 1, 'a', { flat: true });
  return s;
};

/* ---------- hooking it into the page ---------- */
window.mbtiSprites = SP;

function drawAll() {
  document.querySelectorAll('canvas[data-sprite]:not([data-drawn])').forEach(function (cv) {
    var make = SP[cv.getAttribute('data-sprite')];
    if (!make) return;
    make().render(cv, 7);
    cv.setAttribute('data-drawn', '1');
  });
}
new MutationObserver(drawAll).observe(document.documentElement, { childList: true, subtree: true });
drawAll();
})();
