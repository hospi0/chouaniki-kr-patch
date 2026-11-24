# -*- coding: utf-8 -*-
r"""동영상 구운 자막 → 원래 모양 그대로 한글 (2026-11-24, 하스피 «대사 자막은 아래 깔리는 거 원래 영상 모양대로»)
  대상: 아래 자막(대사·서술) — 밝은 회색(채도 낮음) 고딕 + 어두운 가장자리, 화면 아래 띠(BAND).
  1) 프레임마다 글자 덮개 = 띠 안 «채도 < 30 · 밝기 > TH» 화소 → 2픽셀 넓힘
  2) 덮개가 비슷한(IoU) 이어진 프레임 = 한 자막 구간. 구간 시작 시각으로 data/movie_ko.tsv 줄과 짝(가장 가까운 «초»)
  3) 구간에서 글자가 가장 진한 프레임의 덮개를 구간 전체에 씀(나타나고 사라지는 프레임 포함) — 진하기 비 = 한글 불투명도
  4) 덮개 자리 cv2 인페인팅(TELEA) → 한글: 원본 줄 위치(줄마다 왼쪽 x·글자 높이), 원본 글자색·가장자리색, 나눔고딕 Bold 4배 그려 줄임
  5) 바뀐 프레임만 tools/movenc.reencode(프레임마다 원래 크기 이하) → work/kr/<영상>.CPK + 미리보기 work/movie/sub/<영상>_kr.mp4
  python tools/movtext.py SAMPLE [--nopreview]"""
import glob, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import filmcpk, movenc
FFBIN = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin'
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
BAND = (165, 240); TH = 150; S = 4
LH, GAP = 17, 6          # 자막 한 줄 높이·줄 사이(SAMPLE 첫 두 자막 실측)
ROWS = {'_': [(182, 199), (205, 222)]}
BANDA, BANDPAD = 0.9, 5    # 띠 진하기(0~1)·줄 위아래 여유
BODY = (236, 236, 236)     # 한글 글자색
ACCUM = {'1GOOD': ('19', '20', '21')}   # 줄을 쌓으며 위로 미는 자막(きっと・たぶん・そうなんじゃ) → 아래 띠에 쌓아 보임
LOW = 100                  # 아래 자막을 찾는 범위(y ≥ LOW) — 1GOOD 쌓이는 첫 줄 «きっと» y≈118   # 띠 진하기(0~1)·줄 위아래 여유   # 자막 줄 자리(y0, y1) — SAMPLE 실측, 동영상마다 다르면 추가


def frames(name):
    fr = os.path.join(ROOT, 'work', 'movie', 'frames', name.lower())
    if not glob.glob(os.path.join(fr, 'f*.png')):
        os.makedirs(fr, exist_ok=True)
        subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', os.path.join(ROOT, 'work', 'disc1', name + '.CPK'),
                        '-fps_mode', 'passthrough', os.path.join(fr, 'f%04d.png')], check=True)
    return fr, sorted(glob.glob(os.path.join(fr, 'f*.png')))


def times(name):
    film = filmcpk.read(open(os.path.join(ROOT, 'work', 'disc1', name + '.CPK'), 'rb').read())
    return [(e[2] & 0x7FFFFFFF) / film['base'] for e in film['stab'] if e[2] != 0xFFFFFFFF]


def text_mask(a, th=TH):
    y0, y1 = BAND; m = np.zeros(a.shape[:2], bool); b = a[y0:y1].astype(int)
    m[y0:y1] = ((b.max(2) - b.min(2)) < 30) & (b.max(2) > th)
    return m


def segments(masks):
    """덮개가 비슷한 이어진 프레임 묶음 [(시작, 끝)] — 글자 화소 40 미만 프레임은 끊음"""
    seg = []; cur = None
    for i, m in enumerate(masks):
        n = m.sum()
        if n < 40:
            if cur: seg.append(cur); cur = None
            continue
        if cur:
            ref = masks[cur[2]]; iou = (m & ref).sum() / max(1, (m | ref).sum())
            if iou > 0.35:
                cur = (cur[0], i, cur[2] if ref.sum() >= n else i); continue
            seg.append(cur)
        cur = (i, i, i)
    if cur: seg.append(cur)
    return seg


def lines_of(mask):
    """덮개 → 줄 [(y0, y1, x0)] (행 투영으로 나눔)"""
    rc = mask.sum(1); rows = rc >= max(6, 0.15 * rc.max()) if rc.max() else rc > 0; out = []; y = 0   # 잡음 행(1~4화소) 빼기
    while y < len(rows):
        if rows[y]:
            a = y
            while y < len(rows) and rows[y]: y += 1
            if y - a >= 6:
                xs = np.nonzero(mask[a:y].any(0))[0]; out.append((a, y, int(xs.min()), int(xs.max()) + 1))
        else: y += 1
    return out


def ko_rows(name):
    R = []
    for l in open(os.path.join(ROOT, 'data', 'movie_ko.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f = l.split('\t')
        if f[0] == name: R.append((float(f[2]) if False else None, f))
    ja = {}
    for l in open(os.path.join(ROOT, 'data', 'movie_ja.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f = l.split('\t')
        if f[0] == name: ja[f[1]] = (float(f[2]), f[3])
    return [(ja[f[1]][0], f[3].split('／'), '쌓기' if f[1] in ACCUM.get(name, ()) else ja[f[1]][1]) for _, f in R if f[1] in ja]


def outlined_text(a, th=150):
    """자막 글자 화소 = 밝은 회색(채도 < 30·밝기 > th) 이면서 2픽셀 안에 어두운(< 60) 화소 — 머리카락·옷(속은 밝은 회색끼리) 빼기"""
    b = a.astype(int); g = ((b.max(2) - b.min(2)) < 30) & (b.max(2) > th)
    dark = (b.max(2) < 60).astype(np.uint8)
    near = cv2.dilate(dark, np.ones((5, 5), np.uint8)) > 0
    return g & near


def kwidth(pre, line, F):
    """줄 line 을 draw_lines 처럼 높이 LH 로 맞췄을 때 앞부분 pre 가 차지하는 폭"""
    def bb(t):
        im = Image.new('L', (len(t) * LH * S * 2 + 50, LH * S * 3), 0); ImageDraw.Draw(im).text((0, LH * S), t, font=F, fill=255); return im.getbbox()
    a, b = bb(line), bb(pre)
    return 0 if not (a and b) else round(b[2] * LH / (a[3] - a[1]))


def draw_lines(img, lines, boxes, body, rim, alpha):
    """img(RGB 배열)에 한글 줄을 원본 줄 상자(y0,y1,x0,x1) 왼쪽·높이에 맞춰 씀"""
    H, W = img.shape[:2]; cov = np.zeros((H, W)); ring = np.zeros((H, W))
    for t, (y0, y1, x0, x1) in zip(lines, boxes):
        h = y1 - y0; f = ImageFont.truetype(FONT, int(h * S * 1.05))
        im = Image.new('L', (W * S, h * S * 3), 0); ImageDraw.Draw(im).text((0, h * S), t, font=f, fill=255)
        bb = im.getbbox()
        if not bb: continue
        g = im.crop((0, bb[1], bb[2], bb[3])); sc = h / g.height; w = max(1, round(g.width * sc))
        if x0 == 'c': w = min(w, W - 16); x0 = (W - w) // 2
        if x0 + w > W - 4: w = W - 4 - x0
        a = np.asarray(g.resize((w, h), Image.LANCZOS), float) / 255
        cov[y0:y1, x0:x0 + w] = np.maximum(cov[y0:y1, x0:x0 + w], a)
    k = np.ones((3, 3), np.uint8); ring = cv2.dilate((cov * 255).astype(np.uint8), k).astype(float) / 255
    out = img.astype(float)
    r = (ring * alpha)[..., None]; out = out * (1 - r) + np.array(rim) * r
    c = (cov * alpha)[..., None]; out = out * (1 - c) + np.array(body) * c
    return np.clip(out, 0, 255).astype(np.uint8)


def ocr_present(name):
    """4fps OCR 에 일본어 3자 이상 읽힌 프레임 번호 k 집합"""
    import re
    out = set()
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'ocr.tsv'), encoding='utf-8'):
        f = l.rstrip('\n').split('\t'); m, k = f[0].rsplit('_', 1)
        if m == name and len(re.sub(r'[^぀-ヿ一-鿿]', '', f[1] if len(f) > 1 else '')) >= 3: out.add(int(k))
    return out


def ocr_events(name):
    """4fps OCR(work/ocr/ocr.tsv, 프레임 k ≈ (k−1)/4 초) → 글자 있는 구간 [(시작초, 끝초, 대표 글)] — 비슷한 글끼리 이어 묶음"""
    import difflib, re
    rows = []
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'ocr.tsv'), encoding='utf-8'):
        f = l.rstrip('\n').split('\t'); m, k = f[0].rsplit('_', 1)
        if m != name: continue
        t = re.sub(r'[^぀-ヿ一-鿿]', '', f[1] if len(f) > 1 else '')
        rows.append((int(k), t))
    rows.sort(); ev = []
    for k, t in rows:
        if len(t) < 3: continue
        if ev and k - ev[-1][1] <= 2 and difflib.SequenceMatcher(None, t, ev[-1][2]).ratio() >= 0.4:
            ev[-1][1] = k
            if len(t) > len(ev[-1][2]): ev[-1][2] = t
        else: ev.append([k, k, t])
    return [((a - 1) / 4, (b - 1) / 4, t) for a, b, t in ev if b > a]


def main():
    sys.stdout.reconfigure(encoding='utf-8'); name = sys.argv[1]
    fr, fs = frames(name); T = times(name); assert len(fs) == len(T), (len(fs), len(T))
    A = [np.asarray(Image.open(p).convert('RGB')) for p in fs]
    K = ko_rows(name); rows = ROWS.get(name, ROWS['_']); present = ocr_present(name)
    kr = os.path.join(fr, 'kr'); os.makedirs(kr, exist_ok=True)
    for p in glob.glob(os.path.join(kr, '*.png')): os.remove(p)
    F = ImageFont.truetype(FONT, int(LH * S * 1.05))
    band = np.zeros(A[0].shape[:2], bool)
    for y0, y1 in rows: band[y0 - 2:y1 + 2, 4:316] = True
    y0b, y1b = rows[0][0] - BANDPAD, rows[-1][1] + BANDPAD
    lowm = np.zeros(A[0].shape[:2], bool); lowm[LOW:, 4:316] = True; prev = None
    OM = {}
    def om(i):
        if i not in OM: OM[i] = outlined_text(A[i]) & lowm
        return OM[i]
    # 사건: 아래 자막(«자막») = over(원본 자막 위 띠), 그 밖(스크롤·고정·낙서·카드·제목·그림) = add(원본 두고 아래 띠) — 같은 시각 줄은 한 덩어리
    E = []
    for tk, lines, kind in K:
        if kind == '쌓기':                          # 원본이 줄을 쌓으며 위로 미는 연출 → 아래 띠에 앞 줄 + 새 줄(두 줄까지)
            prevl = E[-1][2] if E and E[-1][0] == 'add' and E[-1][3] == '쌓기' else []
            E.append(['add', tk, (prevl + list(lines))[-2:], '쌓기']); continue
        mode = 'over' if kind == '자막' else 'add'
        if mode == 'add' and E and E[-1][0] == 'add' and E[-1][3] != '쌓기' and abs(E[-1][1] - tk) < 0.05: E[-1][2].extend(lines)
        else: E.append([mode, tk, list(lines), kind])
    # over 시작 프레임 다듬기: 번역표 시각 ±0.6초 안에서 띠 속 글자 덮개가 가장 크게 바뀌는 프레임
    st = []; prevt = -1.0
    for j_, (mode, tk, _, _k) in enumerate(E):
        nt = E[j_ + 1][1] if j_ + 1 < len(E) else 1e9
        i0 = min(range(len(T)), key=lambda i: abs(T[i] - tk))
        if mode == 'over':
            cand = [i for i in range(3, len(T)) if max(prevt + 0.5, tk - 4.0) <= T[i] <= min(tk + 0.3, nt - 0.3)]   # 번역표 시각이 늦게 적힌 경우(1GOOD 아돈 6.8→실제 6.0)
            if cand: i0 = max(cand, key=lambda i: (om(i) ^ om(i - 3)).sum()) - 2   # 3프레임 간격(서서히 바뀌는 전환도)
        st.append(max(i0, st[-1] + 1) if st else i0)          # 앞 사건보다 뒤(순서 뒤집힘 방지)
        prevt = tk
    for j, (mode, tk, lines, _k) in enumerate(E):
        s0 = st[j]; s1 = (st[j + 1] if j + 1 < len(E) else len(T)) - 1
        fr_ix = list(range(s0, s1 + 1)); n = 0
        if not fr_ix: print('  ⚠프레임 없음 %.1fs' % tk); continue
        if mode == 'over':                          # 하스피 2026-11-24 «밑에 고정으로 깔아»: 위치 찾기 없음 — 고정 띠·가운데, 처음~끝 한 번
            full = max(1, max(om(i).sum() for i in fr_ix))
            vis = [i for i in fr_ix if om(i).sum() >= 0.3 * full]
            a_, b_ = (vis[0], vis[-1]) if vis else (fr_ix[0], fr_ix[-1])
            # (아래 자막은 끝 상한 없음 — 원본 자막이 보이는 동안 계속, 하스피 «모두 가자·오오 너무 빨리 사라짐»)
            show = lines[-2:]; bx = [(rows[q][0], rows[q][1], 'c', 0) for q in range(len(show))]
            for i in range(a_, b_ + 1):
                mi = outlined_text(A[i], 100) & band
                clean = cv2.inpaint(A[i], cv2.dilate(mi.astype(np.uint8), np.ones((5, 5), np.uint8)), 3, cv2.INPAINT_TELEA).astype(float)
                clean[y0b:y1b] *= (1 - BANDA)
                Image.fromarray(draw_lines(clean.astype(np.uint8), show, bx, BODY, (24, 24, 24), 1.0)).save(os.path.join(kr, 'f%04d.png' % (i + 1))); n += 1
            print('  자막 %.1f‥%.1fs 프레임 %d개 → %s' % (T[a_], T[b_], n, ' / '.join(show)))
        else:                                       # 원본 두고 아래 띠에 두 줄씩 차례로(하스피 «밑에 자막 안 뜨는 것도 띠 둘러서 밑에 깔아»)
            # 끝 = 원본 화면 글자가 사라질 때(하스피 «한 번 화면 글자가 지나갔으면 자막이 사라져야지»):
            #   4fps OCR 에 글자가 이어 잡히는 끝, 없으면 읽을 시간(최소 2초·글자당 0.12초) — 다음 자막보다 늦지 않게
            k = int(round(tk * 4)) + 1
            while k + 1 in present or k + 2 in present: k += 1
            t_end = max(tk + max(2.0, 0.12 * len(''.join(lines))), (k - 1) / 4 + 0.25)
            s1 = min(s1, max(s0, max(i for i in range(len(T)) if T[i] <= t_end)))
            chunks = [lines[q:q + 2] for q in range(0, len(lines), 2)]; per = (s1 - s0 + 1) / len(chunks)
            for c, ch in enumerate(chunks):
                a_, b_ = s0 + int(round(c * per)), s0 + int(round((c + 1) * per)) - 1
                bx = [(rows[q][0], rows[q][1], 'c', 0) for q in range(len(ch))]
                for i in range(a_, b_ + 1):
                    fade = 1.0                                     # 나타남·사라짐 효과 없음(깜빡임 금지)
                    img = A[i].astype(float); img[y0b:y1b] *= (1 - BANDA * fade)
                    Image.fromarray(draw_lines(img.astype(np.uint8), ch, bx, BODY, (24, 24, 24), fade)).save(os.path.join(kr, 'f%04d.png' % (i + 1))); n += 1
            print('  덧자막 %.1f‥%.1fs %d묶음 프레임 %d개' % (T[s0], T[s1], len(chunks), n))
    # movenc 는 fr/f####.png·kr/f####.png 이름 그대로 씀
    dst = os.path.join(ROOT, 'work', 'kr', name + '.CPK'); src = os.path.join(ROOT, 'work', 'disc1', name + '.CPK')
    movenc.TMP = os.path.join(ROOT, 'work', 'movie', '_gop')
    n = movenc.reencode(src, fr, kr, dst, os.path.getsize(src), log=lambda *x: None)
    d = open(dst, 'rb').read(); open(dst, 'wb').write(d + bytes(os.path.getsize(src) - len(d)))
    print('%s → %s %d B (원본 %d)' % (name, dst, n, os.path.getsize(src)))
    if '--nopreview' not in sys.argv:
        os.makedirs(os.path.join(ROOT, 'work', 'movie', 'sub'), exist_ok=True)
        subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', dst, '-vf', 'scale=640:480:flags=neighbor',
                        '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                        os.path.join(ROOT, 'work', 'movie', 'sub', name + '_kr.mp4')], check=True)


if __name__ == '__main__':
    main()
