#!/usr/bin/env python3
"""Build the Mark study book HTML from data/*.json."""
import json, re, sys, glob, html
from pypinyin import pinyin, Style, load_phrases_dict, load_single_dict

# Corrections for polyphones / proper names (phrase -> pinyin per char)
PHRASES = json.load(open('data/pinyin_fix.json', encoding='utf-8'))
load_phrases_dict({k: [[p] for p in v.split()] for k, v in PHRASES.items() if len(k) > 1})
from pypinyin.constants import PINYIN_DICT
load_single_dict({ord(k): v for k, v in PHRASES.items() if len(k) == 1})

CJK = re.compile(r'[一-鿿]')
esc = html.escape

MULTI = sorted([(k, v.split()) for k, v in PHRASES.items() if len(k) > 1], key=lambda x: -len(x[0]))

def py_list(s):
    out = [x[0] for x in pinyin(s, style=Style.TONE, errors=lambda c: [[ch] for ch in c])]
    if len(out) != len(s):
        return out
    done = [False] * len(s)
    for k, v in MULTI:
        if len(v) != len(k): continue
        for m in re.finditer(re.escape(k), s):
            for i in range(len(k)):
                if not done[m.start() + i]:
                    out[m.start() + i] = v[i]; done[m.start() + i] = True
    return out

def ruby(s):
    out = []
    flat = py_list(s)
    # pinyin returns one item per CJK char and one per non-CJK char with errors fn
    i = 0
    for ch in s:
        if CJK.match(ch):
            out.append(f'<ruby>{ch}<rt>{esc(flat[i])}</rt></ruby>')
        else:
            out.append(f'<span class="p">{esc(ch)}</span>')
        i += 1
    return ''.join(out)

def word_py(w):
    return ' '.join(py_list(w))

def mark_notes(en, notes, start):
    """insert superscript numbers after first match of each note term"""
    spans = []
    n = start
    numbered = []
    for note in notes:
        term, gloss = note[0], note[1]
        match = note[2] if len(note) > 2 else term
        m = re.search(r'\b' + re.escape(match) + r"[\w']*", en, re.I)
        n += 1
        numbered.append((n, term, gloss))
        if m and not any(a < m.end() and m.start() < b for a, b, _ in spans):
            spans.append((m.start(), m.end(), n))
    spans.sort()
    out, last = [], 0
    for a, b, k in spans:
        out.append(esc(en[last:a]))
        out.append(f'<span class="w">{esc(en[a:b])}</span><sup>{k})</sup>')
        last = b
    out.append(esc(en[last:]))
    return ''.join(out), numbered, n

CN_NUM = '〇一二三四五六七八九十'
def cnum(n):
    if n <= 10: return CN_NUM[n]
    if n < 20: return '十' + CN_NUM[n - 10]
    return CN_NUM[n // 10] + '十' + (CN_NUM[n % 10] if n % 10 else '')

def section_html(sec, sid):
    parts = []
    parts.append(f'''<section class="peri" id="{sid}">
<header class="peri-h">
 <div class="peri-ref">马尔谷福音 第{cnum(sec["ch"])}章 · 마르코 {sec["ch"]},{sec["range"]}</div>
 <h2 class="zh">{ruby(sec["title_zh"])}</h2>
 <div class="peri-sub"><span class="en">{esc(sec["title_en"])}</span><span class="ko">{esc(sec["title_ko"])}</span></div>
</header>''')
    fn = 0
    for v in sec['verses']:
        en_html, numbered, fn = mark_notes(v['en'], v.get('notes', []), fn)
        vocab_rows = ''.join(
            f'<tr><td class="vw"><button class="say" data-l="zh" data-s="{esc(w[0].replace("……",""))}">🔊</button>{esc(w[0])}</td><td class="vp">{esc(w[2] if len(w) > 2 else word_py(w[0]))}</td><td class="vm">{esc(w[1])}</td></tr>'
            for w in v.get('vocab', []))
        notes_html = ''.join(
            f'<li><b>{k})</b> <button class="say" data-l="en" data-s="{esc(t)}">🔊</button><span class="nt">{esc(t)}</span>{(" <span class=ipa>" + esc(IPA[t]) + "</span>") if t in IPA else ""} : {esc(g)}</li>' for k, t, g in numbered)
        gram = ''
        for g in v.get('grammar', []):
            exs = ''.join(
                f'<div class="gx"><div class="zh">{ruby(e[0])}</div><div class="gk">{esc(e[1])}</div></div>'
                for e in g['ex'])
            gram += f'<div class="gram"><div class="gt">语法 · {esc(g["title"])}</div><div class="gd">{esc(g["desc"])}</div>{exs}</div>'
        parts.append(f'''<article class="verse" id="{sid}-v{v["v"]}">
 <div class="band"><div class="num">{v["v"]}<button class="say big" data-l="zh" data-s="{esc(v["zh"])}" title="중국어 듣기">🔊</button></div><div class="zh big">{ruby(v["zh"])}</div></div>
 <div class="two">
  <div class="col"><div class="lab">{"NAB" if v["en_src"]=="NAB" else "CCB · 임시 (NAB로 교체 예정)"} <button class="say" data-l="en" data-s="{esc(v["en"])}">🔊</button></div><p class="en{"" if v["en_src"]=="NAB" else " tmp"}">{en_html}</p></div>
  <div class="col ko-col"><div class="lab">성경</div><p class="ko">{esc(v["ko"])}</p></div>
 </div>
 <div class="two lower">
  <div class="col"><div class="lab">生词 · 단어</div><table class="vocab">{vocab_rows}</table></div>
  {f'<div class="col"><div class="lab">English Words</div><ol class="notes">{notes_html}</ol></div>' if numbered else '<div class="col empty"><div class="lab">English Words</div><p class="pend">이 절에는 영어 단어 각주가 없습니다.</p></div>'}
 </div>
 {gram}
</article>''')
    parts.append('</section>')
    return '\n'.join(parts)

TEXTS = json.load(open('data/texts.json', encoding='utf-8'))
IPA = json.load(open('data/ipa.json', encoding='utf-8'))
NOTES = {}
for line in open('data/notes.txt', encoding='utf-8'):
    line = line.strip()
    if not line: continue
    key, rest = line.split(' ', 1)
    lst = []
    for ent in rest.split(' ; '):
        m = re.match(r'^(.+?) \[(.+?)\] (.+?)(?: \{(.+)\})?$', ent.strip())
        if not m: raise SystemExit('bad note: ' + ent)
        term, ipa, gloss, match = m.groups()
        IPA.setdefault(term, '/' + ipa + '/')
        lst.append([term, gloss] + ([match] if match else []))
    NOTES[key] = lst
FIX = [('詑', '诧'), ('唾沬', '唾沫'), ('《依撒意亚书上》', '《依撒意亚书》上'), ('握往', '握住'), ('È’', ''), ('祇', '只')]

def fill(sec):
    for v in sec['verses']:
        t = TEXTS.get(f"{sec['ch']}:{v['v']}", {})
        if 'zh' not in v: v['zh'] = t.get('zh', '')
        for a, b in FIX: v['zh'] = v['zh'].replace(a, b)
        if 'ko' not in v: v['ko'] = t.get('ko', '')
        if 'en' in v: v['en_src'] = 'NAB'
        elif t.get('en_nab'): v['en'] = t['en_nab']; v['en_src'] = 'NAB'
        else: v['en'] = t.get('en_ccb', ''); v['en_src'] = 'CCB'
        if 'notes' not in v: v['notes'] = NOTES.get(f"{sec['ch']}:{v['v']}", [])
    return sec

def build(files, out):
    secs = []
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        secs += d if isinstance(d, list) else [d]
    secs = [fill(s) for s in secs]
    secs.sort(key=lambda s: (s['ch'], int(re.match(r'\d+', s['range']).group())))
    nav, body = [], []
    curch = None
    for i, s in enumerate(secs):
        sid = f'mk{s["ch"]}-{s["range"]}'
        if s['ch'] != curch:
            if curch is not None: nav.append('</div>')
            nav.append(f'<div class="navch"><div class="navct">第{cnum(s["ch"])}章 · {s["ch"]}장</div>')
            curch = s['ch']
        nav.append(f'<a href="#{sid}"><span>{s["ch"]},{s["range"]}</span> {esc(s["title_ko"])}</a>')
        body.append(section_html(s, sid))
    nav.append('</div>')
    tpl = open('tools/template.html', encoding='utf-8').read()
    page = tpl.replace('{{NAV}}', '\n'.join(nav)).replace('{{BODY}}', '\n'.join(body))
    open(out, 'w', encoding='utf-8').write(page)
    print('wrote', out, len(secs), 'sections', sum(len(s['verses']) for s in secs), 'verses')

if __name__ == '__main__':
    build(sorted(glob.glob('data/mk*.json')), sys.argv[1] if len(sys.argv) > 1 else 'index.html')
