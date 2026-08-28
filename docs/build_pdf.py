# -*- coding: utf-8 -*-
import re, os, sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth, registerFontFamily
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, PageBreak, Table, TableStyle, XPreformatted,
                                NextPageTemplate)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.tableofcontents import TableOfContents

SRC = r"C:\Users\Harshitha\AI_Director\docs\ai_director_overview.md"
OUT = r"C:\Users\Harshitha\AI_Director\AI_Director_Project_Overview_v2.0.pdf"
FONTS = r"C:\Windows\Fonts"
DEJAVU = r"C:\Users\Harshitha\anaconda3\Lib\site-packages\matplotlib\mpl-data\fonts\ttf"

PAGE_W, PAGE_H = A4
MARGIN = 72
USABLE = PAGE_W - 2 * MARGIN

# ---------------------------------------------------------------- fonts
pdfmetrics.registerFont(TTFont('Georgia', os.path.join(FONTS, 'georgia.ttf')))
pdfmetrics.registerFont(TTFont('Georgia-Bold', os.path.join(FONTS, 'georgiab.ttf')))
pdfmetrics.registerFont(TTFont('Georgia-Italic', os.path.join(FONTS, 'georgiai.ttf')))
pdfmetrics.registerFont(TTFont('Georgia-BoldItalic', os.path.join(FONTS, 'georgiaz.ttf')))
pdfmetrics.registerFont(TTFont('Consolas', os.path.join(FONTS, 'consola.ttf')))
pdfmetrics.registerFont(TTFont('Consolas-Bold', os.path.join(FONTS, 'consolab.ttf')))
pdfmetrics.registerFont(TTFont('DejaVuSans', os.path.join(DEJAVU, 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', os.path.join(DEJAVU, 'DejaVuSans-Bold.ttf')))
registerFontFamily('Georgia', normal='Georgia', bold='Georgia-Bold',
                   italic='Georgia-Italic', boldItalic='Georgia-BoldItalic')
registerFontFamily('Consolas', normal='Consolas', bold='Consolas-Bold')
registerFontFamily('DejaVuSans', normal='DejaVuSans', bold='DejaVuSans-Bold')

# ---------------------------------------------------------------- styles
def st(name, **kw):
    return ParagraphStyle(name, **kw)

body = st('Body', fontName='Georgia', fontSize=11, leading=15.4, alignment=TA_JUSTIFY,
          spaceBefore=0, spaceAfter=6, textColor=colors.HexColor('#1A1A1A'))
bodyC = st('BodyC', parent=body, alignment=TA_CENTER)
h1 = st('H1', fontName='Georgia-Bold', fontSize=18, leading=22, alignment=TA_LEFT,
        spaceBefore=0, spaceAfter=8, keepWithNext=1, textColor=colors.HexColor('#1F3864'))
h2 = st('H2', fontName='Georgia-Bold', fontSize=14, leading=17.5, alignment=TA_LEFT,
        spaceBefore=12, spaceAfter=5, keepWithNext=1, textColor=colors.HexColor('#2E4A79'))
h3 = st('H3', fontName='Georgia-Bold', fontSize=12, leading=15, alignment=TA_LEFT,
        spaceBefore=10, spaceAfter=4, keepWithNext=1, textColor=colors.HexColor('#3A5A8C'))
bullet = st('Bullet', parent=body, leftIndent=18, bulletIndent=6, alignment=TA_LEFT)
quote = st('Quote', fontName='Georgia-Italic', fontSize=10.5, leading=14.5,
           leftIndent=16, rightIndent=10, spaceBefore=6, spaceAfter=6,
           textColor=colors.HexColor('#333333'))
cellHead = st('CellHead', fontName='Georgia-Bold', fontSize=9.5, leading=12,
              textColor=colors.HexColor('#1F3864'))
cellBody = st('CellBody', fontName='Georgia', fontSize=9.5, leading=12.5,
              textColor=colors.HexColor('#1A1A1A'))
codeStyle = st('Code', fontName='Consolas', fontSize=8, leading=9.6,
               leftIndent=0, rightIndent=0, textColor=colors.HexColor('#111111'))
tocLevel0 = st('TOC0', fontName='Georgia', fontSize=11, leading=15.5, leftIndent=14,
               firstLineIndent=-8, spaceBefore=2, spaceAfter=2)
tocTitle = st('TocTitle', fontName='Georgia-Bold', fontSize=18, leading=22,
              alignment=TA_CENTER, spaceAfter=16, textColor=colors.HexColor('#1F3864'))

# ---------------------------------------------------------------- markup
def inline(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', t)
    t = re.sub(r'`([^`]+)`', r'<font name="Consolas">\1</font>', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = t.replace('\u2192', '<font name="DejaVuSans">\u2192</font>')
    t = t.replace('\u2714', '<font name="DejaVuSans">\u2714</font>')
    return t

# ---------------------------------------------------------------- parse
with open(SRC, 'r', encoding='utf-8') as fh:
    raw = fh.read()
lines = raw.split('\n')

# front matter ends at first standalone `---`
cover_lines, body_lines = [], []
seen_hr = False
for ln in lines:
    if not seen_hr and ln.strip() == '---':
        seen_hr = True
        continue
    if seen_hr:
        body_lines.append(ln)
    else:
        cover_lines.append(ln)

# ---- parse blocks: returns list of (kind, data)
def parse_blocks(src):
    blocks = []
    para = []
    table = None
    def flush_para():
        if para:
            blocks.append(('para', ' '.join(p.strip() for p in para if p.strip())))
            para.clear()
    def flush_table():
        nonlocal table
        if table:
            blocks.append(('table', table))
            table = None
    i = 0
    n = len(src)
    while i < n:
        ln = src[i].rstrip('\n')
        s = ln.strip()
        if s == '':
            flush_para(); flush_table(); i += 1; continue
        if s == '---':
            flush_para(); flush_table(); blocks.append(('hr', None)); i += 1; continue
        if s.startswith('```'):
            flush_para(); flush_table()
            i += 1
            code = []
            while i < n and not src[i].strip().startswith('```'):
                code.append(src[i].rstrip('\n'))
                i += 1
            i += 1
            blocks.append(('code', code))
            continue
        if s.startswith('|'):
            flush_para()
            row = [c.strip() for c in s.strip('|').split('|')]
            if table is None:
                table = []
            table.append(row)
            i += 1
            continue
        if s.startswith('#'):
            flush_para(); flush_table()
            m = re.match(r'^(#{1,3})\s+(.*)$', s)
            lvl = len(m.group(1)); text = m.group(2).strip()
            blocks.append(('h%d' % lvl, text))
            i += 1
            continue
        if s.startswith('>'):
            flush_para(); flush_table()
            q = []
            while i < n and src[i].strip().startswith('>'):
                q.append(src[i].strip()[1:].strip())
                i += 1
            blocks.append(('quote', ' '.join(q)))
            continue
        if re.match(r'^-\s+', s):
            flush_para(); flush_table()
            items = []
            while i < n and re.match(r'^-\s+', src[i].strip()):
                items.append(('bullet', re.sub(r'^-\s+', '', src[i].strip())))
                i += 1
            blocks.append(('list', items))
            continue
        if re.match(r'^\d+\.\s+', s):
            flush_para(); flush_table()
            items = []
            while i < n and re.match(r'^\d+\.\s+', src[i].strip()):
                m = re.match(r'^(\d+)\.\s+(.*)$', src[i].strip())
                items.append(('num', m.group(1), m.group(2)))
                i += 1
            blocks.append(('list', items))
            continue
        para.append(ln)
        i += 1
    flush_para(); flush_table()
    return blocks

body_blocks = parse_blocks(body_lines)

# ---------------------------------------------------------------- cover fields
cover_table_rows = []
for blk in parse_blocks(cover_lines):
    if blk[0] == 'table':
        cover_table_rows = blk[1]
    if blk[0] == 'quote':
        cover_quote = blk[1]
    if blk[0] == 'para':
        cover_motto = blk[1]

COVER_VERSION = '2.0'
COVER_DATE = 'July 31, 2026'
for r in cover_table_rows:
    if len(r) >= 2:
        if r[0].strip() == '**Version**': COVER_VERSION = r[1].strip()
        if r[0].strip() == '**Date**': COVER_DATE = r[1].strip()

# ---------------------------------------------------------------- tables
def is_sep(row):
    return len(row) > 0 and all(re.fullmatch(r':?-+:?', c) for c in row)

def natural_width(text, font='Georgia', size=9.5, padding=14):
    t = re.sub(r'<[^>]+>', '', text)
    return stringWidth(t, font, size) + padding

def col_widths(table, usable, max_col=300, min_col=40):
    ncols = max(len(r) for r in table)
    widths = [0.0] * ncols
    for r in table:
        for c in range(ncols):
            txt = r[c] if c < len(r) else ''
            if c == 0:
                w = natural_width(txt, 'Georgia-Bold', 9.5, 16)
            else:
                w = natural_width(txt, 'Georgia', 9.5, 14)
            widths[c] = max(widths[c], w)
    widths = [min(w, max_col) for w in widths]
    total = sum(widths)
    if total > usable:
        widths = [max(min_col, w * usable / total) for w in widths]
        total = sum(widths)
    # distribute remainder exactly
    if total < usable:
        widths[-1] += usable - total
    return widths

def table_flowable(table):
    data = [r for r in table if not is_sep(r)]
    if not data:
        return Spacer(1, 6)
    ncols = max(len(r) for r in data)
    rows = [r + [''] * (ncols - len(r)) for r in data]
    widths = col_widths(rows, USABLE)
    is_head = is_sep(table[1]) if len(table) > 1 else False
    cells = []
    start = 0
    if is_head:
        cells.append([Paragraph(inline(rows[0][c]), cellHead) for c in range(ncols)])
        start = 1
    for r in rows[start:]:
        cells.append([Paragraph(inline(r[c]), cellBody) for c in range(ncols)])
    t = Table(cells, colWidths=widths, repeatRows=1 if is_head else 0, hAlign='LEFT')
    style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#BBBBBB')),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    if is_head:
        style.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8EDF4')))
    t.setStyle(TableStyle(style))
    return t

def code_flowable(code_lines):
    text = '\n'.join(code_lines)
    xp = XPreformatted(text, codeStyle)
    t = Table([[xp]], colWidths=[USABLE - 12], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F6F6F6')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t

# ---------------------------------------------------------------- cover
def cover_flowables():
    flow = []
    flow.append(Spacer(1, 60))
    flow.append(Paragraph('AI DIRECTOR', st('cvTitle', fontName='Georgia-Bold', fontSize=34,
                                            leading=40, alignment=TA_CENTER,
                                            textColor=colors.HexColor('#1F3864'))))
    flow.append(Spacer(1, 8))
    flow.append(Paragraph('Project Overview Document', st('cvSub', fontName='Georgia-Bold', fontSize=17,
                                                          leading=22, alignment=TA_CENTER,
                                                          textColor=colors.HexColor('#333333'))))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(inline('*AI-Powered Social Media Video Production Platform*'),
                          st('cvTag', fontName='Georgia-Italic', fontSize=13, leading=17,
                             alignment=TA_CENTER, textColor=colors.HexColor('#555555'))))
    flow.append(Spacer(1, 26))
    flow.append(Paragraph(inline(cover_motto), st('cvMotto', fontName='Georgia-Italic', fontSize=11.5,
                                                  leading=16, alignment=TA_CENTER,
                                                  textColor=colors.HexColor('#444444'))))
    flow.append(Spacer(1, 34))
    rows = []
    for r in cover_table_rows:
        if len(r) >= 2 and not is_sep(r):
            rows.append([Paragraph(inline(r[0]), st('cvLab', fontName='Georgia-Bold', fontSize=10.5,
                                                    leading=14, alignment=TA_RIGHT,
                                                    textColor=colors.HexColor('#1F3864'))),
                         Paragraph(inline(r[1]), st('cvVal', fontName='Georgia', fontSize=10.5,
                                                    leading=14, alignment=TA_LEFT,
                                                    textColor=colors.HexColor('#1A1A1A')))])
    if rows:
        t = Table(rows, colWidths=[150, 240], hAlign='CENTER')
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.4, colors.HexColor('#CCCCCC')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        flow.append(t)
    flow.append(Spacer(1, 60))
    flow.append(Paragraph(inline(cover_quote), st('cvNote', fontName='Georgia-Italic', fontSize=8.5,
                                                  leading=11.5, alignment=TA_CENTER,
                                                  textColor=colors.HexColor('#666666'))))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph('Confidential \u2014 Internal Review', st('cvConf', fontName='Georgia-Italic',
                                                                    fontSize=9, leading=12,
                                                                    alignment=TA_CENTER,
                                                                    textColor=colors.HexColor('#888888'))))
    return flow

# ---------------------------------------------------------------- doc
class Doc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4, **kw)
        self._h1 = 0
        self._h2 = 0
        frame = Frame(MARGIN, MARGIN, USABLE, PAGE_H - 2 * MARGIN, id='main')
        self.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=self._deco)])

    def _deco(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFont('Georgia', 9)
            canvas.setFillColor(colors.HexColor('#444444'))
            canvas.drawCentredString(PAGE_W / 2, PAGE_H - 50, 'AI Director \u2013 Project Overview')
            canvas.setStrokeColor(colors.HexColor('#CCCCCC'))
            canvas.setLineWidth(0.5)
            canvas.line(MARGIN, PAGE_H - 54, PAGE_W - MARGIN, PAGE_H - 54)
            canvas.setFont('Georgia', 9)
            canvas.drawString(MARGIN, 40, 'AI Director Project Overview v2.0')
            canvas.drawCentredString(PAGE_W / 2, 40, str(doc.page))
        canvas.restoreState()

    def _startBuild(self, filename=None, canvasmaker=None):
        self._h1 = 0
        self._h2 = 0
        return super()._startBuild(filename, canvasmaker=canvasmaker)

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name == 'H1':
                text = flowable.getPlainText()
                key = 'sec%d' % self._h1
                self._h1 += 1
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (0, text, self.page, key))
                self.canv.addOutlineEntry(text, key, level=0, closed=False)
            elif name == 'H2':
                text = flowable.getPlainText()
                key = 'sub%d' % self._h2
                self._h2 += 1
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=1, closed=False)

# ---------------------------------------------------------------- story
story = []

# cover
story += cover_flowables()
story.append(PageBreak())

# TOC page
toc = TableOfContents()
toc.levelStyles = [tocLevel0]
toc.dotsMinLevel = 0
story.append(Paragraph('Table of Contents', tocTitle))
story.append(toc)
story.append(PageBreak())

# body
first_h1 = True
for kind, data in body_blocks:
    if kind == 'h1':
        if not first_h1:
            story.append(PageBreak())
        first_h1 = False
        story.append(Paragraph(inline(data), h1))
    elif kind == 'h2':
        story.append(Paragraph(inline(data), h2))
    elif kind == 'h3':
        story.append(Paragraph(inline(data), h3))
    elif kind == 'para':
        story.append(Paragraph(inline(data), body))
    elif kind == 'table':
        story.append(table_flowable(data))
    elif kind == 'code':
        story.append(code_flowable(data))
        story.append(Spacer(1, 4))
    elif kind == 'quote':
        story.append(Paragraph(inline(data), quote))
    elif kind == 'list':
        for item in data:
            if item[0] == 'bullet':
                story.append(Paragraph(inline(item[1]), bullet, bulletText='\u2022'))
            else:
                story.append(Paragraph(inline(item[2]), bullet, bulletText='%s.' % item[1]))
    elif kind == 'hr':
        story.append(Spacer(1, 8))

doc = Doc(OUT)
doc.multiBuild(story)
print('OK: %s' % OUT)
print('H1 entries: %d, H2 entries: %d' % (doc._h1, doc._h2))
