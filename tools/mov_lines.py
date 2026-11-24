# -*- coding: utf-8 -*-
r"""동영상 OCR(work/ocr/ocr.tsv, 4fps) → 동영상별 고유 줄 원문 초안 work/mov_lines.tsv
  같은 줄이 여러 프레임(스크롤·정지 자막)에 나오므로 비슷한 줄끼리 묶고 가장 많이 읽힌 표기를 고른다(다수결).
  열: 동영상, 순번, 처음 프레임, 마지막 프레임, 읽힌 횟수, 원문(다수결), 다른 표기(최대 3)
  python tools/mov_lines.py"""
import collections, difflib, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JP = re.compile('[぀-ヿ一-鿿]')


def norm(s):
    return re.sub(r'\s', '', s)


def main():
    by = collections.defaultdict(list)
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'ocr.tsv'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        m, f = p[0].rsplit('_', 1)
        for ln in (p[1].split('|') if len(p) > 1 and p[1] else []):
            ln = norm(ln)
            if len(JP.findall(ln)) >= 2:
                by[m].append((int(f), ln))
    out = ['동영상\t순번\t처음\t끝\t횟수\t원문\t다른표기']
    for m in sorted(by):
        groups = []                                   # [대표, Counter, 처음, 끝]
        for f, ln in sorted(by[m]):
            best, bs = None, 0
            for g in groups:
                s = difflib.SequenceMatcher(None, ln, g[0]).ratio()
                if s > bs: best, bs = g, s
            if best is not None and bs >= 0.75:
                best[1][ln] += 1; best[3] = f; best[0] = best[1].most_common(1)[0][0]
            else:
                groups.append([ln, collections.Counter({ln: 1}), f, f])
        for i, g in enumerate(sorted(groups, key=lambda g: g[2])):
            alts = ' / '.join(t for t, _ in g[1].most_common(4)[1:])
            out.append('%s\t%d\t%d\t%d\t%d\t%s\t%s' % (m, i + 1, g[2], g[3], sum(g[1].values()), g[0], alts))
    open(os.path.join(ROOT, 'work', 'mov_lines.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(len(out) - 1, '줄')


if __name__ == '__main__':
    main()
