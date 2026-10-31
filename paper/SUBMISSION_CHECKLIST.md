# Submission checklist (ICNLP 2027, anonymous)

| Item | Status | How checked |
|---|---|---|
| Author block blank | Done | audit: `\author{}` required |
| No names, affiliation, location hints, repository links, first-person self-reference | Done | audit anonymity check (fails on any hit) |
| Self-citation in third person (ICAI paper, "Ahmadnia et al.") | Done | manual; standard double-blind practice |
| Code availability without identifying link | Done | Limitations: "link withheld for anonymous review" |
| Acknowledgments and funding omitted for review | Done | none in the source |
| AI-use disclosure | Open | include only if the ICNLP instructions or submission form require it (one `\pending` marker) |
| 5 pages including references | Done | compile check (pdflatex + bibtex) |
| Fonts embedded | Done | `pdffonts`: all embedded |
| Every held-out number audited | Done | `python scripts/audit_manuscript.py` (79 claims) |
| Final mode | Open (24 Nov) | `\finaltrue` + `python scripts/audit_manuscript.py --final` |
| Public repository vs anonymity | Ask PI | repository is public under the owner's account and contains the paper title and reports with names |
