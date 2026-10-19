from pathlib import Path
import zipfile,xml.etree.ElementTree as E,posixpath as P,copy
S=Path(r'C:\Users\victo\Downloads\CAR_bench_presentation_FIXED_backup.pptx');N=Path('work/slides-edit/newslides.pptx');D=Path('work/slides-edit/candidate.pptx')
NSP='http://schemas.openxmlformats.org/presentationml/2006/main';NSR='http://schemas.openxmlformats.org/package/2006/relationships';NSO='http://schemas.openxmlformats.org/officeDocument/2006/relationships';NSC='http://schemas.openxmlformats.org/package/2006/content-types'
E.register_namespace('p',NSP);E.register_namespace('a','http://schemas.openxmlformats.org/drawingml/2006/main');E.register_namespace('r',NSO)
with zipfile.ZipFile(S) as zs,zipfile.ZipFile(N) as zn:
 data={n:zs.read(n) for n in zs.namelist()};new={n:zn.read(n) for n in zn.namelist()};ct=E.fromstring(data['[Content_Types].xml']);nc=E.fromstring(new['[Content_Types].xml']);types={x.get('PartName').lstrip('/'):x.get('ContentType') for x in nc if x.tag.endswith('Override')};seen=set()
 def xml(e):return E.tostring(e,encoding='utf-8',xml_declaration=True)
 def relname(n):return P.join(P.dirname(n),'_rels',P.basename(n)+'.rels')
 def mapped(n):
  if n.startswith('ppt/slides/slide') and n.endswith('.xml'):return 'ppt/slides/slide'+str(22+int(P.basename(n)[5:-4]))+'.xml'
  return 'ppt/replication/'+n
 def copy_part(n):
  if n in seen:return
  seen.add(n);dest=mapped(n);data[dest]=new[n]
  if n in types:E.SubElement(ct,'{'+NSC+'}Override',PartName='/'+dest,ContentType=types[n])
  rn=relname(n)
  if rn in new:
   rel=E.fromstring(new[rn])
   for r in rel:
    if r.get('TargetMode')=='External':continue
    target=r.get('Target');target=target.lstrip('/') if target.startswith('/') else P.normpath(P.join(P.dirname(n),target))
    copy_part(target);r.set('Target',P.relpath(mapped(target),P.dirname(dest)))
   data[relname(dest)]=xml(rel)
 for i in range(1,5):copy_part(f'ppt/slides/slide{i}.xml')
 for x in nc:
  if x.tag.endswith('Default') and not any(e.tag.endswith('Default') and e.get('Extension')==x.get('Extension') for e in ct):ct.append(copy.deepcopy(x))
 pr=E.fromstring(data['ppt/presentation.xml']);rels=E.fromstring(data['ppt/_rels/presentation.xml.rels']);sl=pr.find('{'+NSP+'}sldIdLst');old=sl[19];rid=old.get('{'+NSO+'}id');sl.remove(old)
 for r in list(rels):
  if r.get('Id')==rid:rels.remove(r)
 mx=max(int(x.get('id')) for x in sl)
 for i in range(4):
  rid=f'rIdReplication{i+1}';E.SubElement(rels,'{'+NSR+'}Relationship',Id=rid,Type=NSO+'/slide',Target=f'slides/slide{i+23}.xml');e=E.Element('{'+NSP+'}sldId',{'id':str(mx+1+i),'{'+NSO+'}id':rid});sl.insert(19+i,e) if i<3 else sl.append(e)
 data['ppt/presentation.xml']=xml(pr);data['ppt/_rels/presentation.xml.rels']=xml(rels)
 data.pop('ppt/slides/slide20.xml',None);data.pop('ppt/slides/_rels/slide20.xml.rels',None)
 data.pop('ppt/notesSlides/notesSlide20.xml',None)
 data.pop('ppt/notesSlides/_rels/notesSlide20.xml.rels',None)
 for x in list(ct):
  if x.get('PartName') in ['/ppt/slides/slide20.xml','/ppt/notesSlides/notesSlide20.xml']:ct.remove(x)
 # Clarify k=3 metrics without claiming that all models have only three stored runs.
 r=E.fromstring(data['ppt/slides/slide14.xml'])
 for t in r.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
  if t.text:t.text=t.text.replace('3 repeated runs','k = 3 metrics')
 data['ppt/slides/slide14.xml']=xml(r)
 # Renumber references after the three primary slides.
 r=E.fromstring(data['ppt/slides/slide22.xml'])
 for t in r.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
  if t.text=='22':t.text='24'
 data['ppt/slides/slide22.xml']=xml(r)
 if 'docProps/app.xml' in data:
  a=E.fromstring(data['docProps/app.xml'])
  for e in a.iter():
   if e.tag.endswith('}Slides'):e.text='25'
  data['docProps/app.xml']=xml(a)
 E.register_namespace('',NSC)
 data['[Content_Types].xml']=xml(ct)
 with zipfile.ZipFile(D,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in data.items():z.writestr(n,b)
 assert len(sl)==25
 for i in [*range(1,14),*range(15,20)]:assert data[f'ppt/slides/slide{i}.xml']==zs.read(f'ppt/slides/slide{i}.xml')
 assert data['ppt/slides/slide21.xml']==zs.read('ppt/slides/slide21.xml')
 print('Merged: 25 slides; original slides except 14, replaced insights and reference footer preserved')
