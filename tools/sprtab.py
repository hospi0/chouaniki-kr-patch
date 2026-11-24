# -*- coding: utf-8 -*-
r"""화면 묶음(ALL*·ENDING·SELTTL) 스프라이트 표 → 전부 그려 보기 (2026-11-24)
  표 항목 8 B = pmod u16 · colr u16 · srca/8 u16 · 크기 u16((폭/8)<<8 | 높이)   (ALL1_1 0xC8280~ 에서 확인, 스테이트 VDP1 명령과 일치)
  파일 위치 = VRAM(srca) + 0x28000 (파일 0x28000~0xA8000 = VDP1 VRAM 512 KB 통째)
  표 찾기 = 유효 항목(pmod ∈ PMS, 폭 8~352·높이 1~240, VRAM 안) 이 20개 이상 이어진 구간, 파일 0xA8000(VRAM 그림 뒤) 이후만
  python tools/sprtab.py [파일...] → work/sprtab/<파일>.tsv + <파일>_NN.png(흑백 색번호, 폭 16 이상만)"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PMS = {0x0080, 0x0088, 0x0090, 0x0098, 0x00A0, 0x0180, 0x0188, 0x01A0, 0x0488, 0x04A0}   # 스테이트들에서 본 값 + 반전 비트
D1 = os.path.join(ROOT, 'work', 'disc1'); OUT = os.path.join(ROOT, 'work', 'sprtab'); BASE = 0x28000


def valid(d, i):
    pm, col, sa, sz = struct.unpack_from('>HHHH', d, i)
    w, h = (sz >> 8) * 8, sz & 0xFF; mode = (pm >> 3) & 7
    return pm in PMS and 8 <= w <= 352 and 1 <= h <= 240 and 0x100 <= sa * 8 and sa * 8 + w * h // 2 <= 0x80000


def tables(d):
    out = []
    for start in (BASE + 0x80000,):
        for al in range(0, 8, 2):
            i = start + al; run = []
            while i + 8 <= len(d):
                if valid(d, i): run.append(i)
                else:
                    if len(run) >= 20: out.append(run)
                    run = []
                i += 8
            if len(run) >= 20: out.append(run)
    seen = set(); res = []
    for r in sorted(out, key=lambda r: r[0]):
        if r[0] in seen: continue
        seen.update(r); res.append(r)
    return res


def pix(d, pm, sa, w, h):
    mode = (pm >> 3) & 7; o = BASE + sa * 8
    if mode in (0, 1):
        b = np.frombuffer(d[o:o + w * h // 2].ljust(w * h // 2, b'\0'), np.uint8)
        a = np.zeros(w * h, np.uint8); a[0::2] = b >> 4; a[1::2] = b & 15; return a.reshape(h, w) * 17
    b = np.frombuffer(d[o:o + w * h].ljust(w * h, b'\0'), np.uint8); return b.reshape(h, w)


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(OUT, exist_ok=True)
    fs = sys.argv[1:] or sorted(f for f in os.listdir(D1) if f.startswith(('ALL', 'ENDING', 'SELTTL')))
    for fn in fs:
        d = open(os.path.join(D1, fn), 'rb').read(); T = tables(d); ent = []
        for r in T:
            for i in r:
                pm, col, sa, sz = struct.unpack_from('>HHHH', d, i); ent.append((i, pm, col, sa, (sz >> 8) * 8, sz & 0xFF))
        uniq = {}; [uniq.setdefault((e[3], e[4], e[5], e[1]), e) for e in ent]
        rows = sorted(uniq.values(), key=lambda e: e[3])
        with open(os.path.join(OUT, fn + '.tsv'), 'w', encoding='utf-8') as f:
            f.write('표위치\tpmod\tcolr\t파일위치\t폭\t높이\n')
            for i, pm, col, sa, w, h in rows: f.write('%X\t%04X\t%04X\t%X\t%d\t%d\n' % (i, pm, col, BASE + sa * 8, w, h))
        items = [(e, pix(d, e[1], e[3], e[4], e[5])) for e in rows if e[4] >= 16 and e[5] >= 8]
        W = 1600; page = 0; xx = yy = rh = 0; S = Image.new('L', (W, 1600), 40); Dd = ImageDraw.Draw(S)
        def flush():
            nonlocal page; S.crop((0, 0, W, yy + rh + 14)).save(os.path.join(OUT, '%s_%02d.png' % (fn, page))); page += 1
        for e, a in items:
            im = Image.fromarray(a)
            if xx + max(im.width, 70) > W: xx = 0; yy += rh + 14; rh = 0
            if yy + im.height + 14 > 1600:
                flush(); S = Image.new('L', (W, 1600), 40); Dd = ImageDraw.Draw(S); xx = yy = rh = 0
            Dd.text((xx, yy), '%X' % (BASE + e[3] * 8), fill=255); S.paste(im, (xx, yy + 12)); xx += max(im.width, 70) + 6; rh = max(rh, im.height)
        flush()
        print('%-12s 표 %d개 · 항목 %d · 고유 스프라이트 %d · 그림 %d장' % (fn, len(T), len(ent), len(rows), page))


if __name__ == '__main__':
    main()
