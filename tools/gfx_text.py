# -*- coding: utf-8 -*-
r"""그림 글자 한글판 1차(2026-11-24) — 바탕 투명(색번호 0) 글자 스프라이트를 통째로 다시 그림
  대상 = 아래 JOBS (data/gfx_ko.tsv 번역). 사본(같은 바이트가 여러 파일에) 은 work/sprtab/uniq.tsv 로 전부 같은 그림.
  색 = 원본 색번호 그대로: 몸통 = 바탕(0)에 안 닿는 화소 최빈값, 테두리 = 0 에 닿는 화소 최빈값. 원본 글자 범위(잉크 상자) 밖 화소 0.
  색 = 원본 색번호 그대로(실제 팔레트 밝기로 고름, 4bpp LUT 값은 CRAM 번호): remake() 설명 참고. 바탕판(가장자리 최빈값)은 그대로.
  글꼴·가장자리: 연성(하스피 선택) 4배 → 덮음 비율로 원본 색 단계 섞기(tools/gfx_aa.render). 육체적점수 = 8×8 한글 한 색(PLAIN8).
  미리보기(실제 색, 원본 | 한글): work/gfx_preview/<무리>.png  ·  결과 색번호: work/gfx/<파일>@<위치>.bin
  python tools/gfx_text.py          (디스크에 안 씀)"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sprtab, spritesheet as SS, vdp2render as V, vdp1cmd, gfx_aa
FONT = gfx_aa.FONTS['연성']                    # 하스피 2026-11-24 선택
D1 = os.path.join(ROOT, 'work', 'disc1'); GFX = os.path.join(ROOT, 'work', 'gfx'); PRE = os.path.join(ROOT, 'work', 'gfx_preview')
GAL = r'C:/claude/utils/font/Galmuri-v2.40.3/Galmuri11-Bold.ttf'
GAL7 = r'C:/claude/utils/font/Galmuri-v2.40.3/Galmuri7.ttf'
NEB = r'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
S = 4
# (id, 무리, 파일, 위치) — 폭·높이·pmod·colr 는 sprtab 표에서
JOBS = [('G002', '타이틀', 'SELTTL.BIN', 0x84660), ('G003', '타이틀', 'SELTTL.BIN', 0x3FC10),
        ('G004', '메뉴', 'SELTTL.BIN', 0x3ED00), ('G005', '메뉴', 'SELTTL.BIN', 0x3F320), ('G006', '메뉴', 'SELTTL.BIN', 0x3F940),
        ('G007', '메뉴', 'SELTTL.BIN', 0x92AA0), ('G010', '캐릭터선택', 'SELTTL.BIN', 0x64EE0), ('G011', '캐릭터선택', 'SELTTL.BIN', 0x654E0)] + \
       [(i, '옵션', 'SELTTL.BIN', o) for i, o in [('G012', 0x5A040), ('G013', 0x83260), ('G014', 0x5B3A0), ('G015', 0x5D020), ('G016', 0x5DE20),
                                               ('G017', 0x5F120), ('G018', 0x5E4A0), ('G019', 0x5EAA0), ('G020', 0x5F820), ('G021', 0x5BB20),
                                               ('G022', 0x5C120), ('G023', 0x5C920), ('G024', 0x83960), ('G025', 0x65C60), ('G026', 0x65D60),
                                               ('G027', 0x663E0)]] + \
       [('G040', 'HUD', 'ALL1_1.BIN', 0x72A80), ('G041', 'HUD', 'ALL1_1.BIN', 0x74288), ('G043', 'HUD', 'ALL1_1.BIN', 0x74708),
        ('G046', 'HUD', 'ALL1_0.BIN', 0x68908)] + \
       [(i, '보스이름', f, o) for i, f, o in [('G047', 'ALL1_0.BIN', 0x67308), ('G048', 'ALL1_1.BIN', 0x89650), ('G049', 'ALL1_3.BIN', 0x88DD0),
                                            ('G050', 'ALL2_1.BIN', 0x87110), ('G051', 'ALL2_3.BIN', 0x88510), ('G052', 'ALL3_1.BIN', 0x91850),
                                            ('G053', 'ALL3_3.BIN', 0x86DD0), ('G054', 'ALL4_3.BIN', 0xA5210), ('G055', 'ALL5_1.BIN', 0x85150),
                                            ('G056', 'ALL5_3.BIN', 0x8EF90), ('G057', 'ALL6_1.BIN', 0x841D0)]]
# 실행 중 쓰는 colr(스테이트 VDP1 명령에서 확인) — 표 값과 다른 것. 보스 이름은 1-1 스테이트 0E9C 를 모든 스테이지에 가정(⚠️확인 전)
COLR = {'G040': 0x0E80, 'G041': 0x0E84, 'G046': 0x0EB4, **{'G%03d' % i: 0x0E9C for i in range(47, 58)}}
STATE = {'타이틀': '타이틀', '메뉴': '메뉴', '캐릭터선택': '캐릭터선택', '옵션': '옵션', 'HUD': '스테이지중그림문자', '보스이름': '스테이지중그림문자'}
# 그라데이션 없음 — 모든 글자 한 색(하스피 2026-11-24 «모든 글자에 그라데이션 빼»)
PLAIN8 = {'G040'}
BEVEL = {'G010', 'G011'}                      # 얇은 테두리 + 입체감(하스피 «1P형님·2P형님 원본처럼»)
GROUP_BODY = {'옵션': None, '메뉴': None}
LEFT = {'메뉴', '옵션'}                        # 원본 글자 왼쪽 끝 맞춤(하스피 «줄 안 맞음»)                  # 무리 통일 몸통 색번호 — main() 첫머리에서 기준 그림(옵션 = G013 大会出場の回数)으로 채움(하스피 «어두운 글자 다른 글자랑 같은 색»)
BODY_REF = {'옵션': ('SELTTL.BIN', 0x83260), '메뉴': ('SELTTL.BIN', 0x3ED00)}   # 메뉴 = 남자답게 기준(하스피 «몸풀기 어두움»)
BODY_KEEP = {'G012'}                          # 통일에서 뺌: 옵션 제목(초록)
# 글자별 원본 색 범위(x 비율) + 줄별 그라데이션 — 하스피: 포징～！ = 포 빨강(ポーズ)·징 노랑(ィング)·～！ 빨강(！)
CHARCOL = {'G046': [(0.0, 0.40), (0.45, 0.85), (0.86, 1.0), (0.86, 1.0)]}                             # 장식 없이 8×8 한글 한 색(하스피)
ROWS = {'G041', 'G043', 'G046'}               # 줄마다 색이 바뀌는 그라데이션 글자 — 원본 줄 색 그대로(하스피 «HUD 색 작살»)
STATE_ID = {'G046': '포즈'}                   # 무리와 다른 화면에서 본 것


def ko_map():
    m = {}
    for l in open(os.path.join(ROOT, 'data', 'gfx_ko.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f = l.split('\t'); m[f[0]] = f[2]
    return m


def entry(fn, off):
    for l in open(os.path.join(ROOT, 'work', 'sprtab', fn + '.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f = l.split('\t')
        if int(f[3], 16) == off: return int(f[1], 16), int(f[2], 16), int(f[4]), int(f[5])
    raise KeyError((fn, hex(off)))


def get_idx(d, pm, off, w, h):
    if (pm >> 3) & 7 in (0, 1):
        b = np.frombuffer(d[off:off + w * h // 2], np.uint8); a = np.zeros(w * h, np.uint8); a[0::2] = b >> 4; a[1::2] = b & 15
        return a.reshape(h, w)
    return np.frombuffer(d[off:off + w * h], np.uint8).reshape(h, w).copy()


def put_idx(a, pm):
    if (pm >> 3) & 7 in (0, 1):
        f = a.reshape(-1); return bytes(((f[0::2] << 4) | f[1::2]).astype(np.uint8))
    return bytes(a.astype(np.uint8).reshape(-1))


def colors(st, pm, col, idx):
    """st = 그 화면 스테이트(work/mem/<st>) — 4bpp LUT 는 그 스테이트 VDP1 VRAM 에서, 8bpp 는 그 스테이트 CRAM 에서"""
    if (pm >> 3) & 7 == 1:
        v = vdp1cmd.load(os.path.join(ROOT, 'work', 'mem', st))
        lut = np.frombuffer(v[col * 8:col * 8 + 32], '>u2').astype(int)
        _, _, cram = V.load(st); cram = np.asarray(cram)
        e = lut[idx]                                   # LUT 값 = CRAM 팔레트 번호(MSB 0, 이 게임 SPCTL 0) — RGB 아님
        return SS.rgb(np.where(e & 0x8000, e, cram[e & 0x7FF]))
    _, _, cram = V.load(st); cram = np.asarray(cram)
    base = (col & 0x7F0) if (pm >> 3) & 7 == 0 else (col & 0x700)
    return SS.rgb(cram[(base + idx.astype(int)) & 0x7FF])


def dil(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if abs(dx) + abs(dy) <= r: out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def text_mask(text, bw, bh):
    """bw×bh 안에 들어가는 글자 덮개 — 높이 < 11 은 갈무리7 픽셀 글꼴, 그 위는 나눔 ExtraBold 4배 그려 줄임. 넘치면 가로만 좁힘"""
    if bh < 11:
        f = ImageFont.truetype(GAL7, 8)
        im = Image.new('L', (len(text) * 16 + 40, 40), 0); ImageDraw.Draw(im).text((10, 10), text, font=f, fill=255)
        g = im.crop(im.getbbox()); m = (np.array(g) >= 128).astype(np.uint8)
    else:
        f = ImageFont.truetype(NEB, bh * S)
        im = Image.new('L', (len(text) * bh * S * 2 + 80, bh * S * 3), 0); ImageDraw.Draw(im).text((20, bh * S // 2), text, font=f, fill=255)
        g = im.crop(im.getbbox()); h = bh; w = max(1, round(g.width * h / g.height))
        m = (np.array(g.resize((w, h), Image.LANCZOS)) >= 110).astype(np.uint8)
    if m.shape[0] > bh:
        m = (np.array(Image.fromarray(m * 255).resize((max(1, round(m.shape[1] * bh / m.shape[0])), bh), Image.LANCZOS)) >= 110).astype(np.uint8)
    if m.shape[1] > bw:
        m = (np.array(Image.fromarray(m * 255).resize((bw, m.shape[0]), Image.LANCZOS)) >= 110).astype(np.uint8)
    return m


def han8_mask(text):
    """8×8 조합형 한글(aww hangul8comp, 쿠오바디스 han8 로 ㅔ/ㅖ 구별) — 칸마다 8 폭 그대로 이어 붙임"""
    sys.path.insert(0, r'C:/claude/project/quovadis2-kr-patch/tools'); import han8
    cols = []
    for ch in text:
        g, _ = han8.glyph(ch); cols.append(np.array(g, np.uint8)[:, :8])
    return np.concatenate(cols, 1)


def remake_plain8(idx, text, lum):
    """장식 다 뺀 8×8 한글 한 색(하스피 2026-11-24 «육체적점수»): 바탕 0, 몸통 = 원본 가장 밝은 색"""
    nz = idx > 0; body = int(np.bincount(idx[nz & (lum[idx] >= 0.85 * lum[idx][nz].max())].ravel(), minlength=256).argmax())
    m = han8_mask(text); out = np.zeros_like(idx); H, W = idx.shape; mh, mw = m.shape
    ox = (W - mw) // 2; oy = (H - mh) // 2; out[oy:oy + mh, ox:ox + mw][m.astype(bool)] = body
    return out


def remake(idx, text, lum, rows=False):
    """lum[색번호] = 실제 밝기.
    바탕 = 가장자리 화소 최빈값(0 = 투명, 아니면 그림 안의 판) — 글자 화소만 바탕으로 지우고 다시 씀.
    바탕이 어두우면(투명 포함) 몸통 = 글자 화소 중 «최대 밝기 60% 이상» 최빈값, 밝으면 몸통 = «가장 어두운 쪽» 최빈값.
    테두리 = 바탕에 닿는 글자 화소 중 몸통과 다른 색의 최빈값."""
    H, W = idx.shape
    border = np.concatenate([idx[0], idx[-1], idx[:, 0], idx[:, -1]])
    bg = int(np.bincount(border, minlength=256).argmax())
    tx = (idx != bg) & (idx != 0)
    ys, xs = np.nonzero(tx); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    nb = ~tx
    edge = tx & (np.roll(nb, 1, 0) | np.roll(nb, -1, 0) | np.roll(nb, 1, 1) | np.roll(nb, -1, 1))
    L = lum[idx]; Lt = L[tx]
    if bg == 0 or lum[bg] < np.median(Lt):
        cand = tx & (L >= 0.6 * Lt.max())
    else:
        cand = tx & (L <= Lt.min() + 0.25 * (Lt.max() - Lt.min()))
    body = int(np.bincount(idx[cand].ravel(), minlength=256).argmax())
    r = edge & (idx != body)
    rim = int(np.bincount(idx[r].ravel(), minlength=256).argmax()) if r.any() else body
    m = text_mask(text, x1 - x0 - 2, y1 - y0 - 2)
    out = idx.copy(); out[tx] = bg; mh, mw = m.shape
    oy = y0 + 1 + (y1 - y0 - 2 - mh) // 2; ox = x0 + 1 + (x1 - x0 - 2 - mw) // 2
    tm = np.zeros((H, W), np.uint8); tm[oy:oy + mh, ox:ox + mw] = m
    ring = dil(tm) & ~tm.astype(bool)
    out[ring.astype(bool)] = rim; out[tm.astype(bool)] = body
    if rows:                                   # 그라데이션 글자: 몸통 색을 원본 «같은 줄» 몸통 색으로(줄에 없으면 가까운 줄)
        inner = tx & ~edge; rc = {}
        for y in range(H):
            v = idx[y][inner[y]]
            if len(v): rc[y] = int(np.bincount(v, minlength=256).argmax())
        for y in range(H):
            if tm[y].any() and rc:
                k = min(rc, key=lambda q: abs(q - y)); out[y][tm[y].astype(bool)] = rc[k]
    keep = np.zeros((H, W), bool); keep[y0:y1, x0:x1] = True; out[~keep] = idx[~keep]   # 원본 글자 상자 밖은 원본 그대로
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(GFX, exist_ok=True); os.makedirs(PRE, exist_ok=True)
    K = ko_map(); groups = {}
    for grp, (fn, off) in BODY_REF.items():                     # 기준 그림의 가장 밝은 쪽 최빈 색번호
        d = open(os.path.join(D1, fn), 'rb').read(); pm, col, w, h = entry(fn, off); ix = get_idx(d, pm, off, w, h)
        pal = colors(STATE[grp], pm, col, np.arange(256).reshape(1, -1))[0]; L = pal.astype(float) @ [0.3, 0.59, 0.11]
        v = ix[ix > 0]; top = v[L[v] >= np.percentile(L[v], 80)]; GROUP_BODY[grp] = int(np.bincount(top, minlength=256).argmax())
    for job in JOBS:
        gid, grp, fn, off = job[:4]
        d = open(os.path.join(D1, fn), 'rb').read(); pm, col, w, h = entry(fn, off)
        col = COLR.get(gid, col)
        st = STATE_ID.get(gid, STATE[grp])
        lum = colors(st, pm, col, np.arange(256 if (pm >> 3) & 7 >= 2 else 16).reshape(1, -1))[0].astype(float) @ [0.3, 0.59, 0.11]
        idx = get_idx(d, pm, off, w, h)
        pal = colors(st, pm, col, np.arange(256 if (pm >> 3) & 7 >= 2 else 16).reshape(1, -1))[0]
        if gid in PLAIN8: new = remake_plain8(idx, K[gid], lum)
        elif gid in BEVEL: new = gfx_aa.render_bevel(idx, K[gid], pal, FONT)
        elif gid in CHARCOL: new = gfx_aa.render_charcolor(idx, K[gid], pal, FONT, CHARCOL[gid])
        else: new = gfx_aa.render(idx, K[gid], pal, FONT, rows=False, body_idx=None if gid in BODY_KEEP else GROUP_BODY.get(grp), align='l' if grp in LEFT else 'c')
        open(os.path.join(GFX, '%s@%X.bin' % (fn, off)), 'wb').write(put_idx(new, pm))
        groups.setdefault(grp, []).append((gid, K[gid], colors(st, pm, col, idx), colors(st, pm, col, new), idx, new))
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 16); Z = 3
    for grp, items in groups.items():
        W = max(it[2].shape[1] for it in items) * Z * 2 + 60; H = sum(it[2].shape[0] * Z + 26 for it in items) + 10
        Sx = Image.new('RGB', (W, H), (70, 70, 80)); D = ImageDraw.Draw(Sx); y = 4
        for gid, ko, a, b, idx, new in items:
            D.text((6, y), '%s  %s' % (gid, ko), font=F, fill=(255, 230, 80)); y += 20
            for k, (im, ix) in enumerate(((a, idx), (b, new))):
                im = im.copy(); im[ix == 0] = (24, 24, 30)
                p = Image.fromarray(im).resize((im.shape[1] * Z, im.shape[0] * Z), Image.NEAREST)
                Sx.paste(p, (6 + k * (p.width + 30), y))
            y += a.shape[0] * Z + 6
        dst = os.path.join(PRE, '%s.png' % grp); tmp = dst + '.tmp.png'; Sx.save(tmp)
        try: os.replace(tmp, dst)
        except OSError: print('  잠김(열려 있음) →', tmp)
    print('그림', len(JOBS), '· 미리보기', ', '.join(groups))


if __name__ == '__main__':
    main()
