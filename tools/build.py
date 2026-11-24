# -*- coding: utf-8 -*-
r"""초형귀 究極…男の逆襲 빌드(2026-11-24, 새턴 봄버맨 파이트 build.py 를 옮김) — 화면 묶음 그림 제자리 덮어쓰기 + 트랙 01 MODE1 EDC/ECC
  입력: work/gfx/<파일>@<위치 16진>.bin (tools/gfx_text.py · gfx_logo.py · gfx_batch2.py) — 스프라이트 색번호 바이트 그대로, 크기 같음.
        work/kr/<동영상>.CPK (tools/movtext.py) — 원본과 같은 크기, 파일 통째.
  사본: 원본 바이트가 다른 화면 묶음(ALL*·ENDING·SELTTL)에도 «같은 바이트»로 있으면 그 자리도 전부 같은 새 그림으로(스테이지 공통 HUD·포즈 등).
  검사: 같은 파일 안 판 겹침 없음 · 파일 크기 그대로 · 바뀐 섹터가 바꾼 파일 안 · 되읽기 일치.
  python tools/build.py [--write] [--install]   ⛔--write·--install 은 하스피 허락 받고
"""
import glob, hashlib, os, shutil, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from iso import Disc, ROMS
from cdrom_ecc import recalc_sector

F_DIR = r'F:\hospi\roms\ss roms\Chou Aniki - Kyuukyoku... Otoko no Gyakushuu (Japan)'
OUT = os.path.join(ROOT, 'dist', 'build', 'Chou Aniki - Kyuukyoku... Otoko no Gyakushuu (Japan)')
SCREENS = ('ALL', 'ENDING', 'SELTTL')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''): h.update(c)
    return h.hexdigest()


def patches(D):
    files = {p.strip('/'): (l, s) for p, l, s in D.files}
    data = {n: D.sec(l, (s + 2047) // 2048)[:s] for n, (l, s) in files.items() if n.startswith(SCREENS)}
    by = defaultdict(dict)
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'gfx', '*@*.bin'))):
        name, off = os.path.basename(fn)[:-4].split('@'); off = int(off, 16); new = open(fn, 'rb').read()
        old = data[name][off:off + len(new)]
        if old == new: continue
        for n, d in data.items():                                  # 같은 바이트 사본 전부
            i = d.find(old)
            while i >= 0:
                prev = by[n].get(i)
                assert prev is None or prev == new, ('같은 자리 다른 새 그림', n, hex(i))
                by[n][i] = new; i = d.find(old, i + 1)
    for fn in sorted(glob.glob(os.path.join(ROOT, 'work', 'kr', '*.CPK'))):     # 동영상 자막(tools/movtext.py, 원본과 같은 크기) — 파일 통째
        name = os.path.basename(fn); new = open(fn, 'rb').read()
        assert len(new) == files[name][1], ('동영상 크기 다름', name)
        by[name][0] = new
    jobs = []
    for name, P in sorted(by.items()):
        lba, size = files[name]; cap = (size + 2047) // 2048 * 2048
        orig = D.sec(lba, cap // 2048); new = bytearray(orig); L = sorted(P.items())
        for (o1, d1), (o2, d2) in zip(L, L[1:]): assert o1 + len(d1) <= o2, ('판 겹침', name, hex(o1), hex(o2))
        for o, d in L: assert o + len(d) <= size, ('파일 밖', name, hex(o)); new[o:o + len(d)] = d
        jobs.append((name, lba, cap, bytes(orig), bytes(new)))
        print('  %-12s 그림 %2d장 · 바뀐 바이트 %d' % (name, len(L), sum(a != b for a, b in zip(orig, new))))
    return jobs


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); jobs = patches(D)
    if '--write' not in sys.argv: print('계획만'); return
    os.makedirs(OUT, exist_ok=True)
    src_dir = os.path.dirname(ROMS[1]); t1 = os.path.join(OUT, os.path.basename(ROMS[1]))
    shutil.copyfile(ROMS[1], t1)
    for f in os.listdir(src_dir):
        q = os.path.join(src_dir, f)
        if os.path.isfile(q) and f != os.path.basename(ROMS[1]) and not os.path.exists(os.path.join(OUT, f)): shutil.copyfile(q, os.path.join(OUT, f))
    dirty = set()
    with open(t1, 'r+b') as fh:
        for name, lba, size, orig, new in jobs:
            for i in range(0, size, 2048):
                if orig[i:i + 2048] == new[i:i + 2048]: continue
                s = lba + i // 2048
                fh.seek(s * 2352); sec = bytearray(fh.read(2352)); assert sec[15] == 1, ('MODE1 아님', name, s)
                sec[16:16 + 2048] = new[i:i + 2048]
                fh.seek(s * 2352); fh.write(recalc_sector(bytes(sec))); dirty.add(s)
    N = Disc.__new__(Disc); N.n = 1; N.f = open(t1, 'rb'); N.files = D.files
    for name, lba, size, orig, new in jobs: assert N.sec(lba, size // 2048) == new, ('되읽기 다름', name)
    a = open(ROMS[1], 'rb'); b = open(t1, 'rb'); bad = []
    for s in range(os.path.getsize(t1) // 2352):
        if a.read(2352) != b.read(2352) and s not in dirty: bad.append(s)
    assert not bad, ('바꾼 파일 밖 섹터가 바뀜', bad[:5])
    print('  검산 통과 · 바뀐 섹터 %d · 트랙 01 md5 %s' % (len(dirty), md5(t1)))
    if '--install' in sys.argv:
        dst = os.path.join(F_DIR, os.path.basename(ROMS[1])); assert os.path.exists(dst), dst
        shutil.copyfile(t1, dst); assert md5(dst) == md5(t1)
        print('  F: 설치(원래 폴더 트랙 01 덮어씀)', dst)


if __name__ == '__main__':
    main()
