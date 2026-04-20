"""SEC EDGAR tools — insider filings and material events.

Two capabilities:
    get_insider_filings(ticker, limit) — recent Form 4 insider buys/sells
    get_recent_filings(ticker, limit)  — recent 8-K / 10-Q / 10-K filings

Both are free and official. EDGAR requires a `User-Agent` that identifies
you; set `EDGAR_USER_AGENT` in `.env` (e.g. "Your Name your@email.com").

Form 4 interpretation:
    transactionCode 'P' = purchase (bullish signal)
    transactionCode 'S' = sale     (often mechanical, noisier)
    transactionCode 'A' = award    (ignore)
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta

import httpx

from agent.config import Settings

_UA = os.environ.get("EDGAR_USER_AGENT") or "stockagent/1.0 contact@example.com"
_HEADERS = {"User-Agent": _UA, "Accept-Encoding": "gzip, deflate"}
_CIK_CACHE: dict[str, str] = {}


def _get_cik(ticker: str) -> str | None:
    ticker = ticker.upper()
    if ticker in _CIK_CACHE:
        return _CIK_CACHE[ticker]
    # The public company tickers file is small (<1 MB) and cached in memory.
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        r = httpx.get(url, headers=_HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for _, row in data.items():
            sym = (row.get("ticker") or "").upper()
            cik = str(row.get("cik_str") or "").zfill(10)
            _CIK_CACHE[sym] = cik
        return _CIK_CACHE.get(ticker)
    except Exception:
        return None


def _recent_filings(cik: str, form_types: set[str], limit: int) -> list[dict]:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = httpx.get(url, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    recent = (r.json().get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    prims = recent.get("primaryDocument") or []
    out: list[dict] = []
    for f, d, a, p in zip(forms, dates, accs, prims):
        if f not in form_types:
            continue
        acc_nodash = a.replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{p}"
        out.append({"form": f, "date": d, "accession": a, "url": doc_url})
        if len(out) >= limit:
            break
    return out


def get_recent_filings(settings: Settings, ticker: str, limit: int = 10) -> list[dict]:
    cik = _get_cik(ticker)
    if not cik:
        return []
    try:
        return _recent_filings(cik, {"8-K", "10-K", "10-Q", "S-1", "S-3"}, limit)
    except Exception:
        return []


def get_insider_filings(settings: Settings, ticker: str, limit: int = 10) -> list[dict]:
    """Recent Form 4 insider transactions.

    The submissions feed gives us the filings; we scrape each primary
    document's XML summary for transaction code + shares + price.
    Non-fatal: if a single filing fails to parse, we just skip it.
    """
    cik = _get_cik(ticker)
    if not cik:
        return []
    try:
        filings = _recent_filings(cik, {"4"}, limit * 2)
    except Exception:
        return []

    out: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=120)
    with httpx.Client(headers=_HEADERS, timeout=20) as client:
        for f in filings:
            try:
                fdate = datetime.strptime(f["date"], "%Y-%m-%d")
                if fdate < cutoff:
                    continue
                # Primary doc is usually a wrapper; the XML is in the index.
                idx_url = f["url"].rsplit("/", 1)[0] + "/"
                idx = client.get(idx_url).text
                xml_name = re.search(r'href="([^"]+\.xml)"', idx)
                if not xml_name:
                    continue
                xml_url = idx_url + xml_name.group(1)
                xml = client.get(xml_url).text
                name = _first(re.search(r"<rptOwnerName>([^<]+)</rptOwnerName>", xml))
                title = _first(re.search(r"<officerTitle>([^<]+)</officerTitle>", xml))
                code = _first(re.search(r"<transactionCode>([^<]+)</transactionCode>", xml))
                shares = _num(re.search(r"<transactionShares>\s*<value>([^<]+)</value>", xml))
                price = _num(re.search(r"<transactionPricePerShare>\s*<value>([^<]+)</value>", xml))
                if not code:
                    continue
                out.append({
                    "date": f["date"],
                    "insider": name,
                    "title": title,
                    "code": code,
                    "action": {"P": "buy", "S": "sell", "A": "award", "M": "exercise"}.get(code, code),
                    "shares": shares,
                    "price": price,
                    "value": (shares or 0) * (price or 0) if shares and price else None,
                    "url": f["url"],
                })
                if len(out) >= limit:
                    break
            except Exception:
                continue
    return out


def _first(m) -> str | None:
    return m.group(1).strip() if m else None


def _num(m) -> float | None:
    if not m:
        return None
    try:
        return float(m.group(1).strip())
    except ValueError:
        return None
