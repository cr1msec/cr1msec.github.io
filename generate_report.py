#!/usr/bin/env python3
"""
generate_report.py — converts a markdown lab-report writeup into a
styled HTML page matching the crimson portfolio theme.

USAGE:
    python3 generate_report.py mywriteup.md

Your markdown file must start with a frontmatter block like this:

---
title: Cap
difficulty: Easy
tags: HTB, Linux, Capabilities
summary: One or two sentence summary shown at the top of the page.
---

Then write your report normally using:
  ## Section Heading
  ### Sub heading

  ```bash
  command here
  ```

  ```text
  raw output / creds / whoami output
  ```

  | Table | Headers |
  |---|---|
  | row | data |

  - bullet
  - point
  list (renders as an arrow-style list, like "Key Takeaways")

  `inline code`
  **highlighted text**   (renders in glowing crimson — use for creds, key findings)

Output: writes report-<slug>.html in the SAME folder as this script
(next to styles.css, index.html, etc — keep it all together, no subfolders).

It also prints the HTML snippet for the report card on reports.html —
paste that into the <div class="card-grid"> block to link the new
writeup in.
"""

import sys, re, html
from pathlib import Path


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def inline_format(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<span class="hl">\1</span>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def parse_frontmatter(lines):
    meta = {}
    if lines and lines[0].strip() == '---':
        i = 1
        while i < len(lines) and lines[i].strip() != '---':
            line = lines[i]
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip().lower()] = v.strip()
            i += 1
        return meta, lines[i + 1:]
    return meta, lines


def parse_body(lines):
    parts = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].rstrip('\n')
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        m = re.match(r'^(#{2,3})\s+(.*)', stripped)
        if m:
            tag = 'h2' if len(m.group(1)) == 2 else 'h3'
            parts.append(f'<{tag}>{inline_format(m.group(2))}</{tag}>')
            i += 1
            continue

        m = re.match(r'^```(\w*)', stripped)
        if m:
            lang = m.group(1).lower()
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i].rstrip('\n'))
                i += 1
            i += 1
            if lang in ('bash', 'sh', 'shell', 'zsh'):
                cmds = ''.join(
                    f'<div><span class="prompt">$</span> {inline_format(l)}</div>'
                    for l in code_lines if l.strip()
                )
                title = code_lines[0].split()[0] if code_lines and code_lines[0].strip() else 'cmd'
                parts.append(
                    '<div class="cmd-block term-card"><div class="term-head">'
                    '<div class="term-dot"></div><div class="term-dot"></div><div class="term-dot"></div>'
                    f'<div class="term-title">{html.escape(title)}</div></div>'
                    f'<div class="term-body">{cmds}</div></div>'
                )
            else:
                body = '\n'.join(inline_format(l) for l in code_lines)
                parts.append(f'<div class="output-block">{body}</div>')
            continue

        if stripped.startswith('|'):
            table_lines = []
            while i < n and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            rows = [[c.strip() for c in l.strip('|').split('|')] for l in table_lines]
            rows = [r for r in rows if not all(re.match(r'^:?-+:?$', c) for c in r)]
            header, *body_rows = rows
            thead = ''.join(f'<th>{inline_format(c)}</th>' for c in header)
            tbody = ''.join(
                '<tr>' + ''.join(f'<td>{inline_format(c)}</td>' for c in r) + '</tr>'
                for r in body_rows
            )
            parts.append(f'<table class="writeup-table"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>')
            continue

        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < n and re.match(r'^[-*]\s+', lines[i].strip()):
                items.append(re.sub(r'^[-*]\s+', '', lines[i].strip()))
                i += 1
            lis = ''.join(f'<li>{inline_format(it)}</li>' for it in items)
            parts.append(f'<ul class="takeaway-list">{lis}</ul>')
            continue

        m = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
        if m:
            alt, src = m.group(1), m.group(2)
            parts.append(f'<img class="writeup-img" src="{html.escape(src)}" alt="{html.escape(alt)}">')
            i += 1
            continue

        para_lines = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(r'^(#{2,3}\s|```|\||[-*]\s)', lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1
        parts.append(f'<p>{inline_format(" ".join(para_lines))}</p>')

    return '\n      '.join(parts)


DIFF_CLASS = {'easy': 'easy', 'medium': 'medium', 'hard': 'hard', 'insane': 'insane'}

ALLOWED_TAGS = {
    # Access / Exploitation
    'web', 'sqli', 'ssti', 'ssrf', 'lfi', 'rfi', 'file upload',
    'command injection', 'rce', 'authentication', 'brute force',
    # Privilege Escalation
    'linux privesc', 'windows privesc', 'sudo', 'suid', 'capabilities',
    'cron', 'kernel exploit', 'service exploit', 'credential abuse',
    # Other
    'ftp', 'ssh', 'wordpress', 'active directory', 'smb', 'api',
    'enumeration', 'misconfiguration',
}

TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} // Lab Report // crimson</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<link rel="stylesheet" href="../styles.css">
</head>
<body>

<div class="grid-bg"></div>
<div class="glow"></div>
<div class="crt-overlay" aria-hidden="true"></div>

<header class="site">
  <nav>
    <div class="logo glitch">~/<span>crimson</span>▋</div>
    <div class="navlinks">
      <a href="../index.html">Home</a>
      <a href="../blog.html">Blog</a>
      <a href="../reports.html" class="active">Lab Reports</a>
      <a href="../methodology.html">Methodology</a>
      <a href="../projects.html">Projects</a>
      <a href="../aboutme.html">About Me</a>
    </div>
    <div class="nav-status"><span class="status-dot"></span>online</div>
  </nav>
</header>

<main>

  <section class="page-head reveal visible" style="border-bottom:none;padding-bottom:0;">
    <a href="../reports.html" class="back-link">← ls reports/</a>
    <div class="eyebrow scramble">cat {slug}.md</div>
    <h1 class="page-title scramble glitch glow-heading">{title}</h1>
    <div class="writeup-meta">
      <span class="tag">HTB</span><span class="tag diff {diff_class}">{difficulty}</span>{tag_pills}<span class="writeup-date">Solved: {date}</span>
    </div>
    <p class="writeup-summary">{summary}</p>
  </section>

  <section class="reveal visible">
    <div class="writeup-body">
      {body}
    </div>
  </section>

</main>

<footer class="site" style="padding-top:0;">
  <div class="foot-bottom" style="max-width:1100px;margin:0 auto;padding:24px;border-top:1px solid var(--border);">
    <div>crimson © 2026</div>
    <div><a href="../reports.html" style="color:var(--text-dim);">← back to Lab Reports</a></div>
  </div>
</footer>

<script src="../script.js"></script>
</body>
</html>
'''


def update_reports_page(reports_path: Path, slug: str, difficulty: str, diff_class: str, title: str, tags: list, date: str):
    if not reports_path.exists():
        return None  # caller falls back to manual instructions

    text = reports_path.read_text(encoding='utf-8-sig')

    tags_attr = ','.join(t.lower() for t in tags)
    card_html = (
        f'      <a href="writeups/report-{slug}.html" class="report-card" data-difficulty="{diff_class}" data-tags="{html.escape(tags_attr)}">\n'
        f'        <div class="report-top">\n'
        f'          <div class="report-tags"><span class="tag">HTB</span><span class="tag diff {diff_class}">{html.escape(difficulty)}</span></div>\n'
        f'          <div class="report-title">{html.escape(title)}</div>\n'
        f'          <div class="report-date">{html.escape(date)}</div>\n'
        f'        </div>\n'
        f'        <div class="report-code">\u250c\u2500\u2500(crimson\u327fkali)-[~/htb/{html.escape(difficulty)}]<br><span class="p1">\u2514\u2500$</span> your-command-here</div>\n'
        f'        <div class="report-foot"><span>{" \u00b7 ".join(tags[:2]) if tags else "summary here"}</span><span class="foot-right"><span class="root-status">ROOT</span><span class="open">open \u2192</span></span></div>\n'
        f'      </a>'
    )

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

    reports_path.write_text(text, encoding='utf-8')
    return action


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_report.py <writeup.md>")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"File not found: {md_path}")
        sys.exit(1)

    raw_text = md_path.read_text(encoding='utf-8-sig')
    raw_text = re.sub(r'<!--.*?-->', '', raw_text, flags=re.DOTALL)  # strip HTML comments before parsing
    lines = raw_text.splitlines(keepends=True)
    meta, body_lines = parse_frontmatter(lines)

    if not meta:
        print("\n\u26a0  STOPPED \u2014 no frontmatter found.")
        print("The very first line of your .md file needs to be exactly: ---")
        print("followed by title/difficulty/tags/summary lines, then another --- to close it.")
        print("\nThis usually happens when text gets copied out of a rendered doc/chat/notes app")
        print("instead of a plain-text source \u2014 headings, bullets, and code blocks lose their")
        print("markdown symbols (##, ```, -, ---) and become plain paragraphs.")
        print("\nOpen report-template.md to see the exact format, and write directly in a plain")
        print("text editor (VS Code, Notepad++) rather than pasting from something styled.")
        print("No file was written.")
        sys.exit(1)

    title = meta.get('title', md_path.stem)
    difficulty = meta.get('difficulty', 'Medium')
    diff_class = DIFF_CLASS.get(difficulty.lower(), '')
    summary = meta.get('summary', '')
    date = meta.get('date', 'date not set')
    tags = [t.strip() for t in meta.get('tags', '').split(',') if t.strip()]
    pill_tags = [t for t in tags if t.lower() != 'htb']  # avoid double "HTB" — it's already hardcoded below
    tag_pills = ''.join(f'<span class="tag">{html.escape(t)}</span>' for t in pill_tags)

    bad_tags = [t for t in pill_tags if t.lower() not in ALLOWED_TAGS]
    if bad_tags:
        print(f"\u26a0  tag(s) not in your approved list, double-check these: {', '.join(bad_tags)}")

    slug = slugify(title)
    body_html = parse_body(body_lines)

    if '<h2' not in body_html:
        print("\u26a0  no '## Heading' sections were detected in the body \u2014 double check your")
        print("   section headers actually start with ## (not just plain bold/large text).")

    out_html = TEMPLATE.format(
        title=html.escape(title), slug=slug, difficulty=html.escape(difficulty),
        diff_class=diff_class, tag_pills=tag_pills, summary=inline_format(summary),
        date=html.escape(date), body=body_html
    )

    writeups_dir = md_path.parent / 'writeups'
    writeups_dir.mkdir(exist_ok=True)
    out_path = writeups_dir / f"report-{slug}.html"
    out_path.write_text(out_html, encoding='utf-8')
    print(f"\u2714 wrote {out_path.name}")

    reports_path = md_path.parent / 'reports.html'
    action = update_reports_page(reports_path, slug, difficulty, diff_class, title, pill_tags, date)

    if action:
        print(f"\u2714 {action} the card on reports.html \u2014 just refresh your browser")
    else:
        print('''
Couldn't find reports.html next to this file (or no <div class="card-grid"> in it),
so paste this in manually instead:

      <a href="writeups/report-{slug}.html" class="report-card">
        <div class="report-top">
          <div class="report-tags"><span class="tag">HTB</span><span class="tag diff {diff_class}">{difficulty}</span></div>
          <div class="report-title">{title}</div>
          <div class="report-date">{date}</div>
        </div>
        <div class="report-code">\u250c\u2500\u2500(crimson\u327fkali)-[~/htb/{difficulty}]<br><span class="p1">\u2514\u2500$</span> your-command-here</div>
        <div class="report-foot"><span>{tagline}</span><span class="foot-right"><span class="root-status">ROOT</span><span class="open">open \u2192</span></span></div>
      </a>
'''.format(slug=slug, diff_class=diff_class, difficulty=difficulty, title=title, date=date,
           tagline=' \u00b7 '.join(pill_tags[:2]) if pill_tags else 'summary here'))


if __name__ == '__main__':
    main()
