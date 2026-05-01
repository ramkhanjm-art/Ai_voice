from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import uuid, os, re, asyncio

app = FastAPI()

# ✅ CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP = "tmp"
os.makedirs(TMP, exist_ok=True)

# 🎙️ Voices
VOICE_MAP = {
     "km": {"male": "km-KH-PisethNeural", "female": "km-KH-SreymomNeural"},
    "en": {"male": "en-US-AndrewNeural", "female": "en-US-AvaNeural"},
    "zh": {"male": "zh-CN-YunxiNeural", "female": "zh-CN-XiaoxiaoNeural"},
    "ja": {"male": "ja-JP-KeitaNeural", "female": "ja-JP-NanamiNeural"},
    "ko": {"male": "ko-KR-InJunNeural", "female": "ko-KR-SunHiNeural"},
    "th": {"male": "th-TH-NiwatNeural", "female": "th-TH-PremwadeeNeural"},
    "vi": {"male": "vi-VN-NamMinhNeural", "female": "vi-VN-HoaiMyNeural"},
    "lo": {"male": "lo-LA-ChanthavongNeural", "female": "lo-LA-KeotaNeural"},
    "my": {"male": "my-MM-ThihaNeural", "female": "my-MM-NilarNeural"},
    "tl": {"male": "fil-PH-AngeloNeural", "female": "fil-PH-BlessicaNeural"},
    "ms": {"male": "ms-MY-OsmanNeural", "female": "ms-MY-YasminNeural"},
    "id": {"male": "id-ID-ArdiNeural", "female": "id-ID-GadisNeural"},
    "br": {"male": "ms-MY-OsmanNeural", "female": "ms-MY-YasminNeural"},
    "bn": {"male": "bn-BD-PradeepNeural", "female": "bn-BD-NabanitaNeural"},
    "hi": {"male": "hi-IN-MadhurNeural", "female": "hi-IN-SwaraNeural"},
    "ar": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural"},
    "pt": {"male": "pt-PT-DuarteNeural", "female": "pt-PT-RaquelNeural"},
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"}
}
# 🧹 Clean SRT
def clean_srt(text):
    text = re.sub(r'\d+\n', '', text)
    text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> .*', '', text)
    return text.strip()

# ✂️ Split text
def split_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# 🔊 Generate voice (fixed)
async def generate_voice(text, voice):
    file_path = os.path.join(TMP, f"{uuid.uuid4()}.mp3")

    communicate = edge_tts.Communicate(text, voice)

    # 🔥 stream audio manually (fix 0:00 bug)
    with open(file_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])

    # validate
    if os.path.getsize(file_path) < 2000:
        raise Exception("Audio broken")

    return file_path
# 🔁 Retry system
async def safe_tts(text, voice):
    for i in range(3):
        try:
            return await generate_voice(text, voice)
        except Exception as e:
            print("Retry:", i, e)
            await asyncio.sleep(1)
    raise Exception("TTS failed after retries")

# 📝 TEXT → VOICE
@app.post("/text")
async def text_to_voice(
    text: str = Form(...),
    voice: str = Form("male")
):
    voice_id = VOICE_MAP.get(voice, VOICE_MAP["male"])

    chunks = split_text(text)
    files = []

    for c in chunks:
        f = await safe_tts(c, voice_id)
        files.append(f)

    # 👉 MVP: return first chunk
    return FileResponse(
        files[0],
        media_type="audio/mpeg",
        filename="voice.mp3"
    )

# 📂 SRT → VOICE
@app.post("/srt")
async def srt_to_voice(
    file: UploadFile = File(...),
    voice: str = Form("male")
):
    content = (await file.read()).decode("utf-8", errors="ignore")
    text = clean_srt(content)

    voice_id = VOICE_MAP.get(voice, VOICE_MAP["male"])
    chunks = split_text(text)

    files = []
    for c in chunks:
        f = await safe_tts(c, voice_id)
        files.append(f)

    return FileResponse(
        files[0],
        media_type="audio/mpeg",
        filename="voice.mp3"
    )