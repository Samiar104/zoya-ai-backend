"""Emotion layer — understand how the user feels.

Detects one of 8 emotions from text (keyword lexicons in Hindi, Urdu,
Punjabi and English, Devanagari + Roman script) and, when voice metadata
is supplied, blends in a simple prosody heuristic (energy/pitch).
Returns (emotion, confidence 0..1).

Honest limits: this is a transparent keyword + heuristic detector, not a
trained ML model. It is tuned for short chat messages and is wrong
sometimes — confidence reflects that. Swap in a trained classifier
behind the same ``detect_emotion()`` function later (see README).
"""
import re

from app.core.logging import get_logger

log = get_logger("zoya.emotion")

EMOTIONS = ["happy", "sad", "stressed", "angry", "tired", "lonely", "excited", "neutral"]

# Keyword lexicons. Roman Urdu/Hindi and Devanagari are both common.
LEXICON: dict[str, list[str]] = {
    "happy": [
        "happy", "khush", "खुश", "great", "awesome", "amazing", "love", "maza", "मज़ा",
        "bohat acha", "बहुत अच्छा", "wonderful", "fantastic", "yay", "jeet", "जीत",
        "khushi", "खुशी", "blessed", "shukar", "शुक्र", "smile", "hansi", "हंसी",
    ],
    "sad": [
        "sad", "dukhi", "दुखी", "dukh", "दुख", "cry", "rona", "रोना", "tears", "aansoo",
        "आँसू", "upset", "heartbroken", "dil toot", "दिल टूट", "miss you", "yaad",
        "याद", "alone", "depressed", "pareshan", "परेशान", "udaas", "udas", "उदास", "غم",
        "gham", "dukhi hoon", "sad hoon", "rona aa raha",
    ],
    "stressed": [
        "stress", "stressed", "tension", "tension hai", "worried", "worry", "pareshan",
        "परेशान", "anxious", "anxiety", "pressure", "deadline", "exam", "exam hai",
        "kaam zyada", "thak gaya", "thak gayi", "overwhelmed", "ghabrahat", "घबराहट",
        "tension ho rahi", "fikar", "फ़िक्र", "dar lag", "डर लग",
    ],
    "angry": [
        "angry", "gussa", "गुस्सा", "ghussa", "naraz", "नाराज़", "furious", "mad",
        "irritated", "annoyed", "bakwas", "बकवास", "shut up", "hate", "nafrat",
        "नफ़रत", "gussa aa raha", "dimag kharab", "दिमाग खराब",
    ],
    "tired": [
        "tired", "thaka", "थका", "thaki", "थकी", "sleepy", "neend", "नींद", "exhausted",
        "thakan", "थकान", "need rest", "soona hai", "सोना है", "low energy", "weak",
        "kamzor", "कमज़ोर", "thak gaya hoon", "bohat thak",
    ],
    "lonely": [
        "lonely", "akela", "अकेला", "akeli", "अकेली", "alone", "koi nahi", "कोई नहीं",
        "miss you", "yaad aa rahi", "tanha", "तन्हा", "bore", "bore ho raha", "kuch nahi",
        "koi baat nahi karta", "ignore",
    ],
    "excited": [
        "excited", "exciting", "can't wait", "wow", "amazing", "shandar", "शानदार",
        "party", "celebrate", "maza aa", "मज़ा आ", "balle", "ਬੱਲੇ", "jeet gaye",
        "jeet gaya", "finally", "akhir", "आख़िर", "news", "khabar", "ख़बर",
    ],
}

# Words that flip an emotion's sign, e.g. "not sad" -> not sad.
NEGATORS = {"not", "nahi", "नहीं", "na", "naa", "never", "kabhi nahi"}


def detect_emotion(text: str, voice_metadata: dict | None = None) -> tuple[str, float]:
    """Return (emotion, confidence). Confidence is 0..1."""
    low = text.lower()
    words = set(re.findall(r"[\w']+", low, flags=re.UNICODE))
    scores: dict[str, float] = {e: 0.0 for e in EMOTIONS}

    for emotion, keywords in LEXICON.items():
        for kw in keywords:
            if kw.lower() in low:
                # Multi-word keywords count more; single words count 1.
                scores[emotion] += 2.0 if " " in kw else 1.0

    # Negation: "not sad" / "nahi dukhi" weakens the matched emotion.
    if words & NEGATORS:
        for emotion in scores:
            if scores[emotion] > 0:
                scores[emotion] *= 0.4

    best = max(scores, key=scores.get)
    best_score = scores[best]

    # Voice metadata blend (when the app sends prosody info).
    # energy 0..1 (loudness), pitch 0..1 (relative), speech_rate 0..1.
    if voice_metadata:
        energy = float(voice_metadata.get("energy", 0.5))
        pitch = float(voice_metadata.get("pitch", 0.5))
        rate = float(voice_metadata.get("speech_rate", 0.5))
        if energy > 0.75 and pitch > 0.65:
            scores["excited"] += 1.5
            scores["angry"] += 1.0
        elif energy < 0.3 and rate < 0.35:
            scores["tired"] += 1.5
            scores["sad"] += 1.0
        best = max(scores, key=scores.get)
        best_score = scores[best]

    if best_score <= 0:
        return "neutral", 0.5

    # Confidence: share of the winning score, capped and floored honestly.
    total = sum(scores.values())
    confidence = round(min(0.95, max(0.45, best_score / max(total, 1.0) + 0.15)), 2)
    return best, confidence


def describe_emotion(emotion: str, language: str = "hi") -> str:
    """One-line human label for an emotion id."""
    labels = {
        "happy": {"hi": "खुश", "ur": "خوش", "pa": "ਖੁਸ਼", "en": "happy"},
        "sad": {"hi": "उदास", "ur": "اداس", "pa": "ਉਦਾਸ", "en": "sad"},
        "stressed": {"hi": "तनाव में", "ur": "پریشان", "pa": "ਤਣਾਅ ਵਿੱਚ", "en": "stressed"},
        "angry": {"hi": "गुस्से में", "ur": "غصے میں", "pa": "ਗੁੱਸੇ ਵਿੱਚ", "en": "angry"},
        "tired": {"hi": "थका हुआ", "ur": "تھکا ہوا", "pa": "ਥੱਕਿਆ ਹੋਇਆ", "en": "tired"},
        "lonely": {"hi": "अकेला", "ur": "اکیلا", "pa": "ਇਕੱਲਾ", "en": "lonely"},
        "excited": {"hi": "उत्साहित", "ur": "پر جوش", "pa": "ਉਤਸ਼ਾਹਿਤ", "en": "excited"},
        "neutral": {"hi": "सामान्य", "ur": "عام", "pa": "ਆਮ", "en": "neutral"},
    }
    return labels.get(emotion, {}).get(language, emotion)
