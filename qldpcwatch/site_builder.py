# ruff: noqa: E501
from __future__ import annotations

import html
import json
from pathlib import Path

from qldpcwatch.io_utils import read_json

HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QLDPC Watch</title>
  <style>
    :root {
      --bg: #f5f7f4;
      --fg: #182122;
      --muted: #4f5f63;
      --card: #ffffff;
      --accent: #0a7a64;
      --line: #d7e1df;
    }
    body { margin: 0; font-family: "IBM Plex Sans", "Segoe UI", sans-serif; background: linear-gradient(180deg, #edf3ef 0%, #f8fbfa 100%); color: var(--fg); }
    .wrap { max-width: 960px; margin: 0 auto; padding: 24px; }
    h1 { margin-top: 0; letter-spacing: -0.02em; }
    .search { width: 100%; padding: 12px; border: 1px solid var(--line); border-radius: 8px; font-size: 15px; }
    .item { border: 1px solid var(--line); border-radius: 10px; padding: 14px; background: var(--card); margin-top: 12px; }
    .meta { color: var(--muted); font-size: 13px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>QLDPC Watch</h1>
    <p>Local index of arXiv papers on decoding quantum LDPC codes.</p>
    <input id=\"q\" class=\"search\" placeholder=\"Search title, category, decoder family...\" />
    <div id=\"results\"></div>
  </div>
  <script>
    const data = __PAPERS__;
    const el = document.getElementById('results');
    const q = document.getElementById('q');

    function render(items) {
      el.innerHTML = items.map(p => `
        <div class=\"item\">
          <div><a href=\"${p.links.abs_url}\" target=\"_blank\" rel=\"noreferrer\">${p.title}</a></div>
          <div class=\"meta\">${p.arxiv_id}${p.arxiv_version} | ${p.primary_category} | relevance=${p.relevance?.label ?? 'unknown'}</div>
          <div class=\"meta\">decoder=${p.decoder?.decoder_family ?? 'unknown'} | updated=${p.updated_date}</div>
        </div>
      `).join('');
    }

    function filter() {
      const needle = q.value.trim().toLowerCase();
      if (!needle) return render(data);
      const items = data.filter(p => {
        const text = [
          p.title,
          p.abstract,
          p.primary_category,
          (p.categories || []).join(' '),
          p.relevance?.label,
          p.decoder?.decoder_family,
          p.decoder?.name
        ].join(' ').toLowerCase();
        return text.includes(needle);
      });
      render(items);
    }

    q.addEventListener('input', filter);
    render(data);
  </script>
</body>
</html>
"""


def rebuild_site(index_json_path: Path, site_dir: Path) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    index = read_json(index_json_path)

    # Keep a machine-readable copy too.
    (site_dir / "papers.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    html_payload = HTML_TEMPLATE.replace(
        "__PAPERS__", html.escape(json.dumps(index, ensure_ascii=False))
    )
    # Undo over-escaping for JSON string delimiters inside script block.
    html_payload = html_payload.replace("&quot;", '"')
    (site_dir / "index.html").write_text(html_payload, encoding="utf-8")
    return site_dir / "index.html"
