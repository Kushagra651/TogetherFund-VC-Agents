import time, json, hashlib, os, urllib.request, urllib.parse
from dotenv import load_dotenv
from .logging_utils import log_event
load_dotenv()

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

def _cache_path(query: str) -> str:
    return os.path.join(CACHE_DIR, hashlib.md5(query.encode()).hexdigest() + ".json")

def _tavily_search(query: str, max_results: int) -> list[dict]:
    import urllib.request, json
    payload = json.dumps({"api_key": TAVILY_API_KEY, "query": query, "max_results": max_results}).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return [
        {"title": r.get("title", ""), "body": r.get("content", "")[:300], "href": r.get("url", "")}
        for r in data.get("results", [])[:max_results]
    ]

def search(query: str, max_results: int = 5) -> list[dict]:
    start = time.time()
    path = _cache_path(query)
    if os.path.exists(path):
        with open(path) as f:
            cached = json.load(f)
        if cached and "Search failed" not in cached[0].get("title", ""):
            log_event("tavily_search", query, len(cached), (time.time() - start) * 1000,
                       cache_hit=True)
            return cached
        os.remove(path)

    try:
        results = _tavily_search(query, max_results)
        if results:
            with open(path, "w") as f:
                json.dump(results, f)
            log_event("tavily_search", query, len(results), (time.time() - start) * 1000,
                       cache_hit=False)
            return results
    except Exception as e:
        log_event("tavily_search", query, 0, (time.time() - start) * 1000,
                   cache_hit=False, error=str(e))
        return [{"title": "Search failed", "body": str(e), "href": ""}]

    log_event("tavily_search", query, 0, (time.time() - start) * 1000, cache_hit=False)
    return [{"title": "No results", "body": "Search returned empty", "href": ""}]

def format_results(results: list[dict]) -> str:
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r.get('title','')}: {r.get('body','')[:200]} ({r.get('href','')})"
        for r in results
    )