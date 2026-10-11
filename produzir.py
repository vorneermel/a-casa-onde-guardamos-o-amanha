from pathlib import Path
import re, json, html, zipfile, uuid, posixpath, subprocess
from xml.etree import ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)
TITLE = 'A Casa Onde Guardamos o Amanhã'
STEM = 'A Casa Onde Guardamos o Amanha'
W, H = 432, 648
POPPLER = Path('C:/Users/vorne/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
esc = lambda s: html.escape(s, quote=False)
source = (ROOT/'manuscrito.md').read_text(encoding='utf-8')
chapters = []
for i, part in enumerate(re.split(r'^## ', source, flags=re.M)[1:], 1):
    heading, body = part.split('\n', 1)
    paragraphs = [p.strip() for p in body.strip().split('\n\n') if p.strip()]
    chapters.append((heading, paragraphs))
    (ROOT/'capitulos').mkdir(exist_ok=True)
    (ROOT/'capitulos'/f'{i:02d}.md').write_text('# '+heading+'\n\n'+'\n\n'.join(paragraphs)+'\n', encoding='utf-8')
assert len(chapters) == 8
back = (ROOT/'contracapa.md').read_text(encoding='utf-8').strip().split('\n\n')[1:]
for name, filename in [('Georgia','georgia.ttf'),('GeorgiaBold','georgiab.ttf'),('GeorgiaItalic','georgiai.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/'+filename))
pdfmetrics.registerFontFamily('Georgia',normal='Georgia',bold='GeorgiaBold',italic='GeorgiaItalic',boldItalic='GeorgiaBold')
green, cream, gold = map(HexColor, ['#244337','#f4eedf','#bfa774'])
styles = {
 'body': ParagraphStyle('body',fontName='Georgia',fontSize=11,leading=14.8,alignment=TA_JUSTIFY,firstLineIndent=16,spaceAfter=4,allowWidows=0,allowOrphans=0),
 'first': ParagraphStyle('first',fontName='Georgia',fontSize=11,leading=14.8,alignment=TA_JUSTIFY,spaceAfter=4,allowWidows=0,allowOrphans=0),
 'label': ParagraphStyle('label',fontName='Georgia',fontSize=10,leading=15,alignment=TA_CENTER,textColor=green,spaceAfter=18),
 'chapter': ParagraphStyle('chapter',fontName='GeorgiaBold',fontSize=21,leading=28,alignment=TA_CENTER,textColor=green,spaceAfter=28),
 'title': ParagraphStyle('title',fontName='Georgia',fontSize=34,leading=42,alignment=TA_CENTER,textColor=green),
 'toc': ParagraphStyle('toc',fontName='Georgia',fontSize=11.5,leading=18,spaceAfter=12),
 'back': ParagraphStyle('back',fontName='Georgia',fontSize=12.5,leading=19.5,textColor=cream,spaceAfter=18),
}

def cover(c):
    c.drawImage(str(ROOT/'arte-capa.png'),0,0,W,H)
    c.setFillColor(green)
    c.setFont('Georgia',31)
    for y,line in [(H-53,'A Casa Onde'),(H-91,'Guardamos'),(H-129,'o Amanhã')]:
        c.drawCentredString(W/2,y,line)
    c.setFont('Georgia',9)
    c.drawCentredString(W/2,H-153,'CONTO')

c=canvas.Canvas(str(ROOT/'capa.pdf'),pagesize=(W,H))
c.setTitle(TITLE); c.setAuthor(''); cover(c); c.showPage(); c.save()
c=canvas.Canvas(str(ROOT/'contracapa.pdf'),pagesize=(W,H))
c.setTitle('Contracapa | '+TITLE); c.setAuthor('')
c.setFillColor(green); c.rect(0,0,W,H,fill=1,stroke=0)
c.setStrokeColor(gold); c.setLineWidth(.7); c.rect(28,28,W-56,H-56,fill=0,stroke=1)
c.setFillColor(cream); c.setFont('Georgia',22)
for y,line in [(H-67,'A Casa Onde'),(H-97,'Guardamos o Amanhã')]: c.drawCentredString(W/2,y,line)
c.setStrokeColor(gold); c.line(160,H-121,272,H-121)
y=H-158
for p in back:
    para=Paragraph(esc(p),styles['back']); _,ph=para.wrap(W-104,H)
    assert y-ph>43, 'Texto de contracapa excedeu area segura'
    para.drawOn(c,52,y-ph); y-=ph+18
c.showPage();c.save()
for name in ['capa','contracapa']:
    subprocess.run([str(POPPLER),'-singlefile','-f','1','-r','200','-png',str(ROOT/f'{name}.pdf'),str(ROOT/name)],check=True,capture_output=True)

class BookDoc(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if hasattr(flowable,'chapter_id'):
            key=flowable.chapter_id
            self.chapter_pages[key]=self.page
            self.canv.bookmarkPage(key)

def footer(c,doc):
    if doc.page>2:
        c.setFont('Georgia',8);c.setFillColor(green);c.drawCentredString(W/2,24,str(doc.page-2))

story=[Spacer(1,120),Paragraph('A Casa Onde<br/>Guardamos o Amanhã',styles['title']),Spacer(1,30),Paragraph('CONTO',styles['label']),PageBreak(),Paragraph('Sumário',styles['chapter']),Spacer(1,15)]
for i,(heading,_) in enumerate(chapters,1):
    story.append(Paragraph(esc(heading),styles['toc']))
story.append(PageBreak())
for i,(heading,paragraphs) in enumerate(chapters,1):
    _,name=heading.split('. ',1)
    story.extend([Spacer(1,6 if i==3 else 22),Paragraph(f'CAPÍTULO {i}',styles['label'])])
    chapter_style=ParagraphStyle('chapterCompact',parent=styles['chapter'],spaceAfter=8) if i==3 else styles['chapter']
    h=Paragraph(esc(name),chapter_style);h.chapter_id=f'ch{i}';story.append(h)
    for j,p in enumerate(paragraphs): story.append(Paragraph(esc(p),styles['first' if j==0 or p.startswith('—') else 'body']))
    if i<len(chapters):story.append(PageBreak())
doc=BookDoc(str(TMP/'miolo.pdf'),pagesize=(W,H),leftMargin=47,rightMargin=47,topMargin=44,bottomMargin=44,title=TITLE,author='')
doc.chapter_pages={}
doc.build(story,onFirstPage=footer,onLaterPages=footer)
writer=PdfWriter()
for path in [ROOT/'capa.pdf',TMP/'miolo.pdf',ROOT/'contracapa.pdf']:writer.append(str(path),import_outline=False)
for i,(heading,_) in enumerate(chapters,1):writer.add_outline_item(heading,doc.chapter_pages[f'ch{i}'])
writer.add_metadata({'/Title':TITLE,'/Author':'','/Subject':'Conto sobre infância, amizade e memória','/Creator':'Preparação editorial com IA'})
with (ROOT/f'{STEM}.pdf').open('wb') as f:writer.write(f)

CSS='body{font-family:serif;line-height:1.5;margin:5%;}h1{text-align:center;font-weight:normal;line-height:1.25;margin:1.5em 0;}p{text-indent:1.2em;margin:0 0 .4em;}p.first,p.dialogue{text-indent:0;}nav li{margin:.6em 0;}.cover{text-align:center;margin:0;}.cover img{max-width:100%;height:auto;}.label{text-indent:0;text-align:center;}'
def xhtml(title,body):
    return f'<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR" xml:lang="pt-BR"><head><title>{esc(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body>{body}</body></html>'
files={'OEBPS/style.css':CSS,'OEBPS/cover.xhtml':xhtml(TITLE,'<section class="cover" epub:type="cover"><img src="cover.png" alt="Capa: A Casa Onde Guardamos o Amanhã; duas crianças diante de uma casa na mangueira"/></section>'),'OEBPS/title.xhtml':xhtml(TITLE,f'<section epub:type="titlepage"><h1>{TITLE}</h1><p class="label">CONTO</p></section>')}
toc=[]
for i,(heading,paragraphs) in enumerate(chapters,1):
    elements=[]
    for j,p in enumerate(paragraphs):
        cl='dialogue' if p.startswith('—') else 'first' if j==0 else ''
        elements.append(f'<p class="{cl}">{esc(p)}</p>')
    files[f'OEBPS/ch{i}.xhtml']=xhtml(heading,f'<section epub:type="chapter" id="ch{i}"><h1>{esc(heading)}</h1>'+''.join(elements)+'</section>')
    toc.append(f'<li><a href="ch{i}.xhtml">{esc(heading)}</a></li>')
files['OEBPS/back.xhtml']=xhtml('Sobre a história','<h1>Sobre a história</h1>'+''.join(f'<p>{esc(p)}</p>' for p in back))
files['OEBPS/nav.xhtml']=xhtml('Sumário','<nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>'+''.join(toc)+'</ol></nav><nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="bodymatter" href="ch1.xhtml">Início da história</a></li></ol></nav>')
bookid='urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_URL,'A-Casa-Onde-Guardamos-o-Amanha-2026-10-11'))
points=''.join(f'<navPoint id="nav{i}" playOrder="{i}"><navLabel><text>{esc(h)}</text></navLabel><content src="ch{i}.xhtml"/></navPoint>' for i,(h,_) in enumerate(chapters,1))
files['OEBPS/toc.ncx']=f'<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="{bookid}"/></head><docTitle><text>{TITLE}</text></docTitle><navMap>{points}</navMap></ncx>'
manifest='<item id="cover-image" href="cover.png" media-type="image/png" properties="cover-image"/><item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="back" href="back.xhtml" media-type="application/xhtml+xml"/>'+''.join(f'<item id="ch{i}" href="ch{i}.xhtml" media-type="application/xhtml+xml"/>' for i in range(1,9))
spine='<itemref idref="cover" linear="no"/><itemref idref="title"/><itemref idref="nav"/>'+''.join(f'<itemref idref="ch{i}"/>' for i in range(1,9))+'<itemref idref="back"/>'
files['OEBPS/content.opf']=f'<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0" xml:lang="pt-BR"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">{bookid}</dc:identifier><dc:title>{TITLE}</dc:title><dc:language>pt-BR</dc:language><dc:description>Conto sobre Miguel, Clara e uma casa na árvore que atravessa gerações pela memória.</dc:description><meta property="dcterms:modified">2026-10-11T00:00:00Z</meta><meta name="cover" content="cover-image"/></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>'
files['META-INF/container.xml']='<?xml version="1.0" encoding="utf-8"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
with zipfile.ZipFile(ROOT/f'{STEM}.epub','w') as z:
    z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
    for name,content in files.items():z.writestr(name,content.encode('utf-8'),compress_type=zipfile.ZIP_DEFLATED)
    z.write(ROOT/'capa.png','OEBPS/cover.png',compress_type=zipfile.ZIP_DEFLATED)

with zipfile.ZipFile(ROOT/f'{STEM}.epub') as z:
    assert z.testzip() is None
    assert z.infolist()[0].filename=='mimetype' and z.infolist()[0].compress_type==0
    for name in z.namelist():
        if name.endswith(('.xml','.opf','.ncx','.xhtml')):ET.fromstring(z.read(name))
    for i,(_,paragraphs) in enumerate(chapters,1):
        tree=ET.fromstring(z.read(f'OEBPS/ch{i}.xhtml'))
        assert [''.join(p.itertext()) for p in tree.findall('.//{http://www.w3.org/1999/xhtml}p')]==paragraphs
    for name in z.namelist():
        if name.endswith(('.xhtml','.opf','.ncx')):
            for el in ET.fromstring(z.read(name)).iter():
                for attr in ['href','src']:
                    ref=el.get(attr)
                    if ref and not ref.startswith(('http:','https:','#')):
                        assert posixpath.normpath(posixpath.join(posixpath.dirname(name),ref.split('#')[0])) in z.namelist()
reader=PdfReader(ROOT/f'{STEM}.pdf')
normalize=lambda s:re.sub(r'\s+','',s)
pdftext=''.join(normalize(re.sub(r'(?m)^\s*\d+\s*$','',p.extract_text() or '')) for p in reader.pages)
offset=0
for _,paragraphs in chapters:
    for p in paragraphs:
        pos=pdftext.find(normalize(p),offset)
        assert pos>=0, 'Parágrafo ausente ou fora de ordem: '+p[:70]
        offset=pos+len(normalize(p))
words=len(re.findall(r'\b[\w]+(?:[-’][\w]+)*\b','\n'.join('\n'.join(p) for _,p in chapters)))
report={'titulo':TITLE,'capitulos':8,'palavras_da_narrativa':words,'minutos_a_180_palavras_por_minuto':round(words/180,1),'faixa_a_180_220_palavras_por_minuto':[round(words/220,1),round(words/180,1)],'paginas_pdf':len(reader.pages),'aberturas_pdf_paginas_fisicas':[doc.chapter_pages[f'ch{i}']+1 for i in range(1,9)],'epub_zip_xml_links_paragrafos':'PASSOU','pdf_todos_paragrafos_presentes_em_ordem':'PASSOU','epubcheck':'NAO EXECUTADO','kindle_previewer':'NAO EXECUTADO','autoria':'Não informada; omitida','backup_publico':'Repositório público criado; confirmar SHA remoto após envio dos arquivos gerados'}
(ROOT/'validacao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
