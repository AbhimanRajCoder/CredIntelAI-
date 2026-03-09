"""
Source Credibility Filter for corporate research.
Filters search results to trusted financial journalism domains.
"""

import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Trusted financial journalism and regulatory domains
TRUSTED_DOMAINS = {
    # Indian financial press
    "economictimes.indiatimes.com",
    "business-standard.com",
    "livemint.com",
    "moneycontrol.com",
    "thehindubusinessline.com",
    "financialexpress.com",
    "ndtv.com",
    "thehindu.com",
    "zeebiz.com",
    "cnbctv18.com",
    # International
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    # Regulatory / legal
    "rbi.org.in",
    "sebi.gov.in",
    "mca.gov.in",
    "indiankanoon.org",
    "livelaw.in",
    "barandbench.com",
    # Rating agencies
    "crisil.com",
    "icraresearch.in",
    "icra.in",
    "careratings.com",
    "indiaratings.co.in",
    # Financial data
    "screener.in",
    "trendlyne.com",
    "finitree.com",
}

# Domains to strictly exclude (social media, user-generated content)
SOCIAL_MEDIA_BLACKLIST = {
    "youtube.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "reddit.com",
    "quora.com",
    "wikipedia.org",
}


def extract_domain(url: str) -> str:
    """Extract the base domain from a URL."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        # Strip leading "www."
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return ""


def is_trusted_source(url: str) -> bool:
    """Check whether a URL belongs to a trusted domain."""
    domain = extract_domain(url)
    
    # Check blacklist first
    for blacklisted in SOCIAL_MEDIA_BLACKLIST:
        if domain == blacklisted or domain.endswith(f".{blacklisted}"):
            return False
            
    # Check trusted list
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith(f".{trusted}"):
            return True
    return False


def filter_results(
    results: List[Dict[str, Any]],
    url_key: str = "link",
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """
    Filter search results by source credibility.
    ALWAYS discards blacklisted domains (YouTube, Facebook, etc.).

    Args:
        results: List of result dicts
        url_key: Key name for the URL
        strict: If True, only return trusted sources. If False, include all non-blacklisted.

    Returns:
        Filtered list of results
    """
    filtered = []
    trusted_count = 0
    blacklisted_count = 0

    for item in results:
        url = item.get(url_key, "")
        domain = extract_domain(url)
        
        # 1. Hard Blacklist check (always discard)
        is_blacklisted = False
        for blacklisted in SOCIAL_MEDIA_BLACKLIST:
            if domain == blacklisted or domain.endswith(f".{blacklisted}"):
                is_blacklisted = True
                break
        
        if is_blacklisted:
            blacklisted_count += 1
            continue
            
        # 2. Trusted check
        trusted = is_trusted_source(url) # This already re-checks domain, but it's safe

        if trusted:
            trusted_count += 1
            item["is_trusted"] = True
            filtered.append(item)
        elif not strict:
            item["is_trusted"] = False
            filtered.append(item)

    logger.info(
        f"Source filter: {trusted_count} trusted, {blacklisted_count} blacklisted, "
        f"{len(filtered)} total kept (mode={'strict' if strict else 'lenient'})"
    )
    return filtered
