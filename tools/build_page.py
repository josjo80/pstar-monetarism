#!/usr/bin/env python3
"""Assemble the designed artifact page from PAPER.md via pandoc output."""
import base64, os, re, subprocess

REPO = "/Users/joshuajohnson/Drive/Documents/Projects/M_Supply/"
HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "fig")
OUT = os.path.join(HERE, "pstar_paper.html")

body = subprocess.run(["pandoc", os.path.join(REPO, "PAPER.md"), "-t", "html",
                       "--no-highlight"], capture_output=True, text=True).stdout

# drop everything before the Abstract heading -- the masthead is built by hand
body = body[body.index('<h2 id="abstract">'):]

# figures: pandoc emits <p><img …/></p> then <p><strong>Figure n.</strong> …</p>
def datauri(name):
    with open(os.path.join(FIG, name), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

def figrepl(m):
    src, cap = m.group("src"), m.group("cap")
    n = re.match(r"\s*<strong>Figure (\d+)\.</strong>", cap)
    num = n.group(1) if n else ""
    cap = re.sub(r"\s*<strong>Figure \d+\.</strong>\s*", "", cap)
    return (f'<figure class="fig"><img src="{datauri(src)}" alt="Figure {num}" '
            f'decoding="async" />'
            f'<figcaption><span class="fig-n">Fig. {num}</span>{cap}</figcaption></figure>')

# pandoc wraps the image in its own <figure> with a redundant aria-hidden caption;
# the real caption is the following paragraph
body = re.sub(
    r'<figure>\s*<img src="(?P<src>[^"]+\.png)"[^>]*/>\s*'
    r'<figcaption[^>]*>.*?</figcaption>\s*</figure>\s*<p>(?P<cap>.*?)</p>',
    figrepl, body, flags=re.S)

# tables get a scroll wrapper; table captions above them keep their own class
body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
body = re.sub(r'<p><strong>(Table \d+\.[^<]*)</strong></p>',
              r'<p class="tcap">\1</p>', body)

# blockquotes in this paper are displayed equations / identities
body = body.replace("<blockquote>", '<blockquote class="eq">')

# number the h2s that are numbered in the source; collect the TOC
toc = []
def h2(m):
    txt, hid = m.group(2), m.group(1)
    n = re.match(r"(\d+)\.\s+(.*)", txt)
    if n:
        toc.append((n.group(1), n.group(2), hid))
        return (f'<h2 id="{hid}"><span class="secn">{n.group(1)}</span>'
                f'<span>{n.group(2)}</span></h2>')
    toc.append(("", txt, hid))
    return f'<h2 id="{hid}"><span class="secn"></span><span>{txt}</span></h2>'

body = re.sub(r'<h2 id="([^"]+)">(.*?)</h2>', h2, body, flags=re.S)

toc_html = "\n".join(
    f'<li><a href="#{hid}"><span class="tn">{n}</span>{t}</a></li>' for n, t, hid in toc)

CSS = """
<style>
  .pp { color-scheme: light;
    --paper:#f7f8f7; --panel:#fdfdfc; --ink:#14191b; --ink2:#4a5459; --ink3:#7b858a;
    --accent:#0f5257; --accent-w:#0f525714; --flag:#8c3a2b; --rule:#dde3e2; --rule2:#eceeed;
    --serif: Charter, "Bitstream Charter", "Iowan Old Style", "Source Serif Pro", Georgia, serif;
    --sans: system-ui, -apple-system, "Segoe UI", Helvetica, sans-serif;
    --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace; }
  @media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) .pp {
    color-scheme: dark;
    --paper:#14181a; --panel:#191e20; --ink:#e8eceb; --ink2:#a7b1b1; --ink3:#7d8789;
    --accent:#63b8bc; --accent-w:#63b8bc1f; --flag:#d98876; --rule:#28312f; --rule2:#1e2426; } }
  :root[data-theme="dark"] .pp { color-scheme: dark;
    --paper:#14181a; --panel:#191e20; --ink:#e8eceb; --ink2:#a7b1b1; --ink3:#7d8789;
    --accent:#63b8bc; --accent-w:#63b8bc1f; --flag:#d98876; --rule:#28312f; --rule2:#1e2426; }

  .pp { background:var(--paper); color:var(--ink); font-family:var(--serif);
        font-size:clamp(16.5px,1.05vw + 13px,18.5px); line-height:1.62;
        -webkit-font-smoothing:antialiased; padding:0 0 6rem; }
  .pp *, .pp *::before, .pp *::after { box-sizing:border-box; }
  .wrap { max-width:min(66ch, calc(100vw - 3rem)); margin-inline:auto; }
  .pp p, .pp ul, .pp ol { margin:0 0 1.05em; }
  .pp a { color:var(--accent); text-underline-offset:.18em;
          text-decoration-thickness:.06em; }
  .pp a:focus-visible, .pp summary:focus-visible {
          outline:2px solid var(--accent); outline-offset:3px; border-radius:2px; }

  /* masthead ------------------------------------------------------------- */
  .mast { border-bottom:1px solid var(--rule); padding:clamp(3rem,7vw,5.5rem) 0 2.4rem;
          margin-bottom:2.8rem; }
  .kicker { font-family:var(--sans); font-size:.7rem; letter-spacing:.16em;
            text-transform:uppercase; color:var(--accent); font-weight:600;
            margin:0 0 1.4rem; }
  .mast h1 { font-size:clamp(1.95rem,3.4vw + .9rem,3.05rem); line-height:1.12;
             letter-spacing:-.015em; font-weight:600; margin:0 0 .6rem;
             text-wrap:balance; }
  .sub { font-size:clamp(1.02rem,1vw + .7rem,1.22rem); color:var(--ink2);
         font-style:italic; margin:0 0 1.9rem; text-wrap:balance; }
  .meta { font-family:var(--sans); font-size:.86rem; color:var(--ink2);
          display:flex; flex-wrap:wrap; gap:.45rem 1.4rem; align-items:baseline; }
  .meta .who { color:var(--ink); font-weight:600; }

  /* table of contents ---------------------------------------------------- */
  .toc { margin:0 0 3rem; padding:1.3rem 1.5rem; background:var(--panel);
         border:1px solid var(--rule); border-radius:3px; }
  .pp .toc h2 { font-family:var(--sans); font-size:.7rem; letter-spacing:.14em;
            text-transform:uppercase; color:var(--ink3); margin:0 0 .9rem;
            font-weight:600; border:0; padding:0; display:block; }
  .toc ol { list-style:none; margin:0; padding:0; columns:2; column-gap:2rem; }
  @media (max-width:640px){ .toc ol { columns:1; } }
  .toc li { break-inside:avoid; margin:0 0 .42em; }
  .toc a { font-family:var(--sans); font-size:.88rem; text-decoration:none;
           color:var(--ink2); display:flex; gap:.55rem; }
  .toc a:hover { color:var(--accent); }
  .tn { font-family:var(--mono); font-size:.78rem; color:var(--ink3);
        min-width:1.1rem; font-variant-numeric:tabular-nums; }

  /* headings ------------------------------------------------------------- */
  .pp h2 { font-size:clamp(1.28rem,1.5vw + .8rem,1.62rem); line-height:1.22;
           font-weight:600; letter-spacing:-.008em; margin:3.2rem 0 1rem;
           padding-top:1.4rem; border-top:1px solid var(--rule);
           display:flex; gap:.85rem; text-wrap:balance; scroll-margin-top:1.5rem; }
  .secn { font-family:var(--mono); font-size:.78em; color:var(--accent);
          font-weight:400; padding-top:.28em; font-variant-numeric:tabular-nums;
          min-width:1.4rem; }
  .pp h2 .secn:empty { display:none; }
  .pp h3 { font-family:var(--sans); font-size:.95rem; font-weight:650;
           letter-spacing:.01em; color:var(--ink); margin:2.2rem 0 .7rem; }

  /* abstract ------------------------------------------------------------- */
  .abs { background:var(--panel); border:1px solid var(--rule);
         border-left:2px solid var(--accent); border-radius:3px;
         padding:1.6rem clamp(1.2rem,2.5vw,2rem); margin:0 0 1.4rem; }
  .abs p { font-size:.96em; }
  .abs p:last-child { margin-bottom:0; }

  /* figures -------------------------------------------------------------- */
  .fig { margin:2.4rem 0 2.6rem; max-width:min(96ch, calc(100vw - 3rem));
         margin-inline:auto; }
  .fig img { width:100%; height:auto; display:block; border:1px solid var(--rule);
             border-radius:3px; background:#fcfcfb; }
  .fig figcaption { font-family:var(--sans); font-size:.83rem; line-height:1.5;
                    color:var(--ink2); margin-top:.75rem; max-width:72ch; }
  .fig-n { font-weight:650; color:var(--ink); margin-right:.45em;
           letter-spacing:.02em; }

  /* tables --------------------------------------------------------------- */
  .tcap { font-family:var(--sans); font-size:.83rem; font-weight:650;
          letter-spacing:.01em; color:var(--ink); margin:2.2rem 0 .6rem; }
  .tw { overflow-x:auto; margin:0 0 1.8rem; max-width:min(96ch, calc(100vw - 3rem));
        margin-inline:auto; border-bottom:1px solid var(--rule); }
  .pp table { border-collapse:collapse; width:100%; font-family:var(--sans);
              font-size:.845rem; font-variant-numeric:tabular-nums; }
  .pp thead th { text-align:left; font-weight:600; color:var(--ink2);
                 font-size:.74rem; letter-spacing:.05em; text-transform:uppercase;
                 padding:.55rem .7rem; border-bottom:1px solid var(--ink3);
                 white-space:nowrap; }
  .pp tbody td { padding:.5rem .7rem; border-bottom:1px solid var(--rule2);
                 color:var(--ink2); }
  .pp tbody td:first-child { color:var(--ink); white-space:nowrap; }
  .pp thead th:first-child { white-space:nowrap; }
  .pp tbody tr:last-child td { border-bottom:0; }
  .pp td strong { color:var(--ink); font-weight:650; }
  .pp th:not(:first-child), .pp td:not(:first-child) { text-align:right; }

  /* equations / identities ----------------------------------------------- */
  .eq { margin:1.4rem 0; padding:.85rem 1.1rem; background:var(--accent-w);
        border-radius:3px; font-family:var(--mono); font-size:.83rem;
        line-height:1.65; color:var(--ink); overflow-x:auto; }
  .eq p { margin:0; }
  .pp code { font-family:var(--mono); font-size:.85em; color:var(--ink2);
             background:var(--rule2); padding:.1em .32em; border-radius:2px; }

  /* references + back matter --------------------------------------------- */
  #references + .refs p, .refs p { font-size:.87rem; line-height:1.5;
        padding-left:1.6rem; text-indent:-1.6rem; color:var(--ink2);
        margin-bottom:.75em; }
  .refs p em { color:var(--ink2); }
  .pp hr { border:0; border-top:1px solid var(--rule); margin:3rem 0; }

  .foot { margin-top:4rem; padding-top:1.6rem; border-top:1px solid var(--rule);
          font-family:var(--sans); font-size:.8rem; color:var(--ink3);
          display:flex; flex-wrap:wrap; gap:.4rem 1.5rem; }
  @media print { .toc, .foot { display:none; } .pp { font-size:10.5pt; } }
</style>
"""

MAST = """
<header class="mast"><div class="wrap">
  <p class="kicker">Replication &amp; extension &middot; Working draft</p>
  <h1>The P-Star Price Gap Is Not Identified in Real Time</h1>
  <p class="sub">A replication and extension of Ireland, Miran and Roubini (2026),
     &ldquo;A Return to Monetarism?&rdquo;</p>
  <div class="meta">
    <span class="who">Joshua Johnson</span>
    <span>Independent researcher</span>
    <span>30 July 2026</span>
    <span>Comments welcome</span>
    <span><a href="https://ssrn.com/abstract=7206999">SSRN 7206999 &#8599;</a></span>
    <span><a href="https://github.com/josjo80/pstar-monetarism">Code &amp; data &#8599;</a></span>
  </div>
</div></header>
"""

FOOT = """
<footer class="foot"><div class="wrap" style="display:flex;flex-wrap:wrap;gap:.4rem 1.5rem;">
  <span>Working draft &mdash; not peer reviewed.</span>
  <span>Every table and figure regenerates from the linked repository.</span>
</div></footer>
"""

# wrap the abstract body in its own block
body = re.sub(r'(<h2 id="abstract">.*?</h2>)(.*?)(?=<h2 )',
              lambda m: m.group(1) + '<div class="abs">' + m.group(2) + "</div>",
              body, flags=re.S)
# references get hanging indents
body = re.sub(r'(<h2 id="references">.*?</h2>)(.*)$',
              lambda m: m.group(1) + '<div class="refs">' + m.group(2) + "</div>",
              body, flags=re.S)

html = (f'<div class="pp">{CSS}{MAST}<div class="wrap">'
        f'<nav class="toc"><h2>Contents</h2><ol>{toc_html}</ol></nav>'
        f'{body}</div>{FOOT}</div>')

with open(OUT, "w") as fh:
    fh.write(html)
print(f"wrote {OUT}  {os.path.getsize(OUT)/1024:.0f}KB")
print(f"sections in TOC: {len(toc)}")
