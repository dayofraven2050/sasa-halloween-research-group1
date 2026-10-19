"""Join reviewed research batches. Preserve raw files and every uncertainty."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parents[1] / 'outputs/SaSa_Section_2_2/support'
OUT = BASE / 'consolidated_2026_10_20'

def read_json(path):
    return json.loads(path.read_text())

def read_lines(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s]

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def main():
    original = read_json(BASE/'analysis_data.json')
    rows, posts, sources = [], [], [BASE/'analysis_data.json']
    for p in original['posts']:
        posts.append(dict(post_id=p['post_id'],platform=p['platform'],url=p['url'],
            title=p['title'],post_date=p['post_date'],date_note=p.get('post_date_as_shown',''),
            method=p['collection_method'],hk_context=p['hk_relevance'],source=p['evidence_file']))
    pmap={p['post_id']:p for p in posts}
    for c in original['comments']:
        state = 'context_reply' if c['kind']!='top_level' else 'valid' if c['included'] is True else 'excluded' if c['included'] is False else 'unclear'
        rows.append(dict(comment_id=c['comment_id'],platform_comment_id='',post_id=c['post_id'],
            platform=pmap[c['post_id']]['platform'],anonymous_user=c['user_id'],
            original_text=c['original_text'],comment_date_original=c['comment_date'],
            exact_comment_datetime='',date_scope_original=c['date_scope'],
            level=c['kind'],status=state,themes=';'.join(c.get('themes',[])),
            evidence_excerpt=c.get('evidence_excerpt',''),source=c['evidence_file'],
            source_row=c['collection_rank'],review_notes=c.get('review_notes',''),
            method=pmap[c['post_id']]['method'],duplicate_sensitivity=False))
    cmap={c['comment_id']:c for c in rows}
    for file, key, date_key in [
        ('reconciliation.json','previous_comment_id','api_comment_date'),
        ('browser_reconciliation.json','prior_comment_id','rendered_datetime_attribute')]:
        src=ROOT/'data/instagram_pilot_review'/file;sources.append(src)
        for cross in read_json(src)['crosswalk']:
            row=cmap[cross[key]]
            row['platform_comment_id']=cross['platform_comment_id']
            row['exact_comment_datetime']=cross[date_key]
            row['review_notes']+=' | Date/ID crosswalk: '+str(src)
    pmap['IG_P01']['date_note']+=' | Prior date 2024-10-28 versus API 2024-10-29 unresolved; both October 2024.'
    src=ROOT/'data/xhs_research/posts.jsonl';sources.append(src)
    for p in read_lines(src):
        posts.append(dict(post_id=p['post_id'],platform='Xiaohongshu',url=p['url'],title=p['title'],
            post_date=p['post_date'],date_note='2026 accepted under revised scope',method=p['collection_method'],
            hk_context=p['hk_relevance'],source=str(src)))
    src=ROOT/'data/xhs_research_review/reviewed_comments.jsonl';sources.append(src)
    for c in read_lines(src):
        rows.append(dict(comment_id=c['comment_id'],platform_comment_id=c['comment_id'],post_id=c['post_id'],
            platform='Xiaohongshu',anonymous_user=c['anonymous_user'],original_text=c['text_original'],
            comment_date_original=c['comment_date'],exact_comment_datetime=c['comment_date'],
            date_scope_original=c['comment_window'],level=c['comment_level'],status=c['inclusion_status'],
            themes=';'.join(c['themes']),evidence_excerpt=c['evidence_excerpt'],source=c['source_jsonl'],
            source_row=c['source_line'],review_notes=c['review_notes'],method=c['collection_method'],
            duplicate_sensitivity=c['sensitivity_exclude_repeated_posting']))
    ext=ROOT/'data/instagram_browser_review/extension_review.csv';sources.append(ext)
    for c in read_csv(ext):
        state='valid' if c['final_denominator_eligible']=='True' else 'excluded' if c['content_review']=='excluded_brand_associated' else 'unclear' if c['content_review']=='unclear' else 'pending_evidence'
        rows.append(dict(comment_id=c['comment_id'],platform_comment_id=c['comment_id'],post_id=c['post_id'],
            platform='Instagram',anonymous_user=c['anonymous_user'],original_text=c['original_text'],
            comment_date_original=c['visible_date'],exact_comment_datetime=c['datetime_attribute'],
            date_scope_original=c['sample_window'],level=c['level_review'],status=state,
            themes=c['theme'],evidence_excerpt=c['evidence_fragment'],source=c['source'],
            source_row=c['capture_position'],review_notes=c['review_note'],method='Browser DOM; screenshot cross-check',
            duplicate_sensitivity=False))
    hist=ROOT/'data/instagram_historical_review/comments_audit.csv';sources.append(hist)
    for c in read_csv(hist):
        rows.append(dict(comment_id=c['comment_id'],platform_comment_id=c['comment_id'],post_id=c['post_id'],
            platform='Instagram',anonymous_user=c['anonymous_user'],original_text=c['original_text'],
            comment_date_original=c['comment_datetime_utc'],exact_comment_datetime=c['comment_datetime_utc'],
            date_scope_original=c['comment_window'],level='top_level' if c['primary_analysis_eligible']=='True' else 'unverified',
            status='valid' if c['primary_analysis_eligible']=='True' else 'pending_evidence',
            themes=c['themes'],evidence_excerpt=c['original_text'] if c['primary_analysis_eligible']=='True' else '',
            source=c['evidence'],source_row=c['position'],review_notes=c['review_note']+' '+c['alternative_products_note'],
            method='Browser DOM; signup overlay affected evidence',duplicate_sensitivity=False))
    for file in ['data/instagram_browser/DeppGlOxgA4_1792433992025104000.json',
                 'data/instagram_historical/DPRfaCiDD7n_1792434597094325000.json',
                 'data/instagram_historical/DA92M5qyQ9H_1792434603497584000.json']:
        src=ROOT/file;sources.append(src);p=read_json(src)
        dt=[t for t in p.get('page_time_elements_for_review',[]) if t['link'] and '/c/' not in t['link']]
        posts.append(dict(post_id=p['post_id'],platform='Instagram',url=p['post_url'],title=p['selection_reason'],
            post_date=dt[-1]['text'] if dt else 'unknown_exact_date',date_note='Original date separate from comment dates',
            method=p['collection_method'],hk_context=p.get('hk_relevance','unverified'),source=str(src)))
    for c in rows:
        exact=c['exact_comment_datetime']
        if exact:
            dt=datetime.fromisoformat(exact.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Hong_Kong'))
            c['comment_year']=str(dt.year)
            c['season_relation']='Sep_Oct' if dt.month in (9,10) else 'other_month'
            c['year_basis']='exact timestamp'
        elif c['date_scope_original']=='supplemental_2026_to_collection_date':
            c['comment_year']='2026';c['season_relation']='unknown_exact_date';c['year_basis']='prior relative-date review'
        else:
            c['comment_year']='unknown';c['season_relation']='unknown';c['year_basis']='unresolved; retain separately'
    assert len({c['comment_id'] for c in rows})==len(rows)
    ids=[c['platform_comment_id'] for c in rows if c['platform_comment_id']]
    assert len(ids)==len(set(ids))
    assert len({p['post_id'] for p in posts})==len(posts)
    for p in posts:
        subset=[c for c in rows if c['post_id']==p['post_id']]
        p['raw_comments']=len(subset);p['valid_comments']=sum(c['status']=='valid' for c in subset)
    summary=[]
    themes=[]
    for platform in ['Xiaohongshu','Instagram']:
        subset=[c for c in rows if c['platform']==platform]
        counts=Counter(c['status'] for c in subset)
        summary.append(dict(platform=platform,posts_attempted=sum(p['platform']==platform for p in posts),
            posts_with_comments=sum(p['platform']==platform and p['raw_comments']>0 for p in posts),
            raw_comments=len(subset),**{s:counts[s] for s in ['valid','excluded','unclear','pending_evidence','context_reply']}))
        for t in original['codebook']:
            selected=[c for c in subset if c['status']=='valid' and t['code'] in c['themes'].split(';')]
            themes.append(dict(platform=platform,theme=t['code'],label=t['theme'],comments=len(selected),
                posts=len({c['post_id'] for c in selected}),valid_denominator=counts['valid']))
    OUT.mkdir(exist_ok=True)
    for name,records in [('comments',rows),('posts',posts),('summary',summary),('themes',themes)]:
        with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    payload=dict(scope='Revised 2024–2026 relevant posts without geographic restriction; unknown dates retained separately; season is descriptive, not an exclusion filter.',
        posts=posts,comments=rows,summary=summary,themes=themes,
        duplicates_not_readded={'XHS technical pilot matching old P01':12,'IG API pilot':7,'IG repeat browser capture':15,'IG native partial overlapping new capture':6},
        limitations=['API returned order differs from browser order; methods are separately recorded.',
            'Valid means content and evidence accepted, not an independent consumer or verified purchase.',
            'Pending evidence is separate from unclear content and excluded comments.',
            'Unknown-date observations remain supplementary, not asserted to be 2024–2026.',
            'Existing outputs have not yet been replaced. This inventory is the merge staging dataset.'],
        sources_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (OUT/'inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(json.dumps({'summary':summary,'themes':themes,'output':str(OUT)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
