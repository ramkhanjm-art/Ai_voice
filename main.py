from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import edge_tts, uuid, os, re

app = FastAPI()

TMP = "tmp"
os.makedirs(TMP, exist_ok=True)

def clean(text):
    return re.sub(r'\d+|-->|\n', ' ', text)

VOICE = {
    "male": "en-US-GuyNeural",
    "female": "en-US-AriaNeural"
}

async def tts(text, voice):
    file = f"{TMP}/{uuid.uuid4()}.mp3"
    com = edge_tts.Communicate(text, voice)
    await com.save(file)
    return file

@app.post("/text")
async def text(text: str = Form(...), voice: str = Form("male")):
    file = await tts(text, VOICE.get(voice))
    return FileResponse(file, media_type="audio/mpeg")

@app.post("/srt")
async def srt(file: UploadFile = File(...), voice: str = Form("male")):
    content = (await file.read()).decode()
    text = clean(content)
    file = await tts(text, VOICE.get(voice))
    return FileResponse(file, media_type="audio/mpeg")
