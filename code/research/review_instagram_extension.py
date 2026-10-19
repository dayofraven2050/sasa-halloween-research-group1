"""Reproduce an individually read, provisional review; never modifies evidence."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/instagram_browser/DeppGlOxgA4_1792433992025104000.json'
OUT = ROOT / 'data/instagram_browser_review'
TRANSLATIONS = [
    'Wow! Wonderful! We love seeing our BT VELVET in action in this work of art, Ana. You delivered! Congratulations!',
    'Congratulations! Incredible!', 'So talented!', 'It turned out incredible',
    'Artist', 'Wow, you are a master! Bravo', 'Thank you for sharing, diva!',
    'It turned out incredible. Congratulations!', 'You really nail it', 'Perfect',
    'Incredible, very talented!', 'Your work is horrifying; congratulations',
    'Wow', 'Wow, I loved it so much. You really nail it.',
    'Girl, you nailed it! How horrifying this makeup is!',
]
OVERLAP = {'18118727269992361', '18118359988952939', '18133940590673023',
           '18111239435333172', '18115544456041797', '17990768286107960'}


def main():
    source_bytes = SOURCE.read_bytes()
    data = json.loads(source_bytes)
    authors, rows = {}, []
    assert len(data['blocks']) == 15
    for block, translation in zip(data['blocks'], TRANSLATIONS):
        lines = block['visible_block_text'].splitlines()
        author = lines[0]
        authors.setdefault(author, f'IG_EXT_U{len(authors)+1:02d}')
        start = lines.index(block['visible_date_text']) + 1
        end = lines.index('Reply')
        if re.fullmatch(r'\d+ likes?', lines[end-1]):
            end -= 1
        original = '\n'.join(lines[start:end])
        pos = block['capture_position']
        status = 'excluded_brand_associated' if pos == 1 else 'unclear' if pos == 13 else 'valid_content_provisional'
        theme = 'T1' if pos not in (1, 7, 13) else ''
        rows.append(dict(
            post_id=data['post_id'], comment_id=block['comment_id'],
            anonymous_user=authors[author], capture_position=pos,
            original_text=original, english_gloss=translation,
            translation_note='Analyst gloss, not original text; emoji retained only in original',
            visible_date=block['visible_date_text'], datetime_attribute=block['datetime_attribute'],
            collection_date=data['collection_date'], sample_window='2026_extension',
            hk_relevance='unverified', post_date='unknown_exact_date',
            content_review=status, theme=theme,
            evidence_fragment=original if theme else '',
            interaction_type='brand_response' if pos == 1 else 'gratitude' if pos == 7 else 'ambiguous_exclamation' if pos == 13 else 'praise',
            purchase_intent='not_expressed', purchase_report='not_expressed',
            level_review='top_level_visible_in_screenshot' if pos <= 5 else 'unverified_offscreen_DOM',
            final_denominator_eligible=pos <= 5 and status == 'valid_content_provisional',
            prior_partial_overlap=block['comment_id'].removeprefix('instagram_') in OVERLAP,
            permalink=block['comment_permalink'], source=str(SOURCE),
            screenshot=str(SOURCE.parent / block['screenshot']),
            review_note='Horrifying is praise in context of congratulations/clapping' if pos in (12,15) else 'Brand affiliation indicated by own-product wording and displayed account' if pos == 1 else '',
        ))
    assert len({r['comment_id'] for r in rows}) == 15
    assert sum(r['prior_partial_overlap'] for r in rows) == 6
    OUT.mkdir(exist_ok=True)
    with (OUT / 'extension_review.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(
        source_sha256=hashlib.sha256(source_bytes).hexdigest(), raw_unique_comments=15,
        content_valid_provisional=13, excluded_brand_associated=1, unclear_content=1,
        valid_with_top_level_screenshot_confirmation=4,
        remaining_level_review_required=10,
        distinct_accounts_within_capture=14,
        prior_partial_overlap=6, incremental_over_partial=9,
        provisional_T1_comments=12, explicit_purchase_intent=0, self_reported_purchase=0,
        final_workbook_updated=False,
        limitations=[
            'All comment timestamps are October 2026; no verified Hong Kong connection.',
            'Only positions 1–5 fully visible in saved screenshot. Other rendered DOM blocks retain unverified hierarchy; do not merge into final top-level denominator yet.',
            'Earlier six native observations overlap this sample; order differs across captures. Freeze latest 15-position capture, do not add earlier six.',
            'Single promotional tutorial, default displayed order; no population inference.',
            'Individual text review by Codex, not independent human intercoder validation.',
        ],
    )
    (OUT / 'extension_review_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
