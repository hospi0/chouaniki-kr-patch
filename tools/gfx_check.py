# -*- coding: utf-8 -*-
r"""그림 글자 «원본 실제 색» 뽑기 (2026-11-24) — 스테이트의 VDP1 VRAM·CRAM 으로 스프라이트를 게임 색 그대로 그림
  · 입체 로고 → work/survey/원본_입체로고.png(3배) · 원본_입체로고_1배.png
  · 판독 불확실 항목(data/gfx_ja.tsv 「확인」) → work/survey/확인필요_그림글자.png(6배)
  python tools/gfx_check.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import vdp1cmd, vdp2render as V, spritesheet as SS, sprtab
FK = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 22); FJ = ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 22)
SV = os.path.join(ROOT, 'work', 'survey')


def real(state, file_off, w, h, pm, col):
    """state = work/mem/<이름>, file_off = 화면 묶음 파일 위치(VRAM + 0x28000)"""
    v = vdp1cmd.load(os.path.join(ROOT, 'work', 'mem', state)); _, _, cram = V.load(state)
    return Image.fromarray(SS.sprite(v, cram, pm, col, file_off - 0x28000, w, h).astype(np.uint8)).convert('RGB')


def gray(fn, o, w, h, pm):
    d = open(os.path.join(ROOT, 'work', 'disc1', fn), 'rb').read(); a = sprtab.pix(d, pm, (o - 0x28000) // 8, w, h).astype(float)
    u = np.unique(a); r = np.searchsorted(u, a) / max(1, len(u) - 1) * 255
    return Image.fromarray(r.astype(np.uint8)).convert('RGB')


def main():
    logo = real('타이틀', 0x38000, 256, 109, 0x00A0, 0x0000)
    logo.save(os.path.join(SV, '원본_입체로고_1배.png')); logo.resize((768, 327), Image.NEAREST).save(os.path.join(SV, '원본_입체로고.png'))
    rows = [(('G009 캐릭터 이름 띠 ', 'いだてん／べんてん?', ' 실제 색'), [real('캐릭터선택', 0x4D440, 128, 8, 0x00A0, 0x0300), real('캐릭터선택', 0x4DC40, 128, 8, 0x00A0, 0x0300)]),
            (('G028 조작 설정 ', 'ほーめーしょん?', ' 실제 색'), [real('옵션', 0x61EE0, 64, 16, 0x0088, 0x0F10)]),
            (('G031 조작 설정 ', '弾でるッス', ' 실제 색'), [real('옵션', 0x624E0, 64, 16, 0x0088, 0x0F10)]),
            (('G032 조작 설정 ', 'とくしゅしよー', ' 실제 색'), [real('옵션', 0x626E0, 64, 16, 0x0088, 0x0F10)]),
            (('G045 HUD 작은 글자 ', '男＝?', ' 실제 색'), [real('스테이지중그림문자', 0x72B20, 16, 8, 0x0088, 0x0E80), real('스테이지중그림문자', 0x72BA0, 16, 8, 0x0088, 0x0E80)]),
            (('G048 보스 이름 1-1 ', '逞と統也?', ' 실제 색'), [real('스테이지중그림문자', 0x89650, 64, 16, 0x0088, 0x0E9C)]),
            (('G052 보스 이름 3-1 ', '蚤大統領?', ' 흑백(이 스테이지 스테이트 없음)'), [gray('ALL3_1.BIN', 0x91850, 64, 16, 0x88)])]
    Z = 6; rows = [(l, [i.resize((i.width * Z, i.height * Z), Image.NEAREST) for i in ims]) for l, ims in rows]
    W = max(sum(i.width + 12 for i in ims) for _, ims in rows) + 20; H = sum(max(i.height for i in ims) + 50 for _, ims in rows) + 10
    S = Image.new('RGB', (W, H), (40, 40, 40)); D = ImageDraw.Draw(S); y = 6
    for (a, b, c), ims in rows:
        x = 10
        for t, f in ((a, FK), (b, FJ), (c, FK)): D.text((x, y), t, font=f, fill=(255, 230, 80)); x += D.textlength(t, font=f)
        x = 10; y += 34
        for im in ims: S.paste(im, (x, y)); x += im.width + 12
        y += max(i.height for i in ims) + 16
    S.save(os.path.join(SV, '확인필요_그림글자.png'))


if __name__ == '__main__':
    main()
