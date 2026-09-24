# MSIL DA2.8 — Bug Zero Dashboard

Live GitHub Pages dashboard tracking open Bug Zero tickets for MSIL DA2.8, split by YTB and Non-YTB scope, sourced directly from the Elvis DB (`tbl_ElvisSR`).

## Pages

| Page | File | Description |
|---|---|---|
| Overview | [`index.html`](index.html) / [`overview.html`](overview.html) | Headline OPEN / CROSSED FPD / NO FPD counts and per-domain priority split for both scopes |
| YTB | [`ytb.html`](ytb.html) | Full YTB detail dashboard — domain breakdown, FPD Not Available, Crossed FPD, burn-rate trend, closing trend |
| Non-YTB | [`non-ytb.html`](non-ytb.html) | Full Non-YTB detail dashboard, same layout as YTB |

## Scope definitions

- Base filter: `ProjectID = 'MSIL_DA2.8'`, `IsDeleted = 'N'`, `ReferenceNumber <= 2`
- Open steps: `Categorizing`, `Reproduction`, `Processing`
- YTB scope: `FG_SWRev != 'P8_YTB_NA'`
- Non-YTB scope: `FG_SWRev = 'P8_YTB_NA'`

## Refreshing the data

All four pages are regenerated from a single live DB snapshot so headline, domain, FPD, and priority totals always reconcile with each other.

```powershell
& ".\.venv\Scripts\python.exe" scripts\update_overview_live.py
```

The script prints validation checks (open totals, No-FPD totals, Crossed-FPD totals) — only publish if it completes without assertion errors.

## Publishing

This branch (`gh-pages`) is mirrored to two remotes and must be pushed to both after a refresh:

```powershell
git add index.html overview.html ytb.html non-ytb.html
git commit -m "Refresh dashboard with live Elvis DB data"
git push origin gh-pages
git push harman gh-pages
```

`origin` hosts the public GitHub Pages site; `harman` hosts the internal HARMAN Enterprise Pages site (SSO-gated).
