"""
مولّد المحتوى - بيستخدم Gemini لتوليد بوستات عربية متنوعة،
وبيقدر يشوف ترندات حقيقية (عن طريق trends.py) ويبني عليها.
"""
import os
import random
import json
import urllib.parse
import urllib.request

import google.generativeai as genai

from trends import random_trending_topic

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("gemini-2.0-flash")

CONTENT_TYPES = [
    {
        "name": "مود شخصي",
        "prompt": (
            "اكتبيلي تغريدة عربية (لهجة شامية/عامية خفيفة) عن مود أو خاطرة يومية "
            "بسيطة وصادقة، إحساس عفوي مش مصطنع. من غير هاشتاقات كتير. أقل من 200 "
            "حرف. بس النص التغريدة، من غير أي مقدمات أو علامات تنصيص."
        ),
    },
    {
        "name": "اقتباس/حكمة",
        "prompt": (
            "اكتبيلي تغريدة عربية قصيرة فيها فكرة أو حكمة حياتية بأسلوب شخصي "
            "(فكرة أصلية مش منسوبة لحدا). أقل من 200 حرف. بس النص، من غير مقدمات."
        ),
    },
    {
        "name": "تفاعل عاطفي",
        "prompt": (
            "اكتبيلي تغريدة عربية بتفتح نقاش أو تفاعل عاطفي (سؤال، رأي، موقف بيهم "
            "بنات بجيلي). الهدف ردود وتفاعل مش مجرد قراءة. أقل من 200 حرف. بس النص."
        ),
    },
]


def _extract_text(response) -> str:
    return response.text.strip().strip('"').strip()


def generate_post(trend_context: str | None = None, auto_trend: bool = False) -> dict:
    """
    بتولد بوست واحد.
    - trend_context: موضوع محدد تعطيه انتي.
    - auto_trend=True: البوت بيجيب ترند حقيقي لحاله من الأخبار ويبني عليه.
    """
    if auto_trend and not trend_context:
        trend_context = random_trending_topic()

    if trend_context:
        content_type_name = "ترند/خبر"
        prompt = (
            f"في ترند/خبر حالياً بخصوص: {trend_context}\n\n"
            "اكتبيلي تغريدة عربية (لهجة شامية عفوية) فيها رأيي أو تعليقي الشخصي "
            "على هالموضوع، مش مجرد نقل خبر. أقل من 220 حرف. بس النص التغريدة، من "
            "غير مقدمات ولا علامات تنصيص."
        )
    else:
        chosen = random.choice(CONTENT_TYPES)
        content_type_name = chosen["name"]
        prompt = chosen["prompt"]

    response = _model.generate_content(prompt)
    text = _extract_text(response)
    if len(text) > 270:
        text = text[:265].rsplit(" ", 1)[0] + "…"

    return {"text": text, "type": content_type_name, "trend": trend_context}


def generate_posts(n: int = 3, trend_context: str | None = None, auto_trend: bool = False) -> list[dict]:
    """بتولد كم نسخة مختلفة (خيارات) دفعة وحدة."""
    if auto_trend and not trend_context:
        trend_context = random_trending_topic()  # نفس الترند لكل الخيارات، أسلوب مختلف
    return [generate_post(trend_context=trend_context) for _ in range(n)]


def generate_reply(original_post_text: str) -> str:
    prompt = (
        f'حدا كتب البوست هاد: "{original_post_text}"\n\n'
        "اكتبيلي رد عربي (لهجة عفوية) قصير وطبيعي، مش عام أو مكرر، مبني فعلاً على "
        "مضمون البوست. أقل من 150 حرف. بس نص الرد."
    )
    response = _model.generate_content(prompt)
    return _extract_text(response)


def suggest_image_keywords(post_text: str) -> str:
    """
    بتحول نص البوست لكلمات مفتاحية إنجليزية بسيطة (للبحث بمكتبة صور حرة الترخيص).
    """
    prompt = (
        f'هاد نص بوست: "{post_text}"\n\n'
        "اعطيني 2-3 كلمات مفتاحية بالإنجليزي بس (مفصولة بفاصلة) تصف مود/موضوع "
        "البوست بشكل بصري، مناسبة للبحث عن صورة (مثال: sunset, coffee, friendship). "
        "بس الكلمات، من غير شرح."
    )
    response = _model.generate_content(prompt)
    return _extract_text(response)


def find_stock_image_url(post_text: str) -> str | None:
    """
    بتدور على صورة حرة الترخيص (Pexels - ترخيص مجاني للاستخدام والنشر بدون
    الحاجة لنسب الحقوق) مرتبطة بموود/موضوع البوست. بترجع None إذا ما لقت شي
    أو المفتاح مش مظبوط.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None

    keywords = suggest_image_keywords(post_text)
    query = urllib.parse.quote(keywords.split(",")[0].strip())

    req = urllib.request.Request(
        f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=square",
        headers={"Authorization": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    photos = data.get("photos") or []
    if not photos:
        return None
    return random.choice(photos)["src"]["large"]


def find_stock_video_url(post_text: str) -> str | None:
    """
    بتدور على فيديو قصير حر الترخيص (Pexels Videos - نفس ترخيص الصور، مجاني
    ومسموح للنشر) مرتبط بموود/موضوع البوست. بترجع None إذا ما لقت شي أو
    المفتاح مش مظبوط.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None

    keywords = suggest_image_keywords(post_text)
    query = urllib.parse.quote(keywords.split(",")[0].strip())

    req = urllib.request.Request(
        f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=square",
        headers={"Authorization": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    videos = data.get("videos") or []
    if not videos:
        return None

    video = random.choice(videos)
    # ناخد أصغر ملف فيديو (كفاية لعرض جودة كويسة وأسرع تحميل)
    files = sorted(video.get("video_files", []), key=lambda f: f.get("width", 9999))
    return files[0]["link"] if files else None


if __name__ == "__main__":
    posts = generate_posts(3, auto_trend=True)
    print(json.dumps(posts, ensure_ascii=False, indent=2))
