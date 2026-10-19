"""Add native hyperlinks absent from Artifact Tool's public authoring API.

All workbook values, styles, formulas, tables and charts were authored by Artifact
Tool. This packaging step only adds source hyperlink elements/relationships and
checks exported native structures. No source data or formula results are changed.
"""
import json
import posixpath
import sys
import zipfile
from pathlib import Path
from lxml import etree as ET

book_path, data_path, checks_path = map(Path, sys.argv[1:4])
data = json.loads(data_path.read_text())
ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
with zipfile.ZipFile(book_path) as src:
    files = {name:src.read(name) for name in src.namelist()}
workbook = ET.fromstring(files['xl/workbook.xml'])
workbook_rels = ET.fromstring(files['xl/_rels/workbook.xml.rels'])
targets={r.get('Id'):r.get('Target') for r in workbook_rels}
sheet_paths={s.get('name'):posixpath.normpath(posixpath.join('xl',targets[s.get('{'+ns['r']+'}id')])).lstrip('/') for s in workbook.find('s:sheets',ns)}
postmap={p['post_id']:p for p in data['posts']}
links={
    'Posts':[(f'I{i+2}',p['url']) for i,p in enumerate(data['posts']) if p.get('url','').startswith(('http://','https://'))],
    'Raw_Comments':[(f'K{i+2}',postmap[c['post_id']]['url']) for i,c in enumerate(data['comments']) if postmap[c['post_id']].get('url','').startswith(('http://','https://'))],
}
created=0
for sheetname, entries in links.items():
    part=sheet_paths[sheetname]
    root=ET.fromstring(files[part])
    relpart=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
    relroot=ET.fromstring(files[relpart]) if relpart in files else ET.Element('{'+ns['p']+'}Relationships',nsmap={None:ns['p']})
    hlinks=root.find('s:hyperlinks',ns)
    if hlinks is None:
        hlinks=ET.Element('{'+ns['s']+'}hyperlinks')
        # OOXML worksheet order: hyperlinks follows dataValidations and precedes
        # printOptions, margins, page setup, drawings, tableParts and extLst.
        later={'printOptions','pageMargins','pageSetup','headerFooter','rowBreaks','colBreaks','customProperties','cellWatches','ignoredErrors','smartTags','drawing','legacyDrawing','legacyDrawingHF','picture','oleObjects','controls','webPublishItems','tableParts','extLst'}
        idx=next((i for i,e in enumerate(root) if ET.QName(e).localname in later),len(root))
        root.insert(idx,hlinks)
    used={r.get('Id') for r in relroot}
    for idx,(cell,url) in enumerate(entries,1):
        ref=f'rIdSaSaSource{idx}'
        while ref in used: ref+='x'
        used.add(ref)
        ET.SubElement(relroot,'{'+ns['p']+'}Relationship',Id=ref,Type=ns['r']+'/hyperlink',Target=url,TargetMode='External')
        ET.SubElement(hlinks,'{'+ns['s']+'}hyperlink',ref=cell,attrib={'{'+ns['r']+'}id':ref})
        created+=1
    files[part]=ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    files[relpart]=ET.tostring(relroot,xml_declaration=True,encoding='UTF-8',standalone=True)

errors=[]
panes={}
for name,part in sheet_paths.items():
    root=ET.fromstring(files[part])
    for c in root.findall('.//s:c[@t="e"]',ns): errors.append({'sheet':name,'cell':c.get('r'),'value':c.findtext('s:v',namespaces=ns)})
    pane=root.find('s:sheetViews/s:sheetView/s:pane',ns)
    panes[name]=dict(pane.attrib) if pane is not None else None
chart_parts=[p for p in files if '/charts/' in p and p.endswith('.xml') and '/_rels/' not in p]
table_parts=[p for p in files if '/tables/' in p and p.endswith('.xml')]
filters=sum(ET.fromstring(files[p]).find('s:autoFilter',ns) is not None for p in table_parts)
assert not errors,errors
assert len(sheet_paths)==8,sheet_paths
assert len(chart_parts)==1,chart_parts
assert filters==7,(filters,table_parts)
assert created==len(links['Posts'])+len(links['Raw_Comments'])
check={'sheets':list(sheet_paths),'native_hyperlinks':created,'chart_parts':chart_parts,
       'native_tables':len(table_parts),'filterable_tables':filters,'freeze_panes':panes,
       'cached_formula_errors':errors,'note':'Artifact Tool calculation and exported OOXML checked; desktop Excel execution not tested.'}
temp=book_path.with_suffix('.packaging.tmp')
with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as dst:
    for name,content in files.items():dst.writestr(name,content)
temp.replace(book_path)
checks_path.write_text(json.dumps(check,ensure_ascii=False,indent=2))
print(json.dumps({'native_hyperlinks':created,'cached_errors':len(errors),'charts':len(chart_parts),'filterable_tables':filters}))
