# Sa Sa Halloween Research — Group 1

## Appendix E — Collection code and data attachments

Supporting materials for Section 2.2 of the Sa Sa Halloween marketing report.

**[Download the Excel analysis workbook](SaSa_Social_Listening_Analysis.xlsx)** (open the file and choose **Download raw file** on GitHub).

## Files

- **SaSa_Social_Listening_Analysis.xlsx**: raw records, coding decisions, theme definitions, descriptive summaries, interview summary and campaign implications.
- **raw_comments.csv** and **posts.csv**: auditable record-level exports and post inventory.
- **summary.csv** and **themes.csv**: platform and theme summaries.
- **code/research/collect.py**: code-based collection.
- **code/research/browser_capture.py**: capture of visible Instagram comment blocks.
- **code/research/**: screening, review, reconciliation and final coding scripts used in the project.
- **code/analysis/**: original analysis assembly, Excel generation and source-link packaging scripts.
- **code/project_sources.json**: upstream projects and pinned versions; its execution status describes an earlier pilot, not the final totals.
- **METHOD_README.txt**: method notes.

## Sample and interpretation

Collection took place on 19–20 October 2026, targeting relevant 2024–2026 posts without geographic restrictions. Of 24 attempted posts, 21 yielded 264 comment or reply records. Thematic analysis retained 128 substantive top-level comments: 69 from Xiaohongshu and 59 from Instagram. The 264 records also include 47 excluded records, 23 unclear records, 36 pending records and 30 contextual replies. These categories must not be counted as additional valid thematic comments.

The interview is a researcher-supplied summary from one cosplayer (n=1), not a verbatim transcript. The researcher subsequently identified her as a local Hong Kong cosplayer. This clarification does not alter the comment dataset.

Code-based collection was supplemented with browser-visible capture and individual review. Browser UI blocks are not API exports or automatically validated comments. Multiple themes can apply to one comment. Product enquiries and praise do not establish purchases. The sample is exploratory and not representative of Hong Kong consumers.

## Reuse and reproducibility

The collection and historical assembly scripts are provided as an audit trail. They are not a standalone one-command reproduction package: historical evidence, workspace inputs, upstream dependencies and manual platform login may be required. The workbook-generation script uses the original Artifact Tool runtime. No platform access restrictions are bypassed by this repository.

Only project scripts are included; upstream MediaCrawler and Instaloader code is not redistributed. Consult the source manifest for their versions and licences. No blanket licence is granted over third-party comment text.

Account sessions, passwords, browser profiles and anonymisation keys are excluded. Local home-directory paths are replaced with portable placeholders in this publication copy; original evidence files remain in the research workspace. Screenshots are not included. Public post links and anonymous record IDs are retained for traceability. Counts, coding decisions and comment text are unchanged by path sanitisation.
