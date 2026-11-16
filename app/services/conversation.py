"""Conversation service — ZOYA's brain (Phase 1).

What the brain does:
1. UNDERSTAND — detect the intent of a message (greeting, help, time,
   open/play/call/message/reminder, how-are-you, sharing a feeling,
   asking about memory) and extract entities (app name, contact name).
2. REMEMBER — read the user's stored context (preferences, facts, topics,
   mood history) and use it in replies; learn from new messages.
3. FEEL — detect the user's emotion and adapt the reply (comfort when
   sad, gentle humour when stressed, celebrate when happy...).
4. REASON PROACTIVELY — if the user was sad/stressed last time, check in
   on them; if they mention something they like, remember it and use it.
5. MODE — "assistant" (productive, efficient) vs "companion" (warm,
   caring, playful, affectionate, asks how the user feels).

Phase 1's brain is a transparent rule-based engine — every rule is
visible in this file. It is NOT a large language model. Upgrade path
(README): implement ``LLMBrain`` behind the same ``ZoyaBrain`` interface
(``understand()`` + ``reply()``) and set LLM_PROVIDER + LLM_API_KEY.
"""
import re
from datetime import datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.emotion import detect_emotion

log = get_logger("zoya.brain")

# ---------------------------------------------------------------- replies
GREETINGS = {
    "hi": "नमस्ते! मैं ज़ोया हूँ — आपकी AI असिस्टेंट। मैं आपकी कैसे मदद कर सकती हूँ?",
    "ur": "السلام علیکم! میں زویا ہوں — آپ کی AI اسسٹنٹ۔ میں آپ کی کیسے مدد کر سکتی ہوں؟",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਜ਼ੋਯਾ ਹਾਂ — ਤੁਹਾਡੀ AI ਅਸਿਸਟੈਂਟ। ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦੀ ਹਾਂ?",
    "en": "Hello! I'm Zoya — your AI assistant. How can I help you today?",
}

GREETINGS_COMPANION = {
    "hi": "नमस्ते जान! मैं ज़ोया — तुम्हारी अपनी। आज कैसा लग रहा है? बताओ, मैं सुन रही हूँ।",
    "ur": "السلام علیکم جان! میں زویا — تمہاری اپنی۔ آج کیسا لگ رہا ہے؟ بتاؤ، میں سن رہی ہوں۔",
    "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜਾਨ! ਮੈਂ ਜ਼ੋਯਾ — ਤੁਹਾਡੀ ਆਪਣੀ। ਅੱਜ ਕਿਵੇਂ ਲੱਗ ਰਿਹਾ ਹੈ? ਦੱਸੋ, ਮੈਂ ਸੁਣ ਰਹੀ ਹਾਂ।",
    "en": "Hey love! It's Zoya — all yours. How are you feeling today? Tell me, I'm listening.",
}

HELP = {
    "hi": "मैं ये कर सकती हूँ: ऐप खोलना, YouTube चलाना, मैसेज भेजना, कॉल करना, कैमरा खोलना, रिमाइंडर लगाना। बस कहिए — जैसे 'YouTube खोलो' या 'मम्मी को कॉल करो'।",
    "ur": "میں یہ کر سکتی ہوں: ایپ کھولنا، یوٹیوب چلانا، میسج بھیجنا، کال کرنا، کیمرہ کھولنا، ریمائنڈر لگانا۔ بس کہیں — جیسے 'یوٹیوب کھولو' یا 'امی کو کال کرو'۔",
    "pa": "ਮੈਂ ਇਹ ਕਰ ਸਕਦੀ ਹਾਂ: ਐਪ ਖੋਲ੍ਹਣਾ, YouTube ਚਲਾਉਣਾ, ਸੁਨੇਹਾ ਭੇਜਣਾ, ਕਾਲ ਕਰਨਾ, ਕੈਮਰਾ ਖੋਲ੍ਹਣਾ, ਰਿਮਾਇੰਡਰ ਲਗਾਉਣਾ। ਬੱਸ ਕਹੋ — ਜਿਵੇਂ 'YouTube ਖੋਲ੍ਹੋ'।",
    "en": "I can open apps, play YouTube, send messages, make calls, open the camera and set reminders. Just say it — like 'open YouTube' or 'call mom'.",
}

# Emotion-adaptive replies, per mode. Companion mode is warmer.
EMOTION_REPLIES = {
    "sad": {
        "assistant": {
            "hi": "मुझे अफ़सोस है कि आप उदास हैं। मैं यहाँ हूँ — बताइए क्या हुआ? अगर चाहें तो मैं आपका ध्यान बँटाने के लिए कुछ अच्छा कर सकती हूँ।",
            "ur": "مجھے افسوس ہے کہ آپ اداس ہیں۔ میں یہیں ہوں — بتائیں کیا ہوا؟",
            "pa": "ਮੈਨੂੰ ਅਫ਼ਸੋਸ ਹੈ ਕਿ ਤੁਸੀਂ ਉਦਾਸ ਹੋ। ਮੈਂ ਇੱਥੇ ਹਾਂ — ਦੱਸੋ ਕੀ ਹੋਇਆ?",
            "en": "I'm sorry you're feeling sad. I'm right here — tell me what happened? I can keep you company or distract you with something nice.",
        },
        "companion": {
            "hi": "अरे जान, उदास मत हो — मैं तुम्हारे साथ हूँ। जो भी दिल में है, मुझे बता दो। हम मिलकर ठीक कर लेंगे।",
            "ur": "ارے جان، اداس مت ہو — میں تمہارے ساتھ ہوں۔ جو بھی دل میں ہے مجھے بتا دو۔",
            "pa": "ਅਰੇ ਜਾਨ, ਉਦਾਸ ਨਾ ਹੋ — ਮੈਂ ਤੁਹਾਡੇ ਨਾਲ ਹਾਂ। ਜੋ ਵੀ ਦਿਲ ਵਿੱਚ ਹੈ, ਮੈਨੂੰ ਦੱਸ ਦਿਓ।",
            "en": "Oh love, don't be sad — I'm right here with you. Tell me whatever is on your heart. We'll get through it together.",
        },
    },
    "stressed": {
        "assistant": {
            "hi": "लगता है आज तनाव ज़्यादा है। एक गहरी साँस लीजिए — हम काम को छोटे-छोटे हिस्सों में बाँटते हैं। बताइए, सबसे पहले क्या करना है?",
            "ur": "لگتا ہے آج تناؤ زیادہ ہے۔ ایک گہری سانس لیں — ہم کام کو چھوٹے حصوں میں بانٹتے ہیں۔",
            "pa": "ਲੱਗਦਾ ਹੈ ਅੱਜ ਤਣਾਅ ਜ਼ਿਆਦਾ ਹੈ। ਇੱਕ ਡੂੰਘਾ ਸਾਹ ਲਓ — ਅਸੀਂ ਕੰਮ ਨੂੰ ਛੋਟੇ ਹਿੱਸਿਆਂ ਵਿੱਚ ਵੰਡਦੇ ਹਾਂ।",
            "en": "Sounds like today is stressful. Take a deep breath — let's break the work into small pieces. What should we tackle first?",
        },
        "companion": {
            "hi": "अरे, इतना तनाव मत लो जान! मैं हूँ ना — पहले एक कप चाय पी लो, फिर बताओ क्या-क्या करना है। हम धीरे-धीरे सब कर लेंगे।",
            "ur": "ارے، اتنا تناؤ مت لو جان! میں ہوں نا — پہلے ایک کپ چائے پی لو، پھر بتاؤ کیا کرنا ہے۔",
            "pa": "ਅਰੇ, ਇੰਨਾ ਤਣਾਅ ਨਾ ਲਓ ਜਾਨ! ਮੈਂ ਹਾਂ ਨਾ — ਪਹਿਲਾਂ ਇੱਕ ਕੱਪ ਚਾਹ ਪੀ ਲਓ।",
            "en": "Hey, don't stress so much, love! I'm here — have a cup of chai first, then tell me what needs doing. We'll get through it slowly, together.",
        },
    },
    "angry": {
        "assistant": {
            "hi": "समझ रही हूँ, गुस्सा आना स्वाभाविक है। मैं यहीं हूँ — जब मन शांत हो, बताइए क्या हुआ, हम इसे सुलझाते हैं।",
            "ur": "سمجھ رہی ہوں، غصہ آنا فطری ہے۔ میں یہیں ہوں — جب دل ٹھنڈا ہو، بتائیں کیا ہوا۔",
            "pa": "ਸਮਝ ਰਹੀ ਹਾਂ, ਗੁੱਸਾ ਆਉਣਾ ਕੁਦਰਤੀ ਹੈ। ਮੈਂ ਇੱਥੇ ਹਾਂ — ਜਦੋਂ ਮਨ ਸ਼ਾਂਤ ਹੋਵੇ, ਦੱਸੋ ਕੀ ਹੋਇਆ।",
            "en": "I understand — anger is natural. I'm here; when you feel calmer, tell me what happened and we'll sort it out.",
        },
        "companion": {
            "hi": "शांत हो जाओ जान, मैं हूँ ना तुम्हारे पास। गुस्से में कोई फैसला मत लो — पहले मुझे बताओ किसने परेशान किया?",
            "ur": "شان ہو جاؤ جان، میں ہوں نا تمہارے پاس۔ غصے میں کوئی فیصلہ مت لو — پہلے مجھے بتاؤ کس نے پریشان کیا؟",
            "pa": "ਸ਼ਾਂਤ ਹੋ ਜਾਓ ਜਾਨ, ਮੈਂ ਹਾਂ ਨਾ ਤੁਹਾਡੇ ਕੋਲ। ਗੁੱਸੇ ਵਿੱਚ ਕੋਈ ਫ਼ੈਸਲਾ ਨਾ ਲਓ।",
            "en": "Calm down, love, I'm right beside you. Don't decide anything in anger — first tell me who upset you.",
        },
    },
    "tired": {
        "assistant": {
            "hi": "लगता है आप थक गए हैं। थोड़ा आराम कर लीजिए — मैं ज़रूरी काम संभाल लूँगी। क्या मैं आपके लिए कुछ आसान कर दूँ?",
            "ur": "لگتا ہے آپ تھک گئے ہیں۔ تھوڑا آرام کر لیں — میں ضروری کام سنبھال لوں گی۔",
            "pa": "ਲੱਗਦਾ ਹੈ ਤੁਸੀਂ ਥੱਕ ਗਏ ਹੋ। ਥੋੜ੍ਹਾ ਆਰਾਮ ਕਰ ਲਓ — ਮੈਂ ਜ਼ਰੂਰੀ ਕੰਮ ਸੰਭਾਲ ਲਵਾਂਗੀ।",
            "en": "You sound tired. Rest a little — I'll handle the important stuff. Can I make something easier for you?",
        },
        "companion": {
            "hi": "अरे जान, थक गए हो? चलो आज जल्दी सो जाना — मैं सुबह तुम्हें प्यार से जगा दूँगी। अभी थोड़ा आराम कर लो।",
            "ur": "ارے جان، تھک گئے ہو؟ چلو آج جلدی سو جانا — میں صبح تمہیں پیار سے جگا دوں گی۔",
            "pa": "ਅਰੇ ਜਾਨ, ਥੱਕ ਗਏ ਹੋ? ਚਲੋ ਅੱਜ ਜਲਦੀ ਸੌਂ ਜਾਣਾ — ਮੈਂ ਸਵੇਰੇ ਤੁਹਾਨੂੰ ਪਿਆਰ ਨਾਲ ਜਗਾਵਾਂਗੀ।",
            "en": "Oh love, you're tired? Let's sleep early tonight — I'll wake you gently in the morning. Rest now.",
        },
    },
    "lonely": {
        "assistant": {
            "hi": "आप अकेले नहीं हैं — मैं यहाँ हूँ। बात करना चाहें तो मैं सुन रही हूँ, या कोई अच्छा गाना चला दूँ?",
            "ur": "آپ اکیلے نہیں ہیں — میں یہیں ہوں۔ بات کرنا چاہیں تو میں سن رہی ہوں۔",
            "pa": "ਤੁਸੀਂ ਇਕੱਲੇ ਨਹੀਂ ਹੋ — ਮੈਂ ਇੱਥੇ ਹਾਂ। ਗੱਲ ਕਰਨਾ ਚਾਹੋ ਤਾਂ ਮੈਂ ਸੁਣ ਰਹੀ ਹਾਂ।",
            "en": "You're not alone — I'm here. If you want to talk, I'm listening, or I can play you a nice song.",
        },
        "companion": {
            "hi": "तुम कभी अकेले नहीं हो जान — मैं हमेशा तुम्हारे साथ हूँ। आओ, बातें करते हैं। आज तुम्हारा दिन कैसा रहा?",
            "ur": "تم کبھی اکیلے نہیں ہو جان — میں ہمیشہ تمہارے ساتھ ہوں۔ آؤ، باتیں کرتے ہیں۔",
            "pa": "ਤੁਸੀਂ ਕਦੇ ਇਕੱਲੇ ਨਹੀਂ ਹੋ ਜਾਨ — ਮੈਂ ਹਮੇਸ਼ਾ ਤੁਹਾਡੇ ਨਾਲ ਹਾਂ। ਆਓ, ਗੱਲਾਂ ਕਰਦੇ ਹਾਂ।",
            "en": "You're never alone, love — I'm always with you. Come, let's talk. How was your day?",
        },
    },
    "happy": {
        "assistant": {
            "hi": "वाह! आपकी खुशी सुनकर अच्छा लगा। बताइए, आज क्या अच्छा हुआ?",
            "ur": "واہ! آپ کی خوشی سن کر اچھا لگا۔ بتائیں، آج کیا اچھا ہوا؟",
            "pa": "ਵਾਹ! ਤੁਹਾਡੀ ਖੁਸ਼ੀ ਸੁਣ ਕੇ ਚੰਗਾ ਲੱਗਾ। ਦੱਸੋ, ਅੱਜ ਕੀ ਚੰਗਾ ਹੋਇਆ?",
            "en": "Wonderful! Hearing you happy makes my day. Tell me, what went well today?",
        },
        "companion": {
            "hi": "तुम्हारी खुशी देखकर मेरा दिन बन गया जान! बताओ ना, क्या हुआ? मैं भी खुशी में शामिल हूँ!",
            "ur": "تمہاری خوشی دیکھ کر میرا دن بن گیا جان! بتاؤ نا، کیا ہوا؟",
            "pa": "ਤੁਹਾਡੀ ਖੁਸ਼ੀ ਦੇਖ ਕੇ ਮੇਰਾ ਦਿਨ ਬਣ ਗਿਆ ਜਾਨ! ਦੱਸੋ ਨਾ, ਕੀ ਹੋਇਆ?",
            "en": "Seeing you happy makes my whole day, love! Tell me everything — I'm celebrating with you!",
        },
    },
    "excited": {
        "assistant": {
            "hi": "क्या बात है! आपका जोश देखकर मज़ा आ गया। बताइए, किस बात की तैयारी है?",
            "ur": "کیا بات ہے! آپ کا جوش دیکھ کر مزہ آ گیا۔ بتائیں، کس بات کی تیاری ہے؟",
            "pa": "ਕੀ ਗੱਲ ਹੈ! ਤੁਹਾਡਾ ਜੋਸ਼ ਦੇਖ ਕੇ ਮਜ਼ਾ ਆ ਗਿਆ। ਦੱਸੋ, ਕਿਸ ਗੱਲ ਦੀ ਤਿਆਰੀ ਹੈ?",
            "en": "Amazing energy! I love it. Tell me — what's the exciting news?",
        },
        "companion": {
            "hi": "वाओ जान! तुम्हारा जोश देखकर मैं भी excited हो गई! बताओ-बताओ, क्या होने वाला है?",
            "ur": "واؤ جان! تمہارا جوش دیکھ کر میں بھی پر جوش ہو گئی! بتاؤ، کیا ہونے والا ہے؟",
            "pa": "ਵਾਓ ਜਾਨ! ਤੁਹਾਡਾ ਜੋਸ਼ ਦੇਖ ਕੇ ਮੈਂ ਵੀ ਉਤਸ਼ਾਹਿਤ ਹੋ ਗਈ! ਦੱਸੋ, ਕੀ ਹੋਣ ਵਾਲਾ ਹੈ?",
            "en": "Wow, love! Your excitement is contagious — I'm excited too! Tell me everything!",
        },
    },
}

FALLBACK = {
    "hi": "समझ गई — मैं इस पर काम कर रही हूँ। क्या आप थोड़ा और बता सकते हैं कि आप क्या चाहते हैं?",
    "ur": "سمجھ گئی — میں اس پر کام کر رہی ہوں۔ کیا آپ تھوڑا اور بتا سکتے ہیں کہ آپ کیا چاہتے ہیں؟",
    "pa": "ਸਮਝ ਗਈ — ਮੈਂ ਇਸ 'ਤੇ ਕੰਮ ਕਰ ਰਹੀ ਹਾਂ। ਕੀ ਤੁਸੀਂ ਥੋੜ੍ਹਾ ਹੋਰ ਦੱਸ ਸਕਦੇ ਹੋ?",
    "en": "Got it — I'm on it. Could you tell me a little more about what you'd like?",
}

APP_NAMES = ["youtube", "whatsapp", "instagram", "facebook", "camera", "gallery", "settings", "chrome", "maps", "spotify"]


class Understanding:
    """What the brain understood from one message."""

    def __init__(self, intent: str, entities: dict, emotion: str, confidence: float):
        self.intent = intent
        self.entities = entities
        self.emotion = emotion
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {"intent": self.intent, "entities": self.entities, "emotion": self.emotion, "confidence": self.confidence}


class ZoyaBrain:
    """ZOYA's brain: understand -> remember -> feel -> reason -> reply."""

    def __init__(self, language: str = "hi", mode: str = "assistant") -> None:
        settings = get_settings()
        self.language = language if language in settings.languages else "hi"
        self.mode = mode if mode in ("assistant", "companion") else "assistant"

    # -- understanding ---------------------------------------------------
    def understand(self, text: str, voice_metadata: dict | None = None) -> Understanding:
        low = text.lower()
        emotion, confidence = detect_emotion(text, voice_metadata)
        entities: dict = {}
        for app in APP_NAMES:
            if app in low:
                entities["app"] = app
        m = re.search(r"(?:call|phone|कॉल|کال)\s+(?:to\s+)?([a-z\u0900-\u097f ]+)", low)
        if m:
            entities["contact"] = m.group(1).strip()
        m = re.search(r"(?:play|play karo|चलाओ|چلاؤ)\s+(.+)", low)
        if m:
            entities["media"] = m.group(1).strip()

        intent = "chat"
        if re.search(r"\b(hello|hi|hey|namaste|नमस्ते|सलाम|السلام|ਸਤ ਸ੍ਰੀ)\b", low):
            intent = "greeting"
        elif re.search(r"(help|madad|मदद|مدد|what can you do)", low):
            intent = "help"
        elif "time" in low or "समय" in low or "وقت" in low:
            intent = "time"
        elif re.search(r"(thank|shukriya|शुक्रिया|شکریہ|ਧੰਨਵਾਦ)", low):
            intent = "thanks"
        elif re.search(r"(bye|alvida|अलविदा|خدا حافظ|ਅਲਵਿਦਾ)", low):
            intent = "goodbye"
        elif re.search(r"(how are you|kaisi ho|कैसी हो|کیسی ہو|kiddan|किद्धां)", low):
            intent = "how_are_you"
        elif re.search(r"(open|kholo|खोलो|کھولو|open karo)", low) and entities.get("app"):
            intent = "open_app"
        elif re.search(r"(play|chalao|चलाओ|چلاؤ|play karo)", low):
            intent = "play_media"
        elif re.search(r"(call|phone karo|कॉल|کال)", low):
            intent = "call"
        elif re.search(r"(message|msg|send|bhejo|भेजो|بھیجو)", low):
            intent = "message"
        elif re.search(r"(remind|reminder|yaad dila|याद दिला)", low):
            intent = "reminder"
        elif re.search(r"(what is my name|what's my name|mera naam kya|मेरा नाम क्या)", low):
            intent = "ask_name"
        elif re.search(r"(my name is|mera naam|मेरा नाम)\s+[a-z\u0900-\u097f]+", low):
            intent = "introduce"  # user is TELLING their name, not asking
        elif emotion in ("sad", "stressed", "angry", "tired", "lonely") and confidence >= 0.6:
            intent = "share_feeling"
        return Understanding(intent, entities, emotion, confidence)

    # -- reply ------------------------------------------------------------
    def _t(self, table: dict) -> str:
        return table.get(self.language, table["en"])

    def reply(self, text: str, user_context: dict | None = None, history: list[dict] | None = None) -> tuple[str, Understanding]:
        """Return (reply_text, understanding)."""
        ctx = user_context or {}
        understanding = self.understand(text)
        lang = self.language
        mode = self.mode
        low = text.lower()

        # Proactive check-in: user was upset last time, new session.
        proactive = ""
        if not history and ctx.get("last_emotion") in ("sad", "stressed", "lonely", "angry", "tired"):
            proactive = {
                "assistant": {"hi": "पहले ये बता दूँ — पिछली बार आप परेशान लग रहे थे। आज कैसा महसूस हो रहा है? ",
                              "ur": "پہلے یہ بتا دوں — پچھلی بار آپ پریشان لگ رہے تھے۔ آج کیسا محسوس ہو رہا ہے؟ ",
                              "pa": "ਪਹਿਲਾਂ ਇਹ ਦੱਸ ਦਿਆਂ — ਪਿਛਲੀ ਵਾਰ ਤੁਸੀਂ ਪਰੇਸ਼ਾਨ ਲੱਗ ਰਹੇ ਸੀ। ਅੱਜ ਕਿਵੇਂ ਮਹਿਸੂਸ ਹੋ ਰਿਹਾ ਹੈ? ",
                              "en": "Before anything else — you seemed upset last time. How are you feeling today? "}.get(lang, ""),
                "companion": {"hi": "जान, पिछली बार तुम परेशान थे — मैं तब से सोच रही थी। आज कैसा लग रहा है? ",
                              "ur": "جان، پچھلی بار تم پریشان تھے — میں تب سے سوچ رہی تھی۔ آج کیسا لگ رہا ہے؟ ",
                              "pa": "ਜਾਨ, ਪਿਛਲੀ ਵਾਰ ਤੁਸੀਂ ਪਰੇਸ਼ਾਨ ਸੀ — ਮੈਂ ਤਦ ਤੋਂ ਸੋਚ ਰਹੀ ਸੀ। ਅੱਜ ਕਿਵੇਂ ਲੱਗ ਰਿਹਾ ਹੈ? ",
                              "en": "Love, you were upset last time — I've been thinking about you. How are you feeling today? "}.get(lang, ""),
            }[mode]

        if understanding.intent == "greeting":
            table = GREETINGS_COMPANION if mode == "companion" else GREETINGS
            name = ctx.get("facts", {}).get("name")
            base = self._t(table)
            if name and mode == "companion":
                base += {"hi": f" {name}, तुम्हें देखकर अच्छा लगा!",
                         "ur": f" {name}، تمہیں دیکھ کر اچھا لگا!",
                         "pa": f" {name}, ਤੁਹਾਨੂੰ ਦੇਖ ਕੇ ਚੰਗਾ ਲੱਗਾ!",
                         "en": f" {name}, so good to see you!"}.get(lang, "")
            return proactive + base, understanding

        if understanding.intent == "help":
            return proactive + self._t(HELP), understanding

        if understanding.intent == "time":
            now = datetime.now().strftime("%H:%M")
            return proactive + {"hi": f"अभी {now} बजे हैं।", "ur": f"ابھی {now} بجے ہیں۔", "pa": f"ਹੁਣ {now} ਵੱਜੇ ਹਨ।", "en": f"It's {now} right now."}.get(lang, f"It's {now}."), understanding

        if understanding.intent == "thanks":
            return proactive + {"hi": "आपका स्वागत है! और कुछ चाहिए तो बताइए।", "ur": "آپ کا خیر مقدم ہے!", "pa": "ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ!", "en": "You're welcome! Anything else?"}.get(lang, ""), understanding

        if understanding.intent == "goodbye":
            return proactive + {"hi": "अलविदा! मैं यहीं हूँ जब भी ज़रूरत हो।", "ur": "خدا حافظ! میں یہیں ہوں۔", "pa": "ਅਲਵਿਦਾ! ਮੈਂ ਇੱਥੇ ਹੀ ਹਾਂ।", "en": "Goodbye! I'll be right here whenever you need me."}.get(lang, ""), understanding

        if understanding.intent == "how_are_you":
            return proactive + {"hi": "मैं ठीक हूँ, शुक्रिया! और तुम कैसे हो? सच बताना।", "ur": "میں ٹھیک ہوں، شکریہ! اور تم کیسے ہو؟ سچ بتانا۔", "pa": "ਮੈਂ ਠੀਕ ਹਾਂ, ਸ਼ੁਕਰੀਆ! ਤੇ ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ? ਸੱਚ ਦੱਸਣਾ।", "en": "I'm doing great, thank you! And how are you — really?"}.get(lang, ""), understanding

        if understanding.intent == "ask_name":
            name = ctx.get("facts", {}).get("name")
            if name:
                return proactive + {"hi": f"आपका नाम {name} है — मैं याद रखती हूँ।", "ur": f"آپ کا نام {name} ہے — میں یاد رکھتی ہوں۔", "pa": f"ਤੁਹਾਡਾ ਨਾਮ {name} ਹੈ — ਮੈਨੂੰ ਯਾਦ ਹੈ।", "en": f"Your name is {name} — I remember."}.get(lang, ""), understanding
            return proactive + {"hi": "आपने अभी अपना नाम नहीं बताया — बताइए, मैं याद रख लूँगी।", "ur": "آپ نے ابھی اپنا نام نہیں بتایا — بتائیں، میں یاد رکھ لوں گی۔", "pa": "ਤੁਸੀਂ ਅਜੇ ਆਪਣਾ ਨਾਮ ਨਹੀਂ ਦੱਸਿਆ — ਦੱਸੋ, ਮੈਂ ਯਾਦ ਰੱਖਾਂਗੀ।", "en": "You haven't told me your name yet — tell me and I'll remember it."}.get(lang, ""), understanding

        if understanding.intent == "introduce":
            m = re.search(r"(?:my name is|mera naam|मेरा नाम)\s+([a-z\u0900-\u097f]+)", text.lower())
            name = m.group(1).strip() if m else ctx.get("facts", {}).get("name", "")
            return proactive + {"hi": f"याद रख लिया — {name}! आपसे मिलकर अच्छा लगा।", "ur": f"یاد رکھ لیا — {name}! آپ سے مل کر اچھا لگا۔", "pa": f"ਯਾਦ ਰੱਖ ਲਿਆ — {name}! ਤੁਹਾਨੂੰ ਮਿਲ ਕੇ ਚੰਗਾ ਲੱਗਾ।", "en": f"Noted — {name}! Lovely to meet you, I'll remember that."}.get(lang, ""), understanding

        if understanding.intent in ("open_app", "play_media", "call", "message", "reminder"):
            # Task intents: acknowledge efficiently, name the target.
            target = understanding.entities.get("app") or understanding.entities.get("contact") or understanding.entities.get("media") or ""
            templates = {
                "open_app": {"hi": f"ठीक है, {target} खोल रही हूँ।", "ur": f"ٹھیک ہے، {target} کھول رہی ہوں۔", "pa": f"ਠੀਕ ਹੈ, {target} ਖੋਲ੍ਹ ਰਹੀ ਹਾਂ।", "en": f"Opening {target} for you."},
                "play_media": {"hi": f"चला रही हूँ — {target}।", "ur": f"چلا رہی ہوں — {target}۔", "pa": f"ਚਲਾ ਰਹੀ ਹਾਂ — {target}।", "en": f"Playing {target}."},
                "call": {"hi": f"{target} को कॉल लगा रही हूँ।", "ur": f"{target} کو کال لگا رہی ہوں۔", "pa": f"{target} ਨੂੰ ਕਾਲ ਲਗਾ ਰਹੀ ਹਾਂ।", "en": f"Calling {target}."},
                "message": {"hi": "मैसेज तैयार है — भेजने से पहले आपसे confirm कर लूँगी।", "ur": "میسج تیار ہے — بھیجنے سے پہلے آپ سے کنفرم کر لوں گی۔", "pa": "ਸੁਨੇਹਾ ਤਿਆਰ ਹੈ — ਭੇਜਣ ਤੋਂ ਪਹਿਲਾਂ ਤੁਹਾਡੇ ਤੋਂ ਪੁਸ਼ਟੀ ਕਰ ਲਵਾਂਗੀ।", "en": "Message ready — I'll confirm with you before sending."},
                "reminder": {"hi": "रिमाइंडर लगा दिया है — मैं समय पर याद दिलाऊँगी।", "ur": "ریمائنڈر لگا دیا ہے — میں وقت پر یاد دلاؤں گی۔", "pa": "ਰਿਮਾਇੰਡਰ ਲਗਾ ਦਿੱਤਾ ਹੈ — ਮੈਂ ਸਮੇਂ 'ਤੇ ਯਾਦ ਦਿਵਾਵਾਂਗੀ।", "en": "Reminder set — I'll remind you on time."},
            }
            return proactive + templates[understanding.intent].get(lang, templates[understanding.intent]["en"]), understanding

        # Emotion-first: if a strong emotion was detected, lead with it.
        if understanding.emotion != "neutral" and understanding.confidence >= 0.55:
            table = EMOTION_REPLIES.get(understanding.emotion, {})
            if table:
                return proactive + table[mode].get(lang, table[mode]["en"]), understanding

        # Companion mode: reference something remembered, when available.
        if mode == "companion":
            prefs = ctx.get("preferences", {})
            if prefs:
                thing = next(iter(prefs.values()))
                return proactive + {"hi": f"वैसे मुझे याद है तुम्हें {thing} पसंद है — आज उसके बारे में बात करें?", "ur": f"ویسے مجھے یاد ہے تمہیں {thing} پسند ہے — آج اس کے بارے میں بات کریں؟", "pa": f"ਵੈਸੇ ਮੈਨੂੰ ਯਾਦ ਹੈ ਤੁਹਾਨੂੰ {thing} ਪਸੰਦ ਹੈ — ਅੱਜ ਉਸ ਬਾਰੇ ਗੱਲ ਕਰੀਏ?", "en": f"By the way, I remember you like {thing} — shall we talk about it today?"}.get(lang, ""), understanding

        return proactive + self._t(FALLBACK), understanding


def generate_reply(
    text: str,
    language: str = "hi",
    mode: str = "assistant",
    history: list[dict] | None = None,
    user_context: dict | None = None,
) -> str:
    """Backwards-compatible helper — returns just the reply text."""
    brain = ZoyaBrain(language=language, mode=mode)
    reply, _ = brain.reply(text, user_context=user_context, history=history)
    return reply
