# -*- coding: utf-8 -*-
r"""입체 로고(SELTTL 0x38000, 256×109 8bpp, colr 0000) 한글판 만들기 — 하스피 제작 그림(my files/초형귀_ 이끼빛 레트로 로고.png) 사용 (2026-11-24)
  1) 256×109 로 줄임(LANCZOS)  2) 바탕(어두운 회색 ≈ (37,37,37)) = 색번호 0(투명)
  3) 나머지 화소 = 원본 로고가 실제로 쓰는 색번호 중 가장 가까운 색(타이틀 스테이트 CRAM) — 팔레트·다른 그림 안 건드림
  → work/gfx/SELTTL.BIN@38000.bin(27,904 B 색번호) · 미리보기 work/survey/로고_원본_한글.png(원본|한글, 3배)
  python tools/gfx_logo.py        (디스크에 쓰지 않음)"""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx_check, vdp2render as V, spritesheet as SS
SRC = os.path.join(ROOT, 'my files', '초형귀_ 이끼빛 레트로 로고.png')
W, H, OFF = 256, 109, 0x38000


def main():
    d = open(os.path.join(ROOT, 'work', 'disc1', 'SELTTL.BIN'), 'rb').read()
    idx = np.frombuffer(d[OFF:OFF + W * H], np.uint8).reshape(H, W)
    _, _, cram = V.load('타이틀')
    pal = SS.rgb(np.asarray(cram)[0:256]).astype(float)          # colr 0000 → CRAM 0~255 (spritesheet.sprite 와 같은 식)
    used = sorted(set(idx.flatten().tolist()) - {0})
    img = np.asarray(Image.open(SRC).convert('RGB').resize((W, H), Image.LANCZOS), float)
    bg = np.array([37, 37, 37], float)
    out = np.zeros((H, W), np.uint8)
    P = pal[used]
    for y in range(H):
        for x in range(W):
            c = img[y, x]
            if np.abs(c - bg).sum() < 40: continue
            out[y, x] = used[int(((P - c) ** 2).sum(1).argmin())]
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'gfx', 'SELTTL.BIN@38000.bin'), 'wb').write(out.tobytes())
    def rgb(a):
        r = pal[a].astype(np.uint8).copy(); r[a == 0] = (40, 40, 40); return Image.fromarray(r)
    S = Image.new('RGB', (W * 2 + 8, H), (90, 90, 90)); S.paste(rgb(idx), (0, 0)); S.paste(rgb(out), (W + 8, 0))
    S.resize((S.width * 3, H * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', 'survey', '로고_원본_한글.png'))
    print('원본 색번호 %d개 사용 · 한글판 화소 %d (원본 %d)' % (len(used), (out > 0).sum(), (idx > 0).sum()))


if __name__ == '__main__':
    main()
