# -*- coding: utf-8 -*-
"""모든 화면 묶음 스프라이트를 «내용(바이트)» 로 중복 제거해 한 시트로 — 글자 찾기용
python tools/sprtab_uniq.py → work/sprtab/uniq_NN.png (라벨 = 처음 나온 파일:위치) + uniq.tsv(내용 같은 사본 전부)"""
import collections, hashlib, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sprtab
ROOT = sprtab.ROOT; D1 = sprtab.D1; OUT = sprtab.OUT
fs = sorted(f for f in os.listdir(D1) if f.startswith(('ALL', 'ENDING', 'SELTTL')))
seen = collections.OrderedDict()
for fn in fs:
    d = open(os.path.join(D1, fn), 'rb').read()
    for r in sprtab.tables(d):
        for i in r:
            pm, col, sa, sz = struct.unpack_from('>HHHH', d, i); w, h = (sz >> 8) * 8, sz & 0xFF
            if w < 16 or h < 8: continue
            nb = w * h // 2 if (pm >> 3) & 7 in (0, 1) else w * h
            o = sprtab.BASE + sa * 8; key = (w, h, hashlib.md5(d[o:o + nb]).hexdigest())
            if key not in seen: seen[key] = [fn, o, w, h, pm, sprtab.pix(d, pm, sa, w, h), set()]
            seen[key][6].add('%s:%X' % (fn, o))
with open(os.path.join(OUT, 'uniq.tsv'), 'w', encoding='utf-8') as f:
    f.write('번호\t폭\t높이\t처음\t사본\n')
    for k, (key, v) in enumerate(seen.items()): f.write('%d\t%d\t%d\t%s:%X\t%s\n' % (k, v[2], v[3], v[0], v[1], ' '.join(sorted(v[6]))))
W = 1600; page = 0; xx = yy = rh = 0; S = Image.new('L', (W, 1500), 40); Dd = ImageDraw.Draw(S)
for k, (key, v) in enumerate(seen.items()):
    im = Image.fromarray(v[5])
    if xx + max(im.width, 90) > W: xx = 0; yy += rh + 14; rh = 0
    if yy + im.height + 14 > 1500:
        S.crop((0, 0, W, yy)).save(os.path.join(OUT, 'uniq_%02d.png' % page)); page += 1
        S = Image.new('L', (W, 1500), 40); Dd = ImageDraw.Draw(S); xx = yy = rh = 0
    Dd.text((xx, yy), '%d %s' % (k, v[0][:6]), fill=255); S.paste(im, (xx, yy + 12)); xx += max(im.width, 90) + 6; rh = max(rh, im.height)
S.crop((0, 0, W, yy + rh + 14)).save(os.path.join(OUT, 'uniq_%02d.png' % page))
print('고유 스프라이트', len(seen), '그림', page + 1)
