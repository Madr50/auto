"""
جلب ترندات/أخبار حقيقية مجاناً عن طريق Google News RSS (بدون مفتاح API).
"""
import urllib.request
import xml.etree.ElementTree as ET
import random

RSS_URL = "https://news.google.com/rss?hl=ar&gl=JO&ceid=JO:ar"


def fetch_trending_topics(limit: int = 8) -> list[str]:
    """بترجع لستة عناوين أخبار حالية بالعربي (ترندات فعلية، مش مولدة)."""
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    titles = [item.findtext("title") for item in root.findall(".//item")]
    titles = [t for t in titles if t]
    return titles[:limit]


def random_trending_topic() -> str | None:
    """بترجع عنوان ترند واحد عشوائي، أو None إذا فشل الجلب."""
    try:
        topics = fetch_trending_topics()
        return random.choice(topics) if topics else None
    except Exception:
        return None


if __name__ == "__main__":
    for t in fetch_trending_topics():
        print("-", t)
