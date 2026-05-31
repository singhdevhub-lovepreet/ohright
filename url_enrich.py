"""
OhRight — URL Metadata Enrichment
Parses browser URLs to extract structured metadata from known sites.
Runs as a pre-processing step before events go to the LLM.
"""

from urllib.parse import urlparse, parse_qs, unquote
import re

KNOWN_DOMAINS = {
    "youtube.com": "_parse_youtube",
    "youtu.be": "_parse_youtube",
    "amazon.in": "_parse_amazon",
    "amazon.com": "_parse_amazon",
    "flipkart.com": "_parse_flipkart",
    "google.com": "_parse_google",
    "reddit.com": "_parse_reddit",
    "twitter.com": "_parse_twitter",
    "x.com": "_parse_twitter",
    "github.com": "_parse_github",
    "linkedin.com": "_parse_linkedin",
    "spotify.com": "_parse_spotify",
    "netflix.com": "_parse_netflix",
    "medium.com": "_parse_medium",
    "stackoverflow.com": "_parse_stackoverflow",
    "wikipedia.org": "_parse_wikipedia",
}


def enrich_url_metadata(url: str) -> dict:
    """
    Parse a browser URL and return structured metadata.
    
    Returns:
        {
            "domain": "youtube.com",
            "site_type": "video",
            "title_hint": "Music video on YouTube",
            "query": "search term if Google",
            "product": "product name if Amazon/Flipkart",
            "video_id": "abc123",
            "subreddit": "r/Python",
            "repo": "user/repo",
            "full_metadata": {...}
        }
    """
    if not url:
        return {"domain": "", "site_type": "unknown"}

    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.netloc.lower().replace("www.", "")
        path = parsed.path
        query = parse_qs(parsed.query)
    except Exception:
        return {"domain": url[:50], "site_type": "unknown"}

    result = {
        "domain": domain,
        "path": path,
        "query_params": {k: v[0] if len(v) == 1 else v for k, v in query.items()},
    }

    # Find matching parser
    for pattern, method_name in KNOWN_DOMAINS.items():
        if pattern in domain:
            parser = globals().get(method_name)
            if parser:
                extra = parser(parsed, path, query)
                result.update(extra)
            break

    return result


def _parse_youtube(parsed, path, query) -> dict:
    video_id = query.get("v", [None])[0]
    list_id = query.get("list", [None])[0]
    
    result = {"site_type": "video"}
    
    if "/watch" in path and video_id:
        result["video_id"] = video_id
        result["title_hint"] = "YouTube video"
        result["url_clean"] = f"https://youtube.com/watch?v={video_id}"
    elif "/playlist" in path and list_id:
        result["title_hint"] = "YouTube playlist"
        result["playlist_id"] = list_id
    elif "/results" in path:
        search_q = query.get("search_query", [None])[0]
        if search_q:
            result["title_hint"] = f"YouTube search: {unquote(search_q)[:60]}"
            result["search_query"] = unquote(search_q)
        else:
            result["title_hint"] = "YouTube search"
    elif "/@" in path:
        result["title_hint"] = f"YouTube channel: {path}"
        result["site_type"] = "social"
    
    return result


def _parse_amazon(parsed, path, query) -> dict:
    result = {"site_type": "shopping"}
    
    # Product page: /dp/PRODUCT_ID or /gp/product/ID
    dp_match = re.search(r'/dp/([A-Z0-9]+)', path)
    gp_match = re.search(r'/product/([A-Z0-9]+)', path)
    
    if dp_match:
        result["product_id"] = dp_match.group(1)
        result["title_hint"] = f"Amazon product: {dp_match.group(1)}"
    elif gp_match:
        result["product_id"] = gp_match.group(1)
        result["title_hint"] = f"Amazon product: {gp_match.group(1)}"
    elif "/s?" in path:
        kw = query.get("k", query.get("keywords", [None]))[0]
        if kw:
            result["title_hint"] = f"Amazon search: {unquote(kw)[:60]}"
            result["search_query"] = unquote(kw)
    elif "/cart" in path:
        result["title_hint"] = "Amazon shopping cart"
        result["purchase_intent"] = True
    elif "/wishlist" in path:
        result["title_hint"] = "Amazon wishlist"
        result["purchase_intent"] = True
    
    return result


def _parse_flipkart(parsed, path, query) -> dict:
    result = {"site_type": "shopping"}
    
    if "/p/" in path:
        pid_match = re.search(r'/p/([a-zA-Z0-9]+)', path)
        if pid_match:
            result["product_id"] = pid_match.group(1)
            result["title_hint"] = f"Flipkart product"
    elif "/search" in path:
        kw = query.get("q", [None])[0]
        if kw:
            result["title_hint"] = f"Flipkart search: {unquote(kw)[:60]}"
            result["search_query"] = unquote(kw)
    elif "/viewcart" in path:
        result["title_hint"] = "Flipkart cart"
        result["purchase_intent"] = True
    
    return result


def _parse_google(parsed, path, query) -> dict:
    result = {"site_type": "search"}
    
    if "/search" in path:
        q = query.get("q", [None])[0]
        if q:
            decoded = unquote(q)
            result["title_hint"] = f"Google search: {decoded[:60]}"
            result["search_query"] = decoded
        else:
            result["title_hint"] = "Google search"
    elif "/maps" in path:
        result["site_type"] = "maps"
        result["title_hint"] = "Google Maps"
    elif "/shopping" in path:
        result["site_type"] = "shopping"
        q = query.get("q", [None])[0]
        if q:
            result["title_hint"] = f"Google Shopping: {unquote(q)[:60]}"
    
    return result


def _parse_reddit(parsed, path, query) -> dict:
    result = {"site_type": "social", "title_hint": "Reddit"}
    
    sub_match = re.search(r'/r/([^/]+)', path)
    if sub_match:
        result["subreddit"] = sub_match.group(1)
        result["title_hint"] = f"Reddit r/{sub_match.group(1)}"
    
    if "/comments/" in path:
        result["title_hint"] = f"Reddit thread: {path.split('/')[-2] if len(path.split('/')) > 2 else ''}"
    
    return result


def _parse_twitter(parsed, path, query) -> dict:
    result = {"site_type": "social"}
    
    user_match = re.search(r'^/([^/]+)$', path)
    if user_match and user_match.group(1) not in ("home", "explore", "notifications", "messages", "i"):
        result["username"] = user_match.group(1)
        result["title_hint"] = f"X/Twitter: @{user_match.group(1)}"
    elif "/status/" in path:
        result["title_hint"] = "X/Twitter post"
    else:
        result["title_hint"] = "X/Twitter feed"
    
    return result


def _parse_github(parsed, path, query) -> dict:
    result = {"site_type": "code"}
    
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        result["repo"] = f"{parts[0]}/{parts[1]}"
        result["title_hint"] = f"GitHub: {parts[0]}/{parts[1]}"
    elif len(parts) == 1:
        result["title_hint"] = f"GitHub: {parts[0]}"
    else:
        result["title_hint"] = "GitHub"
    
    if "/issues/" in path:
        result["title_hint"] += " (issues)"
    elif "/pulls" in path:
        result["title_hint"] += " (pull requests)"
    elif "/blob/" in path:
        result["title_hint"] += " (code)"
    
    return result


def _parse_linkedin(parsed, path, query) -> dict:
    result = {"site_type": "professional"}
    
    if "/jobs/" in path:
        result["title_hint"] = "LinkedIn jobs"
        result["site_type"] = "job_search"
    elif "/company/" in path:
        company = path.split("/company/")[-1].split("/")[0] if "/company/" in path else ""
        result["title_hint"] = f"LinkedIn company: {company}"
    elif "/in/" in path:
        result["title_hint"] = "LinkedIn profile"
    elif "/feed/" in path:
        result["title_hint"] = "LinkedIn feed"
    else:
        result["title_hint"] = "LinkedIn"
    
    return result


def _parse_spotify(parsed, path, query) -> dict:
    result = {"site_type": "music"}
    
    if "/track/" in path:
        result["title_hint"] = "Spotify track"
    elif "/album/" in path:
        result["title_hint"] = "Spotify album"
    elif "/playlist/" in path:
        result["title_hint"] = "Spotify playlist"
    elif "/artist/" in path:
        result["title_hint"] = "Spotify artist"
    else:
        result["title_hint"] = "Spotify"
    
    return result


def _parse_netflix(parsed, path, query) -> dict:
    return {"site_type": "streaming", "title_hint": "Netflix"}


def _parse_medium(parsed, path, query) -> dict:
    return {"site_type": "article", "title_hint": "Medium article"}


def _parse_stackoverflow(parsed, path, query) -> dict:
    result = {"site_type": "technical", "title_hint": "StackOverflow"}
    
    if "/questions/" in path:
        qid = re.search(r'/questions/(\d+)', path)
        if qid:
            result["title_hint"] = f"StackOverflow Q#{qid.group(1)}"
    
    return result


def _parse_wikipedia(parsed, path, query) -> dict:
    result = {"site_type": "reference", "title_hint": "Wikipedia"}
    
    if "/wiki/" in path:
        topic = path.split("/wiki/")[-1]
        result["title_hint"] = f"Wikipedia: {unquote(topic)[:60]}"
    
    return result


def enrich_event(event: dict) -> dict:
    """
    Enrich a single raw event with URL metadata.
    The enriched data is added to the event dict in-place and returned.
    """
    url = event.get("browser_url", "")
    if not url:
        return event

    meta = enrich_url_metadata(url)
    
    # Add url_metadata as a top-level field for the LLM
    event["url_metadata"] = meta
    
    # If no window_name or it's generic, use the parsed title_hint
    if meta.get("title_hint") and (not event.get("window_name") or len(event.get("window_name", "")) < 5):
        event["window_name"] = meta["title_hint"]
    
    return event


if __name__ == "__main__":
    # Test
    test_urls = [
        "https://www.youtube.com/watch?v=EJtRvu6g1xA",
        "https://www.youtube.com/results?search_query=sad+song+punjabi",
        "https://www.amazon.in/dp/B08XYZ1234",
        "https://www.google.com/search?q=best+ultrawide+monitors+2024",
        "https://www.reddit.com/r/ultrawidemasterrace/comments/abc123/",
        "https://github.com/singhdevhub-lovepreet/ohright",
        "https://www.flipkart.com/search?q=laptop",
    ]
    
    for url in test_urls:
        enriched = enrich_url_metadata(url)
        print(f"\n{url}")
        print(f"  → {enriched.get('title_hint', 'unknown')}")
