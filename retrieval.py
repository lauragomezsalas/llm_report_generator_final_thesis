import os
import re
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import urlparse

from experiment_config import (
    RETRIEVAL_NUM_RESULTS,
    RETRIEVAL_TOP_K,
    RETRIEVAL_TIMEOUT_SECONDS,
    PAGE_FETCH_TIMEOUT_SECONDS,
    PAGE_FETCH_MAX_CHARS,
)

import requests
from bs4 import BeautifulSoup

from config import SERPER_API_KEY


CACHE_DIR = "retrieval_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

BLOCKED_DOMAINS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "pinterest.com",
}

PREFERRED_DOMAINS = {
    "mckinsey.com",
    "bain.com",
    "bcg.com",
    "deloitte.com",
    "pwc.com",
    "kpmg.com",
    "ey.com",
    "europa.eu",
    "oecd.org",
    "statista.com",
    "sciencedirect.com",
    "mdpi.com",
    "reuters.com",
    "ft.com",
    "wsj.com",
    "thegrocer.co.uk",
}


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _load_cache(hash_key: str):
    path = os.path.join(CACHE_DIR, f"{hash_key}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(hash_key: str, data: dict):
    path = os.path.join(CACHE_DIR, f"{hash_key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _call_serper(query: str, num_results: int = RETRIEVAL_NUM_RESULTS) -> dict:
    if not SERPER_API_KEY:
        raise ValueError("Missing SERPER_API_KEY in environment variables.")

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": num_results,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=RETRIEVAL_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _extract_page_text(url: str, max_chars: int = PAGE_FETCH_MAX_CHARS) -> str:
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=PAGE_FETCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
            tag.decompose()

        texts = []
        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            txt = tag.get_text(" ", strip=True)
            if txt:
                texts.append(txt)

        content = _clean_text(" ".join(texts))
        return content[:max_chars]
    except Exception:
        return ""


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""
    
def _is_blocked_domain(domain: str) -> bool:
    return domain in BLOCKED_DOMAINS

def _looks_like_low_value_content(content: str) -> bool:
    if not content:
        return True

    lowered = content.lower()

    junk_patterns = [
        "accept cookies",
        "cookie policy",
        "sign in",
        "log in",
        "privacy policy",
        "join now",
        "linkedin and 3rd parties use essential and non-essential cookies",
    ]

    if len(content.strip()) < 150:
        return True

    if any(pat in lowered for pat in junk_patterns):
        return True

    return False

def _extract_year(*texts: str) -> str:
    combined = " ".join([t for t in texts if t])
    match = re.search(r"\b(20\d{2}|19\d{2})\b", combined)
    return match.group(1) if match else "n.d."


def _extract_author(title: str, link: str, source_domain: str) -> str:
    domain = source_domain or _domain(link)

    domain_map = {
        "mckinsey.com": "McKinsey & Company",
        "bain.com": "Bain & Company",
        "bcg.com": "Boston Consulting Group",
        "deloitte.com": "Deloitte",
        "pwc.com": "PwC",
        "kpmg.com": "KPMG",
        "ey.com": "EY",
        "savills.es": "Savills",
        "savills.com": "Savills",
        "europa.eu": "European Commission",
        "oecd.org": "OECD",
        "statista.com": "Statista",
        "sciencedirect.com": "ScienceDirect",
        "mdpi.com": "MDPI",
    }

    if domain in domain_map:
        return domain_map[domain]

    if domain:
        first_part = domain.split(".")[0]
        return first_part.replace("-", " ").title()

    return "Unknown"


def _build_apa_in_text_citation(author: str, year: str) -> str:
    return f"({author}, {year})"


def _build_apa_reference(author: str, year: str, title: str, link: str, source_domain: str) -> str:
    safe_author = author or "Unknown"
    safe_year = year or "n.d."
    safe_title = title or "Untitled source"
    safe_domain = source_domain or _domain(link)

    if link:
        return f"{safe_author}. ({safe_year}). {safe_title}. {safe_domain}. {link}"
    return f"{safe_author}. ({safe_year}). {safe_title}. {safe_domain}."

def _score_document(doc: dict, keywords: list[str]) -> float:
    text = f"{doc.get('title', '')} {doc.get('snippet', '')} {doc.get('content', '')}".lower()
    score = 0.0

    for kw in keywords:
        if kw and kw.lower() in text:
            score += 1.0

    if any(ch.isdigit() for ch in text):
        score += 0.5

    domain = doc.get("source_domain", "")

    if domain in PREFERRED_DOMAINS:
        score += 2.0

    if domain in BLOCKED_DOMAINS:
        score -= 3.0

    content = doc.get("content", "")
    if _looks_like_low_value_content(content):
        score -= 2.0
    else:
        score += 0.5

    return round(score, 2)


def build_retrieval_query(
    consultant_brief: dict | None,
    problem_structuring_output: dict,
) -> str:
    consultant_brief = consultant_brief or {}

    company_name = consultant_brief.get("company_name", "")
    geography = consultant_brief.get("geography", "")
    sector = consultant_brief.get("sector", "grocery retail")
    sub_sector = consultant_brief.get("sub_sector", "")
    main_problem = consultant_brief.get("main_problem", "")
    objectives = consultant_brief.get("objectives", []) or []
    preferred_source_types = consultant_brief.get("preferred_source_types", []) or []
    preferred_domains = consultant_brief.get("preferred_domains", []) or []
    recency_preference = consultant_brief.get("recency_preference", "")

    market_analysis = problem_structuring_output.get("market_analysis", "")
    key_challenges = problem_structuring_output.get("key_challenges", []) or []
    areas_of_improvement = problem_structuring_output.get("areas_of_improvement", []) or []
    strategic_questions = problem_structuring_output.get("strategic_questions", []) or []

    parts = [
        geography,
        sector,
        sub_sector,
        main_problem,
    ]

    # Keep the query tighter and more searchable
    parts.extend(key_challenges[:2])
    parts.extend(objectives[:2])

    source_terms = []
    source_type_map = {
        "consulting reports": "site:mckinsey.com OR site:bain.com OR site:bcg.com OR site:deloitte.com OR site:pwc.com OR site:kpmg.com OR site:ey.com",
        "company filings": "annual report investor relations company results",
        "academic research": "site:sciencedirect.com OR site:mdpi.com OR site:springer.com",
        "regulators": "site:europa.eu OR site:oecd.org",
        "industry news": "retail industry news grocery market trends",
        "market data": "market share consumer trends price sensitivity grocery retail",
    }

    for src in preferred_source_types:
        mapped = source_type_map.get(str(src).strip().lower())
        if mapped:
            source_terms.append(mapped)

    if preferred_domains:
        domain_string = " OR ".join([f"site:{d}" for d in preferred_domains if str(d).strip()])
        if domain_string:
            source_terms.append(domain_string)

    if recency_preference:
        parts.append(f"Recency preference: {recency_preference}")

    parts.extend(source_terms)

    query = " ".join([str(p).strip() for p in parts if str(p).strip()])
    return query[:400]


def retrieve_external_context_raw(query: str) -> dict:
    start_time = time.time()

    hash_key = _hash_query(query)
    cached = _load_cache(hash_key)
    if cached and cached.get("documents"):
        cached["cache_hit"] = True
        return cached

    raw_results = _call_serper(query=query, num_results=RETRIEVAL_NUM_RESULTS)
    keywords = [
        "spain",
        "supermarket",
        "grocery",
        "margin",
        "discount",
        "supply chain",
        "customer loyalty",
        "retail",
    ]

    retrieval_keywords = list(keywords)

    documents = []
    evidence_counter = 1

    for idx, item in enumerate(raw_results.get("organic", []), start=1):
        link = item.get("link", "")
        source_domain = _domain(link)

        if _is_blocked_domain(source_domain):
            continue

        content = _extract_page_text(link)

        if _looks_like_low_value_content(content):
            continue

        title = item.get("title", "")
        snippet = item.get("snippet", "")
        author = _extract_author(title, link, source_domain)
        year = _extract_year(title, snippet, content)

        doc = {
            "evidence_id": f"E{evidence_counter}",
            "search_rank": idx,
            "title": title,
            "link": link,
            "snippet": snippet,
            "source_domain": source_domain,
            "content": content,
            "authors": author,
            "year": year,
            "apa_in_text_citation": _build_apa_in_text_citation(author, year),
            "apa_reference": _build_apa_reference(author, year, title, link, source_domain),
        }
        doc["relevance_score"] = _score_document(doc, keywords)
        documents.append(doc)
        evidence_counter += 1

    documents = sorted(
        documents,
        key=lambda x: x.get("relevance_score", 0.0),
        reverse=True,
    )[:RETRIEVAL_TOP_K]

    retrieval_data = {
        "query": query,
        "documents": documents,
        "cache_hit": False,
        "retrieval_latency": round(time.time() - start_time, 4),
        "timestamp": datetime.utcnow().isoformat(),
        "retrieval_keywords": retrieval_keywords,
    }

    _save_cache(hash_key, retrieval_data)
    return retrieval_data