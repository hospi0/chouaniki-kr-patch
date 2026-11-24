# -*- coding: utf-8 -*-
r"""캐릭터 선택 초상 6장(SELTTL 128×128, 이름 글자가 그림 안 아래쪽) 실제 색 뽑기 (2026-11-24)
  초상 = SELTTL 0x41440·45440·49440·4E040·52040·56040 (pmod 00A0 8bpp, colr 0200, 캐릭터선택 스테이트 CRAM)
  4D440·4DC40(128×8)·4D840(8×128) 은 액자 테두리 조각 — 글자 아님
  → work/survey/원본_캐릭터이름.png (초상 3배 + 이름 부분 6배)
  python tools/gfx_names.py"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gfx_check
F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 20)
OFFS = [0x41440, 0x45440, 0x49440, 0x4E040, 0x52040, 0x56040]
ims = [gfx_check.real('캐릭터선택', o, 128, 128, 0x00A0, 0x0200) for o in OFFS]
S = Image.new('RGB', (6 * 396 + 20, 30 + 384 + 20 + 30 * 6 + 20), (40, 40, 40)); D = ImageDraw.Draw(S)
for k, (o, im) in enumerate(zip(OFFS, ims)):
    x = 10 + k * 396
    D.text((x, 4), 'SELTTL %X' % o, font=F, fill=(255, 230, 80))
    S.paste(im.resize((384, 384), Image.NEAREST), (x, 30))
    S.paste(im.crop((0, 98, 128, 128)).resize((384, 90), Image.NEAREST), (x, 30 + 384 + 20))
S.save(os.path.join(gfx_check.SV, '원본_캐릭터이름.png'))
