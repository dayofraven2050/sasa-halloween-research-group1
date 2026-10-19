"""Explicit individual coding decisions and final reproducible data merge."""
import csv, json, re, shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parents[1]/'outputs/SaSa_Section_2_2'
SUP=OUT/'support/final_revision'
DECISIONS={
 'DAlrf28Njbf':['x','u','u','T1','T1','x','T1','T1','T1','T1','T1','T1'],
 'DBCK7wjpZKe':['T8','x','x','x','T1','T1','x','x','x','T1,T3','x','x','x','x'],
 'DBHO7-1CUzs':['T1','x','T1','T8','T1','T1,T3','T2,T3','T1','T2,T3','T3','T2,T3','T3','T1','x'],
 'DBePt0ntGVD':['x','T1','T1,T2','T1','T1','T1','x','T1','T1','x','x','x','x','x','x'],
 'DPg7zL-DB7o':['T2','T1','T1,T2','T3','T1','u','T2','T1','T1','T1','T2','T3','T1','u','T2'],
 'DBHR6MPOlNY':[]}
GLOSSES={('DBCK7wjpZKe',1):'What pen is that?',('DBCK7wjpZKe',5):'Super',('DBCK7wjpZKe',6):'Magnificent. Classy. Noticeable but not too much.',
 ('DBHO7-1CUzs',4):'It was two days ago (seasonal timing comment; referent inferred from Halloween context).',('DBHO7-1CUzs',7):'What did you use to make the black liquid flow?',('DBHO7-1CUzs',8):'For someone with dark circles like me, this makeup is perfect.',
 ('DBePt0ntGVD',3):'Beautiful and easy.',('DBePt0ntGVD',9):'Cool.',('DPg7zL-DB7o',5):'I liked the third one.',('DPg7zL-DB7o',8):'Wonderful.',('DPg7zL-DB7o',10):'What an artist.'}

def main():
 SUP.mkdir(parents=True,exist_ok=True)
 d=json.loads((OUT/'support/consolidated_2026_10_20/inventory.json').read_text())
 original=json.loads((OUT/'support/analysis_data.json').read_text())
 rows=d['comments'];posts=d['posts']
 old_comments={c['comment_id']:c for c in original['comments']}
 for c in rows:
  old=old_comments.get(c['comment_id'],{})
  c['english_gloss']=old.get('english_translation','');c['engagement']=old.get('engagement_type','not_reclassified');c['purchase_evidence']=old.get('purchase_evidence','No purchase inferred; see source review')
 for p in sorted((ROOT/'data/instagram_gap_batch').glob('*.json')):
  raw=json.loads(p.read_text());short=raw['post_id'].removeprefix('instagram_');decisions=DECISIONS[short]
  assert len(decisions)==len(raw['blocks'])
  posts.append(dict(post_id=raw['post_id'],platform='Instagram',url=raw['post_url'],title=raw['selection_reason'],post_date='unknown_exact_date',date_note='Original post timestamp not exposed in this Reels view. Article year is not substituted.',method=raw['collection_method'],hk_context='not_required',source=str(p),raw_comments=len(decisions),valid_comments=0))
  if not decisions:posts[-1]['date_note']+=' Region-restricted video confirmed by screenshot; zero captured means missing comments.'
  authors={}
  for b,code in zip(raw['blocks'],decisions):
   lines=b['visible_block_text'].splitlines();user=lines[0];authors.setdefault(user,f'{short}_U{len(authors)+1:02d}')
   start=lines.index(b['visible_date_text'])+1;end=lines.index('Reply')
   if re.fullmatch(r'(Like|\d+ likes?)',lines[end-1]):end-=1
   text='\n'.join(lines[start:end]);rank=b['capture_position']
   dt=datetime.fromisoformat(b['datetime_attribute'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Hong_Kong'))
   status='excluded' if code=='x' else 'unclear' if code=='u' else 'valid'
   themes=code.split(',') if status=='valid' else []
   notes='Individual text review against saved DOM; screenshots confirm unexpanded top-level presentation. No purchases inferred.'
   if code=='x':notes='Emoji/tag/punctuation only, music request or personal fan message; excluded from substantive makeup analysis.'
   if code=='u':notes='Bare or ambiguous exclamation; no definite makeup interpretation assigned.'
   if short=='DBCK7wjpZKe' and rank==1:notes='Unspecified pen enquiry: T8 rather than asserting a cosmetic identity.'
   if short=='DPg7zL-DB7o' and rank in (7,11,15):notes='Explicit difficulty/skill concern contradicts universal ease claim; not a buying refusal.'
   rows.append(dict(comment_id=b['comment_id'],platform_comment_id=b['comment_id'],post_id=raw['post_id'],platform='Instagram',anonymous_user=authors[user],original_text=text,comment_date_original=b['visible_date_text'],exact_comment_datetime=b['datetime_attribute'],date_scope_original='2024_2026_revised_scope',level='top_level',status=status,themes=';'.join(themes),evidence_excerpt=text if status=='valid' else '',source=str(p),source_row=rank,review_notes=notes,method=raw['collection_method'],duplicate_sensitivity=False,comment_year=str(dt.year),season_relation='Sep_Oct' if dt.month in (9,10) else 'other_month',year_basis='exact timestamp',english_gloss=GLOSSES.get((short,rank),''),engagement='information_request' if any(t in themes for t in ['T3']) else 'difficulty_or_tutorial_feedback' if 'T2' in themes else 'praise_or_other',purchase_evidence='No explicit purchase intention or self-reported product purchase',review_screenshot=str(p.parent/b['review_screenshot'])))
 assert len(rows)==264 and len(posts)==24
 assert len({c['comment_id'] for c in rows})==len(rows)
 platform_ids=[c['platform_comment_id'] for c in rows if c['platform_comment_id']]
 assert len(platform_ids)==len(set(platform_ids))
 pm={p['post_id']:p for p in posts}
 for c in rows:
  c['post_url']=pm[c['post_id']]['url'];c['collection_date']='2026-10-19 to 2026-10-20 Hong Kong time'
  c['review_screenshot']=c.get('review_screenshot','')
  c['display_text']=re.sub(r'@[\w.]+','@[anonymised]',c['original_text'])
 for p in posts:
  sub=[c for c in rows if c['post_id']==p['post_id']];p['raw_comments']=len(sub);p['valid_comments']=sum(c['status']=='valid' for c in sub)
 summary=[];themes=[]
 for plat in ['Xiaohongshu','Instagram']:
  sub=[c for c in rows if c['platform']==plat];counts=Counter(c['status'] for c in sub)
  summary.append(dict(platform=plat,posts_attempted=sum(p['platform']==plat for p in posts),posts_with_comments=sum(p['platform']==plat and p['raw_comments']>0 for p in posts),raw_comments=len(sub),**{k:counts[k] for k in ['valid','excluded','unclear','pending_evidence','context_reply']}))
  for t in original['codebook']:
   match=[c for c in sub if c['status']=='valid' and t['code'] in c['themes'].split(';')]
   themes.append(dict(platform=plat,code=t['code'],theme=t['theme'],comments=len(match),posts=len({c['post_id'] for c in match}),denominator=counts['valid']))
 campaign=[
  {'finding':'Specific product and technique questions','ids':'instagram_18043406819033229; instagram_18039535139177694; instagram_18060435187776402','implication':'Retain Hero Product identification and show the application steps, shades and amount used.','boundary':'Enquiries do not demonstrate purchase intention or establish that exactly one product is sufficient.'},
  {'finding':'Three comments challenge an easy-look claim on one tutorial','ids':'instagram_18331881349233519; instagram_17882701308287511; instagram_17997080750841342','implication':'Offer beginner and advanced versions, practice guidance and realistic time estimates.','boundary':'Three comments on one post are not three independent market estimates; no causal conversion evidence.'},
  {'finding':'Limited owned makeup inventory prompts a request for tips','ids':'instagram_18360857530083720','implication':'Include an owned-product checklist and distinguish essential additions from optional upgrades.','boundary':'This comment does not explicitly reject buying or prove consumers prefer reuse.'},
  {'finding':'A coser would buy one or two additions for the desired look','ids':'INT01-S1 to INT01-S6','implication':'Explain the visible contribution of a small number of additions.','boundary':'User-provided interview summary n=1; not a transcript or general consumer estimate.'},
  {'finding':'Price enquiries in existing XHS sample concern makeup services','ids':'XHS_P01 comments; T4','implication':'Keep service demand separate from cosmetics pricing; treat service ideas as exploratory.','boundary':'No evidence that product-price objections are common. No coded waste/reuse theme does not mean no such concern exists.'},
  {'finding':'No direct evaluation of proposed AR or reward mechanisms','ids':'All reviewed comments and INT01','implication':'Keep AR, role cards and photobooth/sharing rewards as testable campaign proposals.','boundary':'Do not claim this study validates their sales effect.'}]
 d.update(summary=summary,themes=themes,posts=posts,comments=rows,codebook=original['codebook'],interview=original['interview'],campaign=campaign)
 d['scope']='2024–2026 topical material without geographic restriction; original post dates and comment dates recorded separately; unresolved dates retained as supplementary evidence.'
 d['limitations']=['Non-probability accessible sample; no population or causal inference.','36 records remain excluded from thematic denominators pending visibility/hierarchy evidence.','Dates of five new Reels posts unavailable; article year is discovery context only.','API order for six XHS posts differs methodologically from default visible browser order.','Unknown-date comments remain separately labelled; counts include supplementary undated observations.','One repeated same-user XHS posting is retained by distinct ID; sensitivity removes one valid record.','Comment authors may include creators or professional accounts; no claim that each valid comment is an independent consumer.']
 d['body']='An exploratory review of Xiaohongshu and Instagram examined Halloween makeup discussions, targeting 2024–2026 without geographic restrictions. Across 24 attempted posts, 21 yielded 264 comment or reply records; 128 substantive top-level comments were retained for thematic analysis (Appendix B). Product identification and application questions indicate information needs, while three comments on one tutorial challenged its claim of easy execution. These findings favour explicit Hero Product guidance and tutorials differentiated by skill level, rather than assuming that visual appeal alone prompts purchases. One coser interview (n=1) suggests that achieving the desired look can justify buying one or two additional products despite limited reuse. However, another commenter reported owning little makeup and requested advice. Sa Sa should therefore explain what each additional product contributes and offer practical alternatives. The accessible sample, unresolved dates and excluded evidence limit inference; neither purchase conversion nor the effectiveness of AR, role cards or sharing rewards was established.'
 assert 130<=len(d['body'].split())<=160
 assert sum(s['valid'] for s in summary)==128
 (SUP/'final_data.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 for name,records in [('raw_comments',rows),('posts',posts),('summary',summary),('themes',themes)]:
  keys=list(dict.fromkeys(k for r in records for k in r))
  with (SUP/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
 print(json.dumps({'summary':summary,'themes':themes,'body_words':len(d['body'].split())},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
