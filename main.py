from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import uuid, os, re, asyncio

app = FastAPI()

# CORS (important for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP = "tmp"
os.makedirs(TMP, exist_ok=True)

# Voices
VOICE_MAP = {
    "male": "en-US-GuyNeural",
    "female": "en-US-AriaNeural"
}

# Clean SRT
def clean_srt(text):
    text = re.sub(r'\d+\n', '', text)
    text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> .*', '', text)
    return text.strip()

# Split text
def split_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]

# Generate voice
async def generate_voice(text, voice):
    file_path = os.path.join(TMP, f"{uuid.uuid4()}.mp3")

    communicate = edge_tts.Communicate(text, voice)

    with open(file_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])

    if os.path.getsize(file_path) < 2000:
        raise Exception("Audio broken")

    return file_path

# Retry system
async def safe_tts(text, voice):
    for i in range(3):
        try:
            return await generate_voice(text, voice)
        except Exception as e:
            print("Retry:", i, e)
            await asyncio.sleep(1)

    raise Exception("TTS failed after retries")

# TEXT → VOICE
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

    return FileResponse(
        files[0],
        media_type="audio/mpeg",
        filename="voice.mp3"
    )

# SRT → VOICE
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