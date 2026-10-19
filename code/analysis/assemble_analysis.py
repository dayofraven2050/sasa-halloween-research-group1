"""Assemble reviewed browser transcriptions; no network calls or inferred comments."""
from pathlib import Path
import csv, json, hashlib, collections, re

HERE = Path(__file__).resolve().parent
OUT = HERE.parent

def main():
    names = ['coding_batch01.json','coding_batch02.json','coding_ig01.json','coding_ig02.json','coding_batch03.json']
    if (HERE/'coding_batch04.json').exists(): names.append('coding_batch04.json')
    posts, comments = {}, {}
    for name in names:
        batch=json.loads((HERE/name).read_text())
        for p in batch['posts']: posts[p['post_id']]=p
        for c in batch['comments']:
            assert c['comment_id'] not in comments, c['comment_id']
            comments[c['comment_id']]=c
    posts=sorted(posts.values(),key=lambda p:(p['platform']!='Xiaohongshu',p['post_id']))
    comments=sorted(comments.values(),key=lambda c:(c['post_id'].startswith('IG'),c['post_id'],float(c['collection_rank'])))
    pmap={p['post_id']:p for p in posts}
    # Weeks shown on IG_P02 (9–38w before 19 October 2026) are all outside
    # Sep–Oct 2024/2025 and Sep–Oct 2026, even allowing week rounding.
    # We retain the displayed age; no exact calendar date is invented.
    for c in comments:
        if c['post_id']=='IG_P02':
            c['date_scope_original']=c['date_scope']
            c['date_scope']='outside_selected_window_relative_weeks'
            c['review_notes'] += ' Displayed 9–38w at collection falls outside the selected seasonal windows; exact date remains unknown.'
        if c['comment_id']=='XHS_P06_C02':
            c['themes']=['T7','T8']
            c['review_notes'] += ' Final rule review: explicit request for a link is also T7 sourcing, consistent with general-material sourcing on IG_P03. The object is a veil, not cosmetics.'
        assert c['post_id'] in pmap
        assert not c['included'] or c['kind']=='top_level'
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', c.get('comment_date','')):
            c['comment_date_iso']=c['comment_date']
        c.setdefault('review_status','Individually read against browser evidence')
    reviewed_excerpts={
        'XHS_P05_C07':'问问口红',
        'XHS_P06_C09':'老师别删\n我存了万圣节化',
        'XHS_P02_C01':'放大看能看到有一条白色颜料流下来 但是出汗不多的话其实还好',
        'XHS_P06_C12':'老师的讲解不造为啥让我看的很欢乐～种草了染眉膏。想问这款美瞳轻微遮瞳会影响看东西吗？本人之前种草了它很久没买'
    }
    for c in comments:
        if c['comment_id'] in reviewed_excerpts:
            c['evidence_excerpt']=reviewed_excerpts[c['comment_id']]
            assert c['evidence_excerpt'] in c['original_text']
    for p in posts:
        cc=[c for c in comments if c['post_id']==p['post_id']]
        top=[c for c in cc if c['kind']=='top_level']
        assert len(top)<=15, p['post_id']
        p['captured_top_level_count']=len(top)
        p['captured_reply_count']=len(cc)-len(top)

    codebook=[
      dict(code='T1',theme='Character and visual effect',definition='Character resemblance, festive atmosphere, photographic result, or makeup-effect praise.',include_rule='Explicit character/effect statements; interpretable aesthetic praise on a makeup demonstration.',exclude_rule='Do not infer buying from praise. Ambiguous celebrity compliments or bare exclamations remain unclassified.'),
      dict(code='T2',theme='Tutorial use, feedback and difficulty',definition='Seeking, using or evaluating guidance, learning to recreate a look, effort, difficulty or preparation time.',include_rule='How-to requests; stated learning or saving a tutorial for Halloween; explicit feedback on an explanation; skill/time concerns.',exclude_rule='Product-name questions alone do not establish tutorial need. Enjoying an explanation does not prove learning effectiveness. Recreating a look is not buying a product.'),
      dict(code='T3',theme='Makeup items and shades',definition='Specific cosmetics or false lashes used in the look; product or shade information and expressed product interest.',include_rule='Lipstick, eyeliner, brow mascara and false-lash questions/interest.',exclude_rule='Hair, wigs, decorative contact lenses, clothing and tools are T8, with a named subtype. Questions and interest do not establish a purchase.'),
      dict(code='T4',theme='Price information and budget',definition='Explicit price, budget, cost comparisons or affordability.',include_rule='Neutral price enquiries and explicit price objections; distinguish makeup-service context from retail cosmetics.',exclude_rule='Asking the price alone is not a price barrier. No affordability level inferred without an explicit statement.'),
      dict(code='T5',theme='Single use, waste and reuse',definition='Frequency of use, one-off use acceptance or objection, waste and everyday versatility.',include_rule='Explicit use-frequency, waste or reuse statement.',exclude_rule='No inference from wanting a product; absence of coded comments is not evidence that concerns do not exist.'),
      dict(code='T6',theme='Using products already owned',definition='Owned cosmetics substituted for buying new products.',include_rule='Explicit existing ownership, repurposing owned makeup, or avoiding an additional purchase.',exclude_rule='Unspecified cheaper alternatives are not evidence of existing ownership.'),
      dict(code='T7',theme='Product/material sourcing',definition='Where or how to obtain products/materials, retail availability, stock or delivery.',include_rule='Explicit buying-source/link questions; retain object subtype when it is a non-cosmetic item.',exclude_rule='Product-name questions alone are T3; booking a makeup service is T8 service_access.'),
      dict(code='T8',theme='Other observed needs and concerns',definition='Named emergent themes: service access, durability, hair/accessories, tools, or contact-lens practical concerns.',include_rule='Preserve the exact subtype and supporting text; use subtypes rather than treating all T8 comments as one need.',exclude_rule='Unrelated advertising is excluded. Medical/performance claims in comments are unverified reports, not validated product facts.')
    ]
    interview_source=json.loads((HERE/'protocol/interview.json').read_text())
    interview=[]
    for x in interview_source['claims']:
        quoted=x['record_type']=='direct_quote_supplied_by_user'
        interview.append(dict(id=x['evidence_id'],summary=x['text_en'],verbatim_quote=x['text_zh'] if quoted else '',interpretation=x['interpretation'],boundary=x['limit']+' User-supplied summary, n=1; interview date, age and residence unknown.'))
    metrics={}
    for platform in ['Xiaohongshu','Instagram']:
        pp=[p for p in posts if p['platform']==platform]
        cc=[c for c in comments if pmap[c['post_id']]['platform']==platform]
        tt=[c for c in cc if c['kind']=='top_level']
        vv=[c for c in tt if c['included'] is True]
        metrics[platform]=dict(posts=len(pp),sampled_posts=sum(p['included'] is True for p in pp),posts_with_comments=len({c['post_id'] for c in tt}),posts_with_valid_comments=len({c['post_id'] for c in vv}),raw=len(cc),top_level=len(tt),context=len(cc)-len(tt),valid=len(vv),excluded=sum(c['included'] is False for c in tt),unknown=sum(c['included'] is None for c in tt),themes={t['code']:{'comments':sum(t['code'] in c['themes'] for c in vv),'posts':len({c['post_id'] for c in vv if t['code'] in c['themes']})} for t in codebook})
    scopes=sorted({c['date_scope'] for c in comments})
    mapping={s:('supplemental_2026' if s.startswith('supplemental_2026') else 'verified_2024_2025_season' if s in ['within_2024_sep_oct','within_2025_sep_oct'] else 'outside_window' if s.startswith('outside') else 'unknown') for s in scopes}
    meta=dict(collected_at='2026-10-19 (Asia/Shanghai)',study_window='Preferred: 1 September–31 October 2024 and 2025; verified 2026 observations and unresolved dates retained as separate exploratory extensions.',
      scope_notes='Purposive convenience sample, below the 24-post target. Historical coverage was limited by loading failures, inaccessible public-page comments, and missing date precision. No population inference. Hong Kong relevance means observed post context/publisher, never commenter residence. A verified zero-comment tutorial remains in the post register.',
      method_notes='Public unauthenticated retrieval was tested on both platforms and yielded no usable comments. After user login, actual rendered comments were read with browser accessibility/DOM tools and manually structured, preserving default displayed order and capping each post at 15 unique top-level comments. Replies were contextual only. Repeated loaded entries were deduplicated; repeated short text from different authors was retained. No search snippet, caption or AI search answer was coded as a comment. Comments were pilot-coded, the codebook refined, and all retained comments reviewed in context.',
      limitations='Small non-probability sample with platform ranking, author/content, access and language biases. Several captures are partial. Exact comment dates are often unavailable, so most observations cannot establish pre-Halloween demand in 2024/2025. Services, costumes and accessories are not cosmetics purchases. Posts cluster comments; anonymous IDs are scoped to each post and do not represent independently sampled consumers. One interview (n=1) is exploratory. No verified transactions, causal effects or conversion lift were measured.',
      date_scope_mapping=mapping,
      t8_subtypes=['service_access','general_service_enquiry','durability','accessory_wig','accessory_contact_lenses','accessory_headpiece_clothing','accessory_contact_lenses_visual','accessory_veil','makeup_tools_brush','contact_lens_practical_barrier','accessory_contact_lenses_appearance','general_look_materials_sourcing','hair_colour_material','hair_wig_question'])
    campaign=[
      dict(finding='Questions identify makeup information gaps, without establishing incremental purchase.',evidence_ids=['XHS_P05_C01','XHS_P05_C05','XHS_P05_C07','INT01-S4'],counterevidence='False lashes, accessories and tools are distinct. Product enquiries do not prove intent or sale; no evidence establishes that exactly one product is optimal.',implication='Retain a clearly identified Hero Product with shade, role in the look and purchase information; show what can already be owned. Test additional-purchase conversion.',uncertainty='Directional evidence from a small number of general-reference tutorials; not Hong Kong consumer prevalence.'),
      dict(finding='Tutorial use and appearance goals are plausible motivations.',evidence_ids=['XHS_P06_C08','XHS_P06_C09','IG_P03_C03','INT01-S2','INT01-Q1'],counterevidence='Look-saving and praise are not purchase commitments. Some Instagram reactions are celebrity affection or ambiguous, and were not counted as demand.',implication='Retain KOL demonstrations of real makeup results and actionable steps. Treat role cards and quiz-led discovery as design hypotheses.',uncertainty='No evidence validates 20 roles, a particular KOL allocation, or an AR conversion advantage.'),
      dict(finding='Practical performance can matter alongside the appearance goal.',evidence_ids=['XHS_P02_C01'],counterevidence='One unverified face-painting experience reports paint running with sweat; this is a service-use account, not a comparative retail-product test.',implication='Add realistic application and wear demonstrations to tutorials; explain relevant product limitations. An AR image alone cannot establish actual wear performance.',uncertainty='No prevalence or comparative product efficacy estimate.'),
      dict(finding='Hong Kong service enquiries concern price and booking access.',evidence_ids=['XHS_P01_C01','XHS_P01_C02','XHS_P01_C08','INT01-S5'],counterevidence='Service enquiries do not validate cosmetics price sensitivity, Sa Sa service demand, or a profitable in-store service model.',implication='Consider a separate service feasibility test; keep retail-product and service responses separate in campaign evaluation.',uncertainty='Commercial service post, AI-labelled creative, unknown post year; no observed booking or purchase.'),
      dict(finding='The interview challenges a universal single-use objection.',evidence_ids=['INT01-S3','INT01-S4','INT01-Q1'],counterevidence='One coser accepts a possible one-off purchase; the captured comments do not establish the prevalence of waste/reuse objections or use of owned substitutes.',implication='Lead with a credible occasion result and limited additional-item need. Offer everyday reuse as optional value; do not claim it is every consumer’s principal barrier.',uncertainty='Stated intention from n=1; no transaction verified. Comments neither confirm nor refute a broad reuse barrier.'),
      dict(finding='AR, sharing rewards and photobooth conversion remain untested.',evidence_ids=['INT01-Q1'],counterevidence='Neither the interview nor captured comments directly evaluates the proposed AR, role card, coupon redemption or photobooth mechanics.',implication='Retain these as testable campaign hypotheses, measuring product-page visits, add-to-cart, orders and incremental sales separately from shares/AR use.',uncertainty='No causal or conversion evidence; no inference about ideal geofence, reward amount or geographic coverage.')
    ]
    data=dict(meta=meta,platforms=[dict(platform=p,status='partial',notes='Public-page code did not expose comments; browser-visible sample collected. Partial coverage and dates documented per post.') for p in ['Xiaohongshu','Instagram']],posts=posts,comments=comments,codebook=codebook,interview=interview,campaign=campaign,metrics=metrics)
    # Reviewed report prose is managed separately so updating data cannot silently invent claims.
    cfg=HERE/'report_text.json'
    if cfg.exists(): data['docx']=json.loads(cfg.read_text())
    (HERE/'analysis_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
    for name,rows in [('posts',posts),('raw_comments',comments),('coded_comments',comments)]:
        keys=list(dict.fromkeys(k for row in rows for k in row))
        if name=='raw_comments': keys=[k for k in keys if k not in ['clean_text','english_translation','themes','theme_subtypes','included','exclusion_reason','evidence_excerpt','engagement_type','review_notes','review_status','purchase_evidence']]
        with (HERE/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader()
            for row in rows: w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
    (HERE/'independent_counts.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
    manifest={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE/'browser_evidence').glob('*.txt'))}
    (HERE/'evidence_sha256.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'metrics':metrics,'date_scope_mapping':mapping},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
