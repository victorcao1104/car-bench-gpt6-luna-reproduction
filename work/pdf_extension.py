from pathlib import Path
import re,html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/extension'
pdfmetrics.registerFont(TTFont('ReportFont','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
styles={k:ParagraphStyle(k,fontName='ReportFont',fontSize=size,leading=lead,spaceAfter=6,wordWrap='CJK',keepWithNext=k in ['h1','h2']) for k,size,lead in [('h1',20,26),('h2',14,20),('p',10,15),('cell',8,11)]}
source=(OUT/'comparison-report.html').read_text(encoding='utf-8')
def clean(t):
 t=re.sub(r'<[^>]*>','',t)
 return html.escape(html.unescape(t))
story=[]
for m in re.finditer(r'<(h1|h2|p|ul|table)\b[^>]*>(.*?)</\1>|<img\b[^>]*>',source,re.S):
 tag,body=m.group(1),m.group(2)
 if tag in ['h1','h2','p']:
  if tag=='h2' and clean(body) in ['与论文原表比较：描述性概览','只比较题目定义相同的历史记录','这些结果支持什么结论','六轮对齐与补充重复']:story.append(PageBreak())
  story.append(Paragraph(clean(body),styles[tag]))
 elif tag=='ul':
  for item in re.findall(r'<li>(.*?)</li>',body,re.S):story.append(Paragraph('• '+clean(item),styles['p']))
 elif tag=='table':
  rows=[[Paragraph(clean(c),styles['cell']) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S)] for row in re.findall(r'<tr>(.*?)</tr>',body,re.S)]
  if rows:
   table=Table(rows,colWidths=[487/len(rows[0])]*len(rows[0]),repeatRows=1,hAlign='LEFT')
   table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf4f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dde5e5')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
   story.extend([table,Spacer(1,8)])
 else:
  name=re.search(r'alt="([^"]+)"',m.group(0)).group(1);p=OUT/(name+'.png');w,h=ImageReader(str(p)).getSize()
  story.extend([Image(str(p),width=487,height=487*h/w),Spacer(1,10)])
story.append(Paragraph('复现仓库（私有，需访问权限）：<link href="https://github.com/victorcao1104/car-bench-gpt6-luna-reproduction" color="#237c67">github.com/victorcao1104/car-bench-gpt6-luna-reproduction</link>',styles['p']))
story.append(Paragraph('完整可点击证据链接保留在随附 HTML 报告中。作者仓库：<link href="https://github.com/CAR-bench/car-bench" color="#237c67">github.com/CAR-bench/car-bench</link>',styles['p']))
def footer(canvas,doc):
 canvas.setFont('ReportFont',8);canvas.setFillColor(colors.HexColor('#667777'));canvas.drawCentredString(A4[0]/2,24,f'CAR-bench · GPT-6 Luna · 2026-10-19 | {doc.page}')
p=OUT/'CAR-bench_三类任务六轮对比报告.pdf'
SimpleDocTemplate(str(p),pagesize=A4,rightMargin=54,leftMargin=54,topMargin=45,bottomMargin=45,title='CAR-bench 三类任务六轮对比报告',author='CAR-bench reproduction').build(story,onFirstPage=footer,onLaterPages=footer)
print(p.name,p.stat().st_size)
