#!/usr/bin/env python3
"""
Print-optimised HTML for the SSRN PDF, rendered via headless Chrome.

Differs from the web page: single light theme, Letter page geometry with real
margins, a title block carrying the SSRN front matter (abstract, keywords, JEL),
figures constrained to the text block, and page-break rules so tables and
figures are not split across pages.
"""
import base64, os, re, subprocess

REPO = "/Users/joshuajohnson/Drive/Documents/Projects/M_Supply/"
HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "fig")
HTML = os.path.join(HERE, "pstar_print.html")
PDF = os.path.join(REPO, "paper", "Johnson-2026-pstar-real-time.pdf")

KEYWORDS = ("P-star, Divisia monetary aggregates, real-time data, "
            "Hodrick-Prescott filter, Hamilton filter, inflation forecasting, "
            "monetary policy, output gap, data revisions")
JEL = "E31, E37, E41, E52, C22"

body = subprocess.run(["pandoc", os.path.join(REPO, "PAPER.md"), "-t", "html",
                       "--no-highlight"], capture_output=True, text=True).stdout
body = body[body.index('<h2 id="abstract">'):]


def datauri(name):
    with open(os.path.join(FIG, name), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def figrepl(m):
    src, cap = m.group("src"), m.group("cap")
    n = re.match(r"\s*<strong>Figure (\d+)\.</strong>", cap)
    num = n.group(1) if n else ""
    cap = re.sub(r"\s*<strong>Figure \d+\.</strong>\s*", "", cap)
    return (f'<figure class="fig"><img src="{datauri(src)}" alt="Figure {num}" />'
            f'<figcaption><b>Figure {num}.</b> {cap}</figcaption></figure>')


body = re.sub(r'<figure>\s*<img src="(?P<src>[^"]+\.png)"[^>]*/>\s*'
              r'<figcaption[^>]*>.*?</figcaption>\s*</figure>\s*<p>(?P<cap>.*?)</p>',
              figrepl, body, flags=re.S)
body = body.replace("<table>", '<div class="tw"><table>').replace("</table>", "</table></div>")
body = re.sub(r'<p><strong>(Table \d+\.[^<]*)</strong></p>', r'<p class="tcap">\1</p>', body)
body = body.replace("<blockquote>", '<blockquote class="eq">')

# number the sections
def h2(m):
    hid, txt = m.group(1), m.group(2)
    n = re.match(r"(\d+)\.\s+(.*)", txt)
    return (f'<h2 id="{hid}">{n.group(1)}. {n.group(2)}</h2>' if n
            else f'<h2 id="{hid}">{txt}</h2>')

body = re.sub(r'<h2 id="([^"]+)">(.*?)</h2>', h2, body, flags=re.S)

# the abstract heading is replaced by the front matter block
body = re.sub(r'<h2 id="abstract">.*?</h2>', '', body, count=1, flags=re.S)
i = body.index('<h2 id="introduction">')
abstract, rest = body[:i], body[i:]
rest = re.sub(r'(<h2 id="references">.*?</h2>)(.*)$',
              lambda m: m.group(1) + '<div class="refs">' + m.group(2) + "</div>",
              rest, flags=re.S)

CSS = """<style>
@page { size: Letter; margin: 22mm 20mm 20mm 20mm; }
* { box-sizing: border-box; }
body { font-family: Charter, "Bitstream Charter", "Iowan Old Style", Georgia, serif;
       font-size: 10.4pt; line-height: 1.48; color: #14191b; margin: 0;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }
p { margin: 0 0 .62em; text-align: justify; hyphens: auto; }
a { color: #0f5257; text-decoration: none; }
h1 { font-size: 19pt; line-height: 1.16; font-weight: 600; margin: 0 0 .35em;
     letter-spacing: -.01em; }
.sub { font-size: 11.6pt; font-style: italic; color: #4a5459; margin: 0 0 1.3em; }
.byline { font-size: 10pt; margin: 0 0 .25em; }
.byline b { font-weight: 650; }
.dateline { font-size: 9.2pt; color: #4a5459; margin: 0 0 1.6em;
            font-family: system-ui, sans-serif; }
.fm { border-top: 1.2pt solid #14191b; border-bottom: .5pt solid #c9d0cf;
      padding: .9em 0 1em; margin: 0 0 1.6em; }
.fm h3 { font-family: system-ui, sans-serif; font-size: 8pt; letter-spacing: .12em;
         text-transform: uppercase; color: #6f797d; margin: 0 0 .5em; font-weight: 650; }
.fm p { font-size: 9.5pt; line-height: 1.44; }
.meta2 { font-size: 8.8pt; color: #4a5459; font-family: system-ui, sans-serif;
         margin-top: .9em; line-height: 1.5; }
.meta2 b { color: #14191b; }
h2 { font-size: 12.6pt; font-weight: 650; margin: 1.7em 0 .55em;
     padding-top: .5em; border-top: .5pt solid #dde3e2;
     break-after: avoid; page-break-after: avoid; }
h3 { font-family: system-ui, sans-serif; font-size: 9.6pt; font-weight: 650;
     margin: 1.2em 0 .4em; break-after: avoid; page-break-after: avoid; }
.tcap { font-family: system-ui, sans-serif; font-size: 8.8pt; font-weight: 650;
        margin: 1.3em 0 .4em; break-after: avoid; page-break-after: avoid; }
.tw { break-inside: avoid; page-break-inside: avoid; margin: 0 0 1.1em; }
table { border-collapse: collapse; width: 100%; font-family: system-ui, sans-serif;
        font-size: 8.2pt; font-variant-numeric: tabular-nums; }
thead th { text-align: left; font-size: 7.4pt; letter-spacing: .04em;
           text-transform: uppercase; color: #4a5459; padding: .32em .45em;
           border-bottom: .8pt solid #6f797d; font-weight: 650; }
tbody td { padding: .3em .45em; border-bottom: .4pt solid #eceeed; color: #2c3438; }
tbody td:first-child { color: #14191b; }
th:not(:first-child), td:not(:first-child) { text-align: right; }
.fig { break-inside: avoid; page-break-inside: avoid; margin: 1.3em 0 1.5em; }
.fig img { width: 100%; height: auto; display: block; border: .5pt solid #dde3e2; }
.fig figcaption { font-family: system-ui, sans-serif; font-size: 8.4pt;
                  line-height: 1.42; color: #4a5459; margin-top: .45em; text-align: left; }
.eq { margin: .9em 0; padding: .55em .8em; background: #0f52570f; border-radius: 2px;
      font-family: ui-monospace, Menlo, monospace; font-size: 8.8pt; line-height: 1.55; }
.eq p { margin: 0; text-align: left; }
code { font-family: ui-monospace, Menlo, monospace; font-size: .88em; }
.refs p { font-size: 9pt; line-height: 1.4; padding-left: 1.5em; text-indent: -1.5em;
          text-align: left; margin-bottom: .45em; }
hr { display: none; }
ol, ul { margin: 0 0 .7em; padding-left: 1.3em; }
li { margin-bottom: .28em; }
</style>"""

FRONT = f"""
<h1>The P-Star Price Gap Is Not Identified in Real Time</h1>
<p class="sub">A replication and extension of Ireland, Miran and Roubini (2026),
&ldquo;A Return to Monetarism?&rdquo;</p>
<p class="byline"><b>Joshua Johnson</b> &nbsp;&middot;&nbsp; Independent researcher</p>
<p class="dateline">This version: 4 August 2026 &nbsp;&middot;&nbsp; supersedes the 30 July draft, in which
2026Q2 was a nowcast &nbsp;&middot;&nbsp; SSRN 7206999 &nbsp;&middot;&nbsp;
Replication code and data: github.com/josjo80/pstar-monetarism</p>
<div class="fm">
  <h3>Abstract</h3>
  {abstract}
  <p class="meta2"><b>Keywords:</b> {KEYWORDS}<br/>
  <b>JEL classification:</b> {JEL}</p>
</div>
"""

with open(HTML, "w") as fh:
    fh.write("<!doctype html><html><head><meta charset='utf-8'>" + CSS +
             "</head><body>" + FRONT + rest + "</body></html>")

os.makedirs(os.path.dirname(PDF), exist_ok=True)
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=20000", f"--print-to-pdf={PDF}",
                "file://" + HTML], capture_output=True)
print(f"wrote {PDF}  {os.path.getsize(PDF)/1024:.0f}KB")
