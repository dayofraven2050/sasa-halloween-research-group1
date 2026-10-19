"""Audit saved evidence without changing raw captures or the final workbook."""
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/instagram_historical_review'
FILES = ['DPRfaCiDD7n_1792434597094325000.json', 'DA92M5qyQ9H_1792434603497584000.json']


def main():
    rows, posts = [], []
    for name in FILES:
        path = ROOT / 'data/instagram_historical' / name
        data = json.loads(path.read_text())
        dates = [t for t in data['page_time_elements_for_review'] if t['link'] and '/c/' not in t['link']]
        assert len(dates) == 1
        post_date = dates[0]['text']
        posts.append(dict(post_id=data['post_id'], post_date_displayed=post_date,
                          post_datetime_attribute=dates[0]['datetime'], raw_blocks=len(data['blocks']),
                          hk_relevance=data['hk_relevance'], evidence=str(path)))
        author_map = {}
        for block in data['blocks']:
            lines = block['visible_block_text'].splitlines()
            author_map.setdefault(lines[0], f'{data["post_id"]}_U{len(author_map)+1:02d}')
            start, end = lines.index(block['visible_date_text'])+1, lines.index('Reply')
            if re.fullmatch(r'(Like|\d+ likes?)', lines[end-1]):
                end -= 1
            raw = '\n'.join(lines[start:end])
            date = datetime.fromisoformat(block['datetime_attribute'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Hong_Kong'))
            historical = date.year in (2024,2025) and date.month in (9,10)
            key = block['comment_id'] == 'instagram_18360857530083720'
            pos = block['capture_position']
            ghost = 'DPRfa' in data['post_id']
            # Content labels are separate from eligibility; obscured evidence is held.
            content = ('help_request' if key else 'emoji_or_tag_only' if (ghost and pos in (3,6,9,10,11,13)) or (not ghost and pos in (1,6,10,13,14)) else 'other_or_praise_pending_eligibility')
            rows.append(dict(post_id=data['post_id'], comment_id=block['comment_id'],
                anonymous_user=author_map[lines[0]], position=pos,
                original_text=raw, display_text=re.sub(r'@[\w.]+','@[anonymised]',raw),
                comment_datetime_utc=block['datetime_attribute'], comment_datetime_hk=date.isoformat(),
                comment_window='historical_Sep_Oct' if historical else '2026_extension' if date.year==2026 and date.month in (9,10) else 'outside_selected_season',
                content_review=content, themes='T1;T2' if key else '',
                alternative_products_note='Limited owned makeup inventory; asks for tips. T6 substitution is plausible but not explicitly stated.' if key else '',
                purchase_intent='not_expressed',
                evidence_status='full_text_and_top_level_visually_confirmed' if key else 'hold_visual_review_or_obscured',
                primary_analysis_eligible=key and historical,
                evidence=str(path), permalink=block['comment_permalink'],
                review_screenshot=str(path.parent / ('DPRfaCiDD7n_1792434597094325000_position_13.png' if key else block['review_screenshot'])),
                review_note='Default displayed order; comments trend newest-first in this capture, not a verified sort setting. Several screenshots show signup overlay. Preserve raw, do not treat as complete verified sample.'))
    assert len(rows)==28 and len({r['comment_id'] for r in rows})==28
    OUT.mkdir(exist_ok=True)
    for filename, records in [('comments_audit.csv',rows),('posts_audit.csv',posts)]:
        with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    summary=dict(raw_posts=2,raw_comments=28,
        comment_historical_window=sum(r['comment_window']=='historical_Sep_Oct' for r in rows),
        verified_relevant_historical_comments=sum(r['primary_analysis_eligible'] for r in rows),
        historical_window_note='Two comments are within Sep–Oct 2025 in Hong Kong time: one relevant question and one tag-only comment. All 15 black-lipstick-post comments are from 2026.',
        historical_post_dates={p['post_id']:p['post_date_displayed'] for p in posts},
        limitation='Both pages displayed logged-out UI. Several screenshots are obstructed by a signup prompt; rows on hold are not counted as verified valid comments. No inference about HK commenter residence.',
        campaign_implication='Offer an owned-product checklist and optional clearly justified Hero Product. A request for tips is not willingness to buy.',
        final_workbook_updated=False)
    (OUT/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
