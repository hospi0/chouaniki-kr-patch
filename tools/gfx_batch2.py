# -*- coding: utf-8 -*-
r"""그림 글자 한글판 2차(2026-11-24) — 판 위 글자(조작 설정 버튼·안내 막대·말풍선) + 흐르는 이야기 띠
  글꼴·가장자리 = 1차와 같음(연성, tools/gfx_aa.coverage, 그라데이션 없음).
  판 위 글자: 안쪽(가장자리 MARGIN 픽셀 뺀) 줄마다 최빈 색 = 판 색, 그와 다른 화소 = 글자 → 판 색으로 지우고
             한글을 «글자 몸통 색 ↔ 그 줄 판 색» 덮음 비율로 섞어 원본이 쓰는 색번호 중 가장 가까운 것으로.
  말풍선: 원본 글자 줄(띠) 위치 그대로 — 1줄 왼쪽 맞춤, 2줄 «が» 자리에 «의», 3줄 왼쪽 맞춤.
  이야기 띠: 조각들을 가로로 이어 한 번에 그린 뒤 원래 조각 크기로 자름(낱말이 조각 경계에 걸려도 크기 같음).
  → work/gfx/<파일>@<위치>.bin · 미리보기 work/gfx_preview/{조작설정,말풍선,이야기띠}.png (실제 색, 원본|한글)
  python tools/gfx_batch2.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx_text as G, gfx_aa as A
FONT = G.FONT; D1 = G.D1
LUMW = np.array([0.3, 0.59, 0.11])
PLATES = [('G028', 0x61EE0), ('G029', 0x620E0), ('G030', 0x622E0), ('G031', 0x624E0), ('G032', 0x626E0),
          ('G033', 0x628E0), ('G034', 0x62AE0), ('G035', 0x62CE0), ('G036', 0x62EE0), ('G037', 0x63EE0)]
STRIPS = {'G038': ('ALL1_0.BIN', [0x7D8D0, 0x7E8D0, 0x7F8D0, 0x804D0, 0x80B50, 0x81B50, 0x82B50, 0x83B50, 0x84B50, 0x85B50]),
          'G039': ('ALL4_0.BIN', [0x7DC50, 0x7EBD0, 0x7FBD0, 0x80BD0, 0x81BD0, 0x82BD0, 0x83BD0])}
BUBBLE = ('ALL1_1.BIN', 0x74888)
PORTRAITS = [('G008', 0x41440), ('G008b', 0x45440), ('G008b', 0x49440), ('G008', 0x4E040), ('G008', 0x52040), ('G008b', 0x56040)]
BUBBLE_KO = ['슬슬, 보스인', '의', '모습이 보입니다요！']


def mix_into(out, Acov, oy, ox, body_rgb, plate_rgb_row, used, pal):
    P = pal[used].astype(float); H, W = out.shape; mh, mw = Acov.shape
    for y in range(mh):
        for x in range(mw):
            a = Acov[y, x]
            if a < 0.2: continue
            Y, X = oy + y, ox + x
            if not (0 <= Y < H and 0 <= X < W): continue
            c = body_rgb * a + plate_rgb_row[Y] * (1 - a)
            out[Y, X] = used[int(((P - c) ** 2).sum(1).argmin())]


def plate_parts(idx, margin):
    H, W = idx.shape; rowmode = np.zeros(H, int)
    for y in range(H):
        v = idx[y, margin:W - margin]; rowmode[y] = np.bincount(v, minlength=256).argmax()
    tm = np.zeros((H, W), bool); tm[margin:H - margin, margin:W - margin] = True
    tm &= (idx != rowmode[:, None]) & (idx != 0)
    return rowmode, tm


def plate_text(idx, text, pal, margin=2, boxes=None):
    """boxes = [(글자, x0, y0, x1, y1, 맞춤)] 없으면 글자 상자 하나에 가운데"""
    rowmode, tm = plate_parts(idx, margin)
    body = int(np.bincount(idx[tm], minlength=256).argmax())
    out = idx.copy(); out[tm] = rowmode[np.nonzero(tm)[0]]
    used = sorted(set(idx[idx > 0].ravel().tolist()) | {body})
    prow = {y: pal[rowmode[y]].astype(float) for y in range(idx.shape[0])}
    if boxes is None:
        ys, xs = np.nonzero(tm); boxes = [(text, xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, 'c')]
    for t, x0, y0, x1, y1, al in boxes:
        a = A.coverage(t, FONT, x1 - x0, y1 - y0); mh, mw = a.shape
        ox = x0 if al == 'l' else x0 + (x1 - x0 - mw) // 2
        mix_into(out, a, y0 + (y1 - y0 - mh) // 2, ox, pal[body].astype(float), prow, used, pal)
    return out


def bubble_boxes(idx):
    """말풍선 글자 줄(띠) 찾기 → 줄마다 글자 상자. 2줄째(«が» 하나)는 그 자리"""
    _, tm = plate_parts(idx, 4)
    rows = tm.any(1); bands = []; y = 0
    while y < len(rows):
        if rows[y]:
            y0 = y
            while y < len(rows) and rows[y]: y += 1
            bands.append((y0, y))
        else: y += 1
    bands = [b for b in bands if b[1] - b[0] >= 6]
    out = []
    for (y0, y1), t in zip(bands, BUBBLE_KO):
        xs = np.nonzero(tm[y0:y1].any(0))[0]; out.append((t, xs.min(), y0, xs.max() + 1, y1, 'l' if t != '의' else 'c'))
    return out, bands


def sheet(name, items, Z=3):
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 16)
    W = max(a.shape[1] for _, _, a, b in items) * Z * (1 if max(a.shape[1] for _, _, a, b in items) > 400 else 2) + 60
    stack = max(a.shape[1] for _, _, a, b in items) > 400
    H = sum((a.shape[0] * Z) * (2 if stack else 1) + 34 for _, _, a, b in items) + 10
    S = Image.new('RGB', (W, H), (70, 70, 80)); D = ImageDraw.Draw(S); y = 4
    for gid, ko, a, b in items:
        D.text((6, y), '%s  %s' % (gid, ko[:60]), font=F, fill=(255, 230, 80)); y += 20
        pa = Image.fromarray(a).resize((a.shape[1] * Z, a.shape[0] * Z), Image.NEAREST)
        pb = Image.fromarray(b).resize((b.shape[1] * Z, b.shape[0] * Z), Image.NEAREST)
        if stack: S.paste(pa, (6, y)); y += pa.height + 4; S.paste(pb, (6, y)); y += pb.height + 10
        else: S.paste(pa, (6, y)); S.paste(pb, (6 + pa.width + 30, y)); y += pa.height + 10
    dst = os.path.join(G.PRE, name + '.png'); tmp = dst + '.tmp.png'; S.save(tmp)
    try: os.replace(tmp, dst)
    except OSError: print('  잠김 →', tmp)


def show(st, pm, col, ix):
    rgb = G.colors(st, pm, col, ix).copy(); rgb[ix == 0] = (24, 24, 30); return rgb


def outlined(base, A, body, rim, pal, used, thr=0.35):
    """흰 몸통 + 검은 테두리 글자(원본 버튼·막대 글씨 모양): 덮음 A, 테두리 = A 를 1픽셀 넓힌 범위"""
    from PIL import ImageFilter
    O = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), float) / 255
    P = pal[used].astype(float); out = base.copy(); b, r = pal[body].astype(float), pal[rim].astype(float)
    for y, x in zip(*np.nonzero(O >= thr)):
        c = b * A[y, x] + r * (1 - A[y, x]); out[y, x] = used[int(((P - c) ** 2).sum(1).argmin())]
    return out


def place(H, W, text, x0, y0, x1, y1, al='c'):
    a = A.coverage(text, FONT, x1 - x0, y1 - y0); mh, mw = a.shape; M = np.zeros((H, W))
    ox = x0 if al == 'l' else x0 + (x1 - x0 - mw) // 2; oy = y0 + (y1 - y0 - mh) // 2
    M[oy:oy + mh, ox:ox + mw] = a; return M


def fill_texture(idx, mask):
    """mask 화소를 같은 줄 가장 가까운 비글자 화소로(왼쪽·오른쪽 번갈아) — 무늬 판 지우기"""
    out = idx.copy(); H, W = idx.shape
    for y, x in zip(*np.nonzero(mask)):
        for k in range(1, W):
            for xx in (x - k, x + k):
                if 0 <= xx < W and not mask[y, xx]: out[y, x] = idx[y, xx]; break
            else: continue
            break
    return out


def inpaint(idx, mask, pal):
    """mask 화소를 둘레(가림 안 된) 화소 RGB 평균으로 바깥부터 채워 들어감 → 원본이 쓰는 색번호 중 가장 가까운 것"""
    rgb = pal[idx].astype(float); m = mask.copy(); H, W = idx.shape; out = idx.copy()
    used = sorted(set(idx[~mask].ravel().tolist()) - {0}); P = pal[used].astype(float)
    while m.any():
        nxt = []
        for y, x in zip(*np.nonzero(m)):
            acc = []; 
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    Y, X = y + dy, x + dx
                    if (dy or dx) and 0 <= Y < H and 0 <= X < W and not m[Y, X]: acc.append(rgb[Y, X])
            if len(acc) >= 2: nxt.append((y, x, np.mean(acc, 0)))
        if not nxt:
            break
        for y, x, c in nxt:
            rgb[y, x] = c; m[y, x] = False; out[y, x] = used[int(((P - c) ** 2).sum(1).argmin())]
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8'); K = G.ko_map()
    # 조작 설정 버튼판 8장 = 같은 크기·같은 색 → 화소별 최빈값으로 «빈 판» 하나 공유 / 안내 막대 2장 = 무늬로 지움 (조작법 스테이트 색)
    d = open(os.path.join(D1, 'SELTTL.BIN'), 'rb').read(); items = []; ST = '조작법'
    pills = [(g, o) for g, o in PLATES if G.entry('SELTTL.BIN', o)[2] == 64]
    arrs = []
    for g, o in pills:
        pm, col, w, h = G.entry('SELTTL.BIN', o); arrs.append(G.get_idx(d, pm, o, w, h))
    stk = np.stack(arrs)
    pm0, col0, _, _ = G.entry('SELTTL.BIN', pills[0][1]); Lp0 = G.colors(ST, pm0, col0, np.arange(16).reshape(1, -1))[0].astype(float) @ LUMW
    istx = (Lp0[stk] >= 200) | (Lp0[stk] <= 24)                         # 흰 몸통·검은 테두리 = 글자
    empty = np.zeros(stk.shape[1:], int); hole = np.zeros(stk.shape[1:], bool)
    for y in range(stk.shape[1]):
        for x in range(stk.shape[2]):
            v = stk[:, y, x][~istx[:, y, x]]
            if len(v): empty[y, x] = np.bincount(v, minlength=16).argmax()
            else: hole[y, x] = True
    empty = fill_texture(empty, hole)                                    # 8장 모두 글자인 화소 = 옆 무늬로
    for (gid, off), idx in zip(pills, arrs):
        pm, col, w, h = G.entry('SELTTL.BIN', off); pal = G.colors(ST, pm, col, np.arange(16).reshape(1, -1))[0]
        L = pal.astype(float) @ LUMW; tx = idx != empty
        body = max(set(idx[tx].tolist()), key=lambda u: L[u]); rim = min(set(idx[tx].tolist()), key=lambda u: L[u])
        used = sorted(set(stk.ravel().tolist()) - {0})
        new = outlined(empty, place(h, w, K[gid], 4, 2, w - 4, h - 2), body, rim, pal, used)
        open(os.path.join(G.GFX, 'SELTTL.BIN@%X.bin' % off), 'wb').write(G.put_idx(new, pm))
        items.append((gid, K[gid], show(ST, pm, col, idx), show(ST, pm, col, new)))
    for gid, off in [p for p in PLATES if p not in pills]:
        pm, col, w, h = G.entry('SELTTL.BIN', off); idx = G.get_idx(d, pm, off, w, h)
        pal = G.colors(ST, pm, col, np.arange(256).reshape(1, -1))[0]; L = pal.astype(float) @ LUMW
        inner = np.zeros((h, w), bool); inner[1:h - 1, 2:w - 2] = True
        Lp = L[idx]; mid = np.median(Lp[inner])
        tx = inner & ((Lp >= mid + 60) | (Lp <= 24))                      # 흰 몸통·검은 테두리
        body = int(np.bincount(idx[tx & (Lp >= mid + 60)], minlength=256).argmax()); rim = int(np.bincount(idx[tx & (Lp <= 24)], minlength=256).argmax())
        base = fill_texture(idx, tx); used = sorted(set(idx.ravel().tolist()) - {0})
        new = outlined(base, place(h, w, K[gid], 4, 1, w - 4, h - 1), body, rim, pal, used)
        open(os.path.join(G.GFX, 'SELTTL.BIN@%X.bin' % off), 'wb').write(G.put_idx(new, pm))
        items.append((gid, K[gid], show(ST, pm, col, idx), show(ST, pm, col, new)))
    sheet('조작설정', items)
    # 말풍선(공통, 스테이지 스테이트 colr 0E9C)
    fn, off = BUBBLE; d = open(os.path.join(D1, fn), 'rb').read(); pm, col, w, h = G.entry(fn, off); col = 0x0E9C
    idx = G.get_idx(d, pm, off, w, h); pal = G.colors('스테이지중그림문자', pm, col, np.arange(16).reshape(1, -1))[0]
    L = pal.astype(float) @ LUMW; plate = 1                          # 말풍선 속 흰색(색번호 1)
    boxes = [('슬슬, 보스인', 12, 9, 140, 24, 'l'), ('의', 166, 25, 190, 38, 'c'), ('모습이 보입니다요！', 10, 41, 170, 55, 'l')]   # 원본 글자 덩어리 자리(어두운 화소 지도로 잼)
    base = idx.copy(); dark = [u for u in range(16) if u and L[u] < 120]
    for _, x0, y0, x1, y1, _a in boxes:                               # 지우기는 상자보다 2픽셀 넓게(흐린 가장자리 흔적까지), 테두리(x=0) 빼고
        reg = base[max(2, y0 - 2):y1 + 2, max(2, x0 - 5):min(w - 2, x1 + 2)]; reg[reg != plate] = plate
    body = min(dark, key=lambda u: abs(L[u] - 58)); Mx = np.zeros((h, w))
    for t, x0, y0, x1, y1, al in boxes: Mx = np.maximum(Mx, place(h, w, t, x0, y0, x1, y1, al))
    used = sorted(set(idx.ravel().tolist()) - {0}); P = pal[used].astype(float); new = base.copy()
    for y, x in zip(*np.nonzero(Mx >= 0.2)):
        c = pal[body] * Mx[y, x] + pal[plate] * (1 - Mx[y, x]); new[y, x] = used[int(((P - c) ** 2).sum(1).argmin())]
    open(os.path.join(G.GFX, '%s@%X.bin' % (fn, off)), 'wb').write(G.put_idx(new, pm))
    sheet('말풍선', [('G044', ' / '.join(BUBBLE_KO), show('스테이지중그림문자', pm, col, idx), show('스테이지중그림문자', pm, col, new))], Z=4)
    # 이야기 띠(인게임 그림글자 스테이트 colr 0EFC)
    items = []
    for gid, (fn, offs) in STRIPS.items():
        d = open(os.path.join(D1, fn), 'rb').read(); parts = []
        for off in offs:
            pm, col, w, h = G.entry(fn, off); parts.append((off, pm, w, G.get_idx(d, pm, off, w, h)))
        col = 0x0EFC; big = np.concatenate([p[3] for p in parts], 1)
        pal = G.colors('인게임 그림글자', pm, col, np.arange(16).reshape(1, -1))[0]
        nb = A.render(big, K[gid], pal, FONT, rows=False); x = 0
        for off, pm_, w, _ in parts:
            open(os.path.join(G.GFX, '%s@%X.bin' % (fn, off)), 'wb').write(G.put_idx(nb[:, x:x + w], pm_)); x += w
        items.append((gid, K[gid], show('인게임 그림글자', pm, col, big), show('인게임 그림글자', pm, col, nb)))
    sheet('이야기띠', items, Z=1)
    # 초상 6장 속 이름(캐릭터선택 스테이트 colr 0200): 흰 글자 + 둘레 어두운 화소 지우고 주변 사진 색으로 메움 → 같은 자리에 한글
    d = open(os.path.join(D1, 'SELTTL.BIN'), 'rb').read(); items = []; ST = '캐릭터선택'
    for gid, off in PORTRAITS:
        pm, col, w, h = G.entry('SELTTL.BIN', off); idx = G.get_idx(d, pm, off, w, h)
        pal = G.colors(ST, pm, col, np.arange(256).reshape(1, -1))[0]; L = pal.astype(float) @ LUMW; Lp = L[idx]
        zone = np.zeros((h, w), bool); zone[104:h, 6:w - 6] = True
        white = zone & (Lp > 225)
        near = np.zeros_like(white)
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2): near |= np.roll(np.roll(white, dy, 0), dx, 1)
        mask = zone & near                                                # 흰 글자 둘레 2픽셀 전부(흐린 회색 가장자리 얼룩 방지)
        ys, xs = np.nonzero(white); box = (xs.min() - 2, ys.min() - 1, xs.max() + 3, min(h, ys.max() + 2))
        body = int(np.bincount(idx[white], minlength=256).argmax()); dk = idx[mask & ~white]
        dk = idx[mask & ~white & (Lp < 70)]; rim = int(np.bincount(dk, minlength=256).argmax()) if len(dk) else int(np.argmin(L))
        base = inpaint(idx, mask, pal); used = sorted(set(idx.ravel().tolist()) - {0})
        new = outlined(base, place(h, w, K[gid], *box), body, rim, pal, used)
        open(os.path.join(G.GFX, 'SELTTL.BIN@%X.bin' % off), 'wb').write(G.put_idx(new, pm))
        items.append((gid, K[gid], show(ST, pm, col, idx)[92:], show(ST, pm, col, new)[92:]))
    sheet('초상이름', items, Z=3)
    print('조작설정 %d · 말풍선 1 · 이야기 띠 %d조각' % (len(PLATES), sum(len(v[1]) for v in STRIPS.values())))


if __name__ == '__main__':
    main()
