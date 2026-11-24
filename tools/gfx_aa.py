# -*- coding: utf-8 -*-
r"""8bpp(SELTTL) 그림 글자 «부드러운 가장자리» 한글판 (2026-11-24, 하스피 «메뉴 글자 원본의 고급스런 느낌·폰트 다 날아감»)
  원본 = 가는 붓 느낌 고딕, 흰 몸통 + 회색 단계 가장자리 + 검은 1픽셀 테두리.
  4배로 그려 줄인 덮음 비율 a(0~1) → 색 = 몸통·테두리 RGB 를 a 로 섞은 뒤 «원본이 쓰는 색번호» 중 가장 가까운 것.
  테두리 범위 = a 를 1픽셀 넓힌 것. 그 밖 = 원본 바탕(0 또는 판).
  render(idx, text, rgbpal, font, rows) → 새 색번호 배열
  python tools/gfx_aa.py 비교   → work/gfx_preview/메뉴_글꼴비교.png (글꼴 후보 나란히)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
FONTS = {'주아': r'C:/claude/utils/font/jua/Jua-Regular.ttf', '도현': r'C:/claude/utils/font/dohyeon/DoHyeon-Regular.ttf',
         '연성': r'C:/claude/utils/font/yeonsung/YeonSung-Regular.ttf', '맑은고딕굵게': r'C:/Windows/Fonts/malgunbd.ttf',
         '나눔고딕굵게': r'C:/claude/utils/font/nanum-gothic/NanumGothicBold.ttf'}
S = 4
BOLD = 0.02          # 획 두께 보탬(4배 그림 글꼴 크기 비율) — 연성은 가늘어 작은 크기에서 흐려짐. 0.05 는 뭉침(2026-11-24)
MIRROR = {'⇐': '⇒'}   # 연성·맑은 고딕에 없는 글자 → 반대 화살표를 좌우로 뒤집어 그림
GAPMAX = 0.15        # 글자 사이 최대 벌림(글자 높이 비율) — 한글이 일본어보다 좁아 원본 폭을 채우려고


def coverage(text, font, bw, bh, spans=None):
    """bw×bh 안에 맞춘 덮음 비율(0~1). 글자마다 따로 그려(같은 기준선·같은 크기) 원본 폭에 맞게 사이를 벌림.
    넘치면 가로만 좁힘. 공백 = 글자 높이 0.35."""
    fs = bh * S * 2; f = ImageFont.truetype(font, fs); sw = max(1, round(fs * BOLD))
    asc, desc = f.getmetrics(); Hc = asc + desc + 2 * sw
    cells = []
    for ch in text:
        if ch == ' ': cells.append(None); continue
        im = Image.new('L', (fs * 2, Hc), 0); ImageDraw.Draw(im).text((sw, sw), MIRROR.get(ch, ch), font=f, fill=255, stroke_width=sw, stroke_fill=255)
        if ch in MIRROR: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        bb = im.getbbox(); cells.append(im.crop((bb[0], 0, bb[2], Hc)) if bb else None)
    ink = [c for c in cells if c is not None]
    top = min(c.getbbox()[1] for c in ink); bot = max(c.getbbox()[3] for c in ink)
    sc = bh / (bot - top)                                                    # 4배 그림 → 실제 크기 배율
    ws = [c.width * sc if c is not None else bh * 0.35 for c in cells]
    nat = sum(ws); n = len(cells)
    gap = min(GAPMAX * bh, (bw - nat) / (n - 1)) if n > 1 and nat < bw else 0
    tot = nat + gap * (n - 1); sx = min(1.0, bw / tot)                      # 넘치면 가로만 좁힘
    W = max(1, int(round(tot * sx))); out = np.zeros((bh, W)); x = 0.0
    for c, w in zip(cells, ws):
        if c is not None:
            cw = max(1, int(round(w * sx)))
            a = np.asarray(c.crop((0, top, c.width, bot)).resize((cw, bh), Image.LANCZOS), float) / 255
            x0 = int(round(x)); x1 = min(W, x0 + cw); out[:, x0:x1] = np.maximum(out[:, x0:x1], a[:, :x1 - x0])
            if spans is not None: spans.append((x0, x1))
        elif spans is not None: spans.append(None)
        x += (w + gap) * sx
    return out


def render(idx, text, rgbpal, font, rows=True, body_idx=None, align='c'):
    H, W = idx.shape
    border = np.concatenate([idx[0], idx[-1], idx[:, 0], idx[:, -1]])
    bg = int(np.bincount(border, minlength=256).argmax())
    tx = (idx != bg) & (idx != 0)
    ys, xs = np.nonzero(tx); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    used = sorted(set(idx[tx].ravel().tolist()))
    light = bg != 0 and float(rgbpal[bg].astype(float) @ [0.3, 0.59, 0.11]) > float(np.median(rgbpal[idx[tx]].astype(float) @ [0.3, 0.59, 0.11]))
    if light: used = sorted(set(used) | {bg})
    if body_idx is not None: used = sorted(set(used) | {body_idx})     # 무리 통일 몸통 색(원본에 없던 번호도 허용 — 같은 팔레트 안)          # 밝은 판 위 어두운 글씨(보스 이름): 가장자리는 판 색 쪽으로 섞음
    P = rgbpal[used].astype(float); lum = P @ [0.3, 0.59, 0.11]
    rim = bg if light else used[int(lum.argmin())]
    body_rgb_row = {}
    for y in range(y0, y1):                                 # 줄마다 가장 밝은 쪽 색(그라데이션 유지)
        v = idx[y][tx[y]]
        if len(v):
            L = rgbpal[v].astype(float) @ [0.3, 0.59, 0.11]; top = v[L <= np.percentile(L, 20)] if light else v[L >= np.percentile(L, 80)]
            body_rgb_row[y] = rgbpal[np.bincount(top, minlength=256).argmax()].astype(float)
    if not rows:                                            # 그라데이션 없이 한 색(하스피 «메뉴·옵션 쓸데없는 그라데이션 빼»)
        v = idx[tx]; L = rgbpal[v].astype(float) @ [0.3, 0.59, 0.11]
        top = v[L <= np.percentile(L, 20)] if light else v[L >= np.percentile(L, 80)]
        one = rgbpal[np.bincount(top, minlength=256).argmax() if body_idx is None else body_idx].astype(float)
        body_rgb_row = {y: one for y in body_rgb_row}
    a = coverage(text, font, x1 - x0 - 2, y1 - y0 - 2)
    A = np.zeros((H, W)); mh, mw = a.shape
    oy = y0 + 1 + (y1 - y0 - 2 - mh) // 2; ox = x0 + 1 + ((x1 - x0 - 2 - mw) // 2 if align == 'c' else 0)   # 'l' = 원본 글자 왼쪽 끝에 맞춤
    A[oy:oy + mh, ox:ox + mw] = a
    O = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), float) / 255
    out = idx.copy(); out[tx] = bg
    rr = rgbpal[rim].astype(float)
    for y in range(H):
        for x in range(W):
            if (A[y, x] if light else O[y, x]) < 0.35: continue
            br = body_rgb_row.get(y) if rows else None
            if br is None: br = body_rgb_row[min(body_rgb_row, key=lambda q: abs(q - y))]
            c = br * A[y, x] + rr * (1 - A[y, x])
            out[y, x] = used[int(((P - c) ** 2).sum(1).argmin())]
    return out


def compare():
    import gfx_text as G
    d = open(os.path.join(ROOT, 'work', 'disc1', 'SELTTL.BIN'), 'rb').read()
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18); Z = 4; rows = []
    for off, text, st in [(0x3ED00, '남자답게, 혼자서！', '메뉴'), (0x92AA0, '형님의 화원', '메뉴'), (0x5B3A0, '목적에 맞는 단련법', '옵션')]:
        pm, col, w, h = G.entry('SELTTL.BIN', off); idx = G.get_idx(d, pm, off, w, h)
        pal = G.colors(st, pm, col, np.arange(256).reshape(1, -1))[0]
        line = [('원본', idx)] + [(k, render(idx, text, pal, f)) for k, f in FONTS.items()]
        rows.append([(k, pal[x].copy(), x) for k, x in line])
    cw = max(r[0][1].shape[1] for r in rows) * Z + 20
    Sx = Image.new('RGB', (cw * 3, sum(r[0][1].shape[0] * Z + 30 for r in rows) * 2 + 20), (60, 60, 90)); D = ImageDraw.Draw(Sx)
    y = 4
    for r in rows:
        for k, (name, im, ix) in enumerate(r):
            im[ix == 0] = (28, 28, 60); x = (k % 3) * cw; yy = y + (k // 3) * (im.shape[0] * Z + 30)
            D.text((x + 4, yy), name, font=F, fill=(255, 230, 80))
            Sx.paste(Image.fromarray(im).resize((im.shape[1] * Z, im.shape[0] * Z), Image.NEAREST), (x + 4, yy + 22))
        y += 2 * (r[0][1].shape[0] * Z + 30)
    Sx.save(os.path.join(ROOT, 'work', 'gfx_preview', '메뉴_글꼴비교.png'))


if __name__ == '__main__':
    compare()


def render_charcolor(idx, text, rgbpal, font, src):
    """글자마다 원본의 다른 부분 색을 줄별로(그라데이션) 가져와 칠함 — 하스피 2026-11-24 «포징: 포 빨강·징 노랑·～! 빨강, 아래→위 옅어짐»
    src[k] = 글자 k 의 색을 가져올 원본 x 범위(0~1 비율). 줄 색 = 그 범위·그 줄 글자 화소 중 테두리 아닌 것의 최빈값."""
    H, W = idx.shape
    border = np.concatenate([idx[0], idx[-1], idx[:, 0], idx[:, -1]]); bg = int(np.bincount(border, minlength=256).argmax())
    tx = (idx != bg) & (idx != 0)
    ys, xs = np.nonzero(tx); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    nb = ~tx; edge = tx & (np.roll(nb, 1, 0) | np.roll(nb, -1, 0) | np.roll(nb, 1, 1) | np.roll(nb, -1, 1)); inner = tx & ~edge
    used = sorted(set(idx[tx].ravel().tolist())); P = rgbpal[used].astype(float); lum = P @ [0.3, 0.59, 0.11]
    rim = used[int(lum.argmin())]; rr = rgbpal[rim].astype(float)
    def rowmap(fa, fb):
        a, b = int(W * fa), int(W * fb); m = {}
        for y in range(H):
            v = idx[y, a:b][inner[y, a:b]]
            if len(v): m[y] = rgbpal[np.bincount(v, minlength=256).argmax()].astype(float)
        sub = sorted(set(idx[:, a:b][tx[:, a:b]].ravel().tolist())); Ps = rgbpal[sub].astype(float)
        r_ = sub[int((Ps @ [0.3, 0.59, 0.11]).argmin())]
        return m, sub, Ps, rgbpal[r_].astype(float)
    maps = [rowmap(*r) for r in src]
    sp = []; a = coverage(text, font, x1 - x0 - 2, y1 - y0 - 2, sp)
    A = np.zeros((H, W)); mh, mw = a.shape
    oy = y0 + 1 + (y1 - y0 - 2 - mh) // 2; ox = x0 + 1 + (x1 - x0 - 2 - mw) // 2; A[oy:oy + mh, ox:ox + mw] = a
    O = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), float) / 255
    owner = np.full(W, -1)
    for k, s_ in enumerate(sp):
        if s_: owner[ox + s_[0]:ox + s_[1] + 1] = k
    for x in range(W):                                   # 글자 사이 빈 열은 가까운 글자 것
        if owner[x] < 0:
            ks = [k for k, s_ in enumerate(sp) if s_]; owner[x] = min(ks, key=lambda k: min(abs(ox + sp[k][0] - x), abs(ox + sp[k][1] - x)))
    out = idx.copy(); out[tx] = bg
    for y in range(H):
        for x in range(W):
            if O[y, x] < 0.35: continue
            m, sub, Ps, rr_ = maps[owner[x]]; br = m[min(m, key=lambda q: abs(q - y))]
            c = br * A[y, x] + rr_ * (1 - A[y, x])
            out[y, x] = sub[int(((Ps - c) ** 2).sum(1).argmin())]
    return out


def render_bevel(idx, text, rgbpal, font):
    """테두리 1픽셀(원본 글자 둘레 색) + 입체감(위·왼쪽 가장자리 가장 밝게, 아래·오른쪽 한 단계 어둡게, 속 중간) — 하스피 2026-11-24 «1P형님·2P형님»"""
    H, W = idx.shape
    border = np.concatenate([idx[0], idx[-1], idx[:, 0], idx[:, -1]]); bg = int(np.bincount(border, minlength=256).argmax())
    tx = (idx != bg) & (idx != 0)
    ys, xs = np.nonzero(tx); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    nb = ~tx; edge = tx & (np.roll(nb, 1, 0) | np.roll(nb, -1, 0) | np.roll(nb, 1, 1) | np.roll(nb, -1, 1))
    glow = int(np.bincount(idx[edge].ravel(), minlength=256).argmax())
    used = sorted(set(idx[tx].ravel().tolist()) - {glow}); L = {u: float(rgbpal[u].astype(float) @ [0.3, 0.59, 0.11]) for u in used}
    bright = sorted(used, key=lambda u: -L[u]); hi = bright[0]
    mid = bright[1] if len(bright) > 1 else hi
    lo = min(bright, key=lambda u: abs(L[u] - 0.72 * L[hi]))
    a = coverage(text, font, x1 - x0 - 4, y1 - y0 - 2)
    A = np.zeros((H, W)); mh, mw = a.shape
    oy = y0 + 1 + (y1 - y0 - 2 - mh) // 2; ox = x0 + 2 + (x1 - x0 - 4 - mw) // 2; A[oy:oy + mh, ox:ox + mw] = a
    T = A >= 0.45
    ring = np.asarray(Image.fromarray(T.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
    out = idx.copy(); out[tx] = bg; out[ring & ~T] = glow
    up = ~np.roll(T, 1, 0); left = ~np.roll(T, 1, 1); dn = ~np.roll(T, -1, 0); rt = ~np.roll(T, -1, 1)
    out[T] = mid; out[T & (dn | rt)] = lo; out[T & (up | left)] = hi
    return out
