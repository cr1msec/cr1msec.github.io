#!/usr/bin/env python3
"""
register_report.py — takes an already-generated report HTML file
(e.g. one downloaded from writeup-converter.html) and wires it into
reports.html automatically: adds a new card, or updates the existing
one if you run this again after re-generating the same writeup.

USAGE:
    python3 register_report.py writeups/report-knife.html

Expects your folder layout to be:
    your-site/
    ├── index.html, reports.html, styles.css, etc.
    └── writeups/
        └── report-knife.html   <- the file you point this at

It reads the title/difficulty/tags straight out of the HTML file
itself (no need to re-type anything), so just make sure the file
was generated properly by writeup-converter.html or generate_report.py
first.
"""

import sys, re, html
from pathlib import Path
from datetime import datetime

ALLOWED_TAGS = {
    'web', 'sqli', 'ssti', 'ssrf', 'lfi', 'rfi', 'file upload',
    'command injection', 'rce', 'authentication', 'brute force',
    'linux privesc', 'windows privesc', 'sudo', 'suid', 'capabilities',
    'cron', 'kernel exploit', 'service exploit', 'credential abuse',
    'ftp', 'ssh', 'wordpress', 'active directory', 'smb', 'api',
    'enumeration', 'misconfiguration',
}


def extract_meta(report_html: str):
    title_m = re.search(r'<h1 class="page-title[^"]*">(.*?)</h1>', report_html, re.DOTALL)
    title = html.unescape(title_m.group(1).strip()) if title_m else None

    meta_block_m = re.search(r'<div class="writeup-meta">(.*?)</div>', report_html, re.DOTALL)
    tags = []
    difficulty = 'Medium'
    if meta_block_m:
        block = meta_block_m.group(1)
        diff_m = re.search(r'<span class="tag diff (\w+)">(.*?)</span>', block)
        if diff_m:
            difficulty = html.unescape(diff_m.group(2).strip())
        # every OTHER <span class="tag">...</span> that isn't the diff one and isn't "HTB"
        for m in re.finditer(r'<span class="tag">(.*?)</span>', block):
            t = html.unescape(m.group(1).strip())
            if t.lower() != 'htb':
                tags.append(t)

    date_m = re.search(r'class="writeup-date">Solved:\s*(.*?)</(?:div|span)>', report_html, re.DOTALL)
    date = html.unescape(date_m.group(1).strip()) if date_m else 'date not set'

    return title, difficulty, tags, date


def parse_report_date(date_str: str):
    try:
        return datetime.strptime(date_str.strip(), '%B %d, %Y')
    except ValueError:
        return datetime.min  # unparseable/missing dates sort to the bottom


def find_matching_close_div(text: str, open_tag_pos: int, open_tag_len: int) -> int:
    """Given the position right after an opening <div ...> tag, walk forward counting
    nested <div>/</div> tags to find the index right after the matching closing </div>."""
    pos = open_tag_pos + open_tag_len
    depth = 1
    while depth > 0:
        next_open = text.find('<div', pos)
        next_close = text.find('</div>', pos)
        if next_close == -1:
            raise ValueError('unbalanced HTML: no matching </div> found')
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            pos = next_close + len('</div>')
    return pos


def resort_card_grid(reports_html: str) -> str:
    """Re-sort every <a class="report-card"> inside <div class="card-grid"> by its
    report-date, newest first, using a depth-aware match so nested divs inside each
    card never confuse the boundary detection."""
    marker = '<div class="card-grid">'
    start = reports_html.find(marker)
    if start == -1:
        return reports_html
    inner_start = start + len(marker)
    end = find_matching_close_div(reports_html, start, len(marker))
    inner_end = end - len('</div>')
    inner = reports_html[inner_start:inner_end]

    cards = re.findall(r'<a href="[^"]*"[^>]*class="report-card"[^>]*>.*?</a>', inner, re.DOTALL)
    if not cards:
        return reports_html

    def card_date(card):
        m = re.search(r'<div class="report-date">(.*?)</div>', card)
        return parse_report_date(html.unescape(m.group(1))) if m else datetime.min

    cards_sorted = sorted(cards, key=card_date, reverse=True)
    new_inner = '\n\n' + '\n\n'.join('      ' + c for c in cards_sorted) + '\n\n    '
    return reports_html[:inner_start] + new_inner + reports_html[inner_end:]


def update_reports_page(reports_path: Path, href: str, slug: str, difficulty: str, title: str, tags: list, date: str):
    if not reports_path.exists():
        return None

    diff_class = difficulty.lower() if difficulty.lower() in ('easy', 'medium', 'hard', 'insane') else ''
    text = reports_path.read_text(encoding='utf-8-sig')

    tags_attr = ','.join(t.lower() for t in tags)
    card_html = (
        f'      <a href="{href}" class="report-card" data-difficulty="{diff_class}" data-tags="{html.escape(tags_attr)}">\n'
        f'        <div class="report-top">\n'
        f'          <div class="report-tags"><span class="tag">HTB</span><span class="tag diff {diff_class}">{html.escape(difficulty)}</span></div>\n'
        f'          <div class="report-title">{html.escape(title)}</div>\n'
        f'          <div class="report-date">{html.escape(date)}</div>\n'
        f'        </div>\n'
        f'        <div class="report-code">\u250c\u2500\u2500(crimson\u327fkali)-[~/htb/{html.escape(difficulty)}]<br><span class="p1">\u2514\u2500$</span> your-command-here</div>\n'
        f'        <div class="report-foot"><span>{" \u00b7 ".join(tags[:2]) if tags else "summary here"}</span><span class="foot-right"><span class="root-status">ROOT</span><span class="open">open \u2192</span></span></div>\n'
        f'      </a>'
    )

    # match a card with this slug regardless of what path prefix it currently has
    existing_pattern = re.compile(
        rf'<a href="[^"]*report-{re.escape(slug)}\.html"[^>]*class="report-card"[^>]*>.*?</a>',
        re.DOTALL
    )

    if existing_pattern.search(text):
        text = existing_pattern.sub(card_html, text, count=1)
        action = 'updated'
    else:
        marker = '<div class="card-grid">'
        idx = text.find(marker)
        if idx == -1:
            return None
        insert_at = idx + len(marker)
        text = text[:insert_at] + '\n\n' + card_html + text[insert_at:]
        action = 'added'

    text = resort_card_grid(text)
    reports_path.write_text(text, encoding='utf-8')
    return action


def update_homepage(index_path: Path, reports_path: Path):
    """Keep the homepage stats/activity panels in sync with reports.html — called after every register."""
    if not index_path.exists() or not reports_path.exists():
        return False

    reports_html = reports_path.read_text(encoding='utf-8-sig')

    # pull every report card's title + its short descriptor (first span in report-foot), in DOM order (newest first)
    cards = re.findall(
        r'<div class="report-title">(.*?)</div>.*?<div class="report-foot"><span>(.*?)</span>',
        reports_html, re.DOTALL
    )
    if not cards:
        return False

    titles = [html.unescape(t.strip()) for t, _ in cards]
    count = len(titles)

    index_html = index_path.read_text(encoding='utf-8-sig')

    # 1. LAB_REPORTS stat number
    index_html = re.sub(
        r'(<span class="stat-glow">)\d+(</span></div><div class="label">LAB_REPORTS</div>)',
        rf'\g<1>{count}\g<2>', index_html
    )

    # 2. latest_content.log — "ls reports/" listing
    reports_line = '&nbsp;&nbsp;'.join(titles)
    index_html = re.sub(
        r'(<span class="prompt">\$</span> ls reports/</div>\s*<div>)(.*?)(</div>)',
        lambda m: m.group(1) + reports_line + m.group(3),
        index_html, count=1, flags=re.DOTALL
    )

    # 3. activity/"git log" panel — regenerate report lines, but preserve any "* post: ..." blog entries already there
    existing_activity_match = re.search(
        r'<div class="comment">// Recent activity</div>\s*<div>&nbsp;</div>\s*(.*?)\s*</div>\s*</div>\s*</section>',
        index_html, re.DOTALL
    )
    preserved_posts = []
    if existing_activity_match:
        preserved_posts = re.findall(r'<div>\* post:.*?</div>', existing_activity_match.group(1))

    activity_lines = '\n'.join(f'        {line}' for line in preserved_posts)
    if preserved_posts:
        activity_lines += '\n'
    activity_lines += '\n'.join(
        f'        <div>* docs: add writeup \u2014 {t} <span style="color:var(--text-faint)">({d})</span></div>'
        for t, d in zip(titles, [html.unescape(d.strip()) for _, d in cards])
    )
    activity_lines += '\n        <div>* project: ship Gandalf.exe</div>\n        <div>* init: portfolio scaffold live</div>'

    index_html = re.sub(
        r'(<div class="comment">// Recent activity</div>\s*<div>&nbsp;</div>\s*)(.*?)(\s*</div>\s*</div>\s*</section>)',
        lambda m: m.group(1).rstrip() + '\n' + activity_lines + m.group(3),
        index_html, count=1, flags=re.DOTALL
    )

    index_path.write_text(index_html, encoding='utf-8')
    return True


def sync_only(reports_path: Path):
    """Re-sort reports.html by date and re-sync the homepage, without registering
    a new writeup. Use this after any manual edit to reports.html."""
    if not reports_path.exists():
        print(f"File not found: {reports_path}")
        sys.exit(1)
    text = reports_path.read_text(encoding='utf-8-sig')
    text = resort_card_grid(text)
    reports_path.write_text(text, encoding='utf-8')
    print("\u2714 re-sorted reports.html by date")

    index_path = reports_path.parent / 'index.html'
    if update_homepage(index_path, reports_path):
        print("\u2714 synced homepage stats + activity panel")
    else:
        print("\u26a0  couldn't find index.html next to reports.html")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 register_report.py <path-to-report.html>")
        print("       python3 register_report.py --sync   (re-sort + re-sync without a new writeup)")
        print("e.g.:  python3 register_report.py writeups/report-knife.html")
        sys.exit(1)

    if sys.argv[1] == '--sync':
        sync_only(Path('reports.html'))
        return

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"File not found: {report_path}")
        sys.exit(1)

    report_html = report_path.read_text(encoding='utf-8-sig')
    title, difficulty, tags, date = extract_meta(report_html)

    if not title:
        print("\u26a0  Couldn't find a page title in that file \u2014 is this a report page")
        print("   generated by writeup-converter.html or generate_report.py?")
        sys.exit(1)

    bad_tags = [t for t in tags if t.lower() not in ALLOWED_TAGS]
    if bad_tags:
        print(f"\u26a0  tag(s) not in your approved list, double-check these: {', '.join(bad_tags)}")

    slug = report_path.stem.replace('report-', '', 1)

    # figure out where reports.html lives, and what href to use, based on folder layout
    if report_path.parent.name == 'writeups':
        reports_path = report_path.parent.parent / 'reports.html'
        href = f'writeups/{report_path.name}'
    else:
        reports_path = report_path.parent / 'reports.html'
        href = report_path.name

    action = update_reports_page(reports_path, href, slug, difficulty, title, tags, date)

    if action:
        print(f"\u2714 {action} the '{title}' card on {reports_path.name} \u2014 just refresh your browser")
    else:
        print(f"\u26a0  couldn't find {reports_path} (or no <div class=\"card-grid\"> in it)")
        print(f"   paste this in manually:\n")
        diff_class = difficulty.lower() if difficulty.lower() in ('easy','medium','hard','insane') else ''
        tagline = ' \u00b7 '.join(tags[:2]) if tags else 'summary here'
        print(f'''      <a href="{href}" class="report-card">
        <div class="report-top">
          <div class="report-tags"><span class="tag">HTB</span><span class="tag diff {diff_class}">{difficulty}</span></div>
          <div class="report-title">{title}</div>
          <div class="report-date">{date}</div>
        </div>
        <div class="report-code">\u250c\u2500\u2500(crimson\u327fkali)-[~/htb/{difficulty}]<br><span class="p1">\u2514\u2500$</span> your-command-here</div>
        <div class="report-foot"><span>{tagline}</span><span class="foot-right"><span class="root-status">ROOT</span><span class="open">open \u2192</span></span></div>
      </a>''')
        return

    index_path = reports_path.parent / 'index.html'
    if update_homepage(index_path, reports_path):
        print("\u2714 synced homepage stats + activity panel with your current reports")
    else:
        print("\u26a0  couldn't find index.html next to reports.html \u2014 homepage not updated")


if __name__ == '__main__':
    main()
