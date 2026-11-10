#!/usr/bin/env python3
"""Видео модуля: слайды презентации и озвучка текста из заметок.

Каждый слайд держится на экране, пока звучит его текст. Голос — Yandex SpeechKit API v3,
по умолчанию «Денис» (модель LiveTTS). Ключ берётся из YANDEX_SPEECHKIT_API_KEY
(и YANDEX_FOLDER_ID, если он задан).

    python3 presentations/make_video.py --module 01               # всё видео модуля 1
    python3 presentations/make_video.py --module 03 --only 1,3,5  # проба на нескольких слайдах
    python3 presentations/make_video.py --module 02 --silent      # проверить сборку без озвучки

Перед этим соберите презентацию: python3 presentations/build_alpNN_from_book.py.
Нужны LibreOffice (soffice), poppler (pdftoppm) и ffmpeg.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

BUILD = ROOT / "build"
TTS_URL = os.environ.get("YANDEX_TTS_URL", "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis")
LIVETTS_VOICES = {"denis", "sofia", "vera", "vasily", "sergey", "irina"}
RATE = 48000
MAX_CHARS = 240
SENTENCE_GAP = 0.25
LEAD_IN = 0.5
TAIL = 0.9


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def render_slides(pptx: Path, work: Path) -> list[Path]:
    frames = work / "frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(work), str(pptx)])
    pdf = work / (pptx.stem + ".pdf")
    run(["pdftoppm", "-png", "-scale-to-x", "1920", "-scale-to-y", "1080", str(pdf), str(frames / "slide")])
    return sorted(frames.glob("slide-*.png"))


def speech_text(narration: str) -> str:
    return narration.replace("«", "").replace("»", "")


def sentences(text: str, limit: int = MAX_CHARS) -> list[str]:
    """Режет текст по предложениям в куски не длиннее limit символов."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    chunks: list[str] = []
    for part in parts:
        while len(part) > limit:
            cut = part.rfind(",", 0, limit)
            cut = cut if cut > 0 else part.rfind(" ", 0, limit)
            chunks.append(part[: cut + 1].strip())
            part = part[cut + 1:].strip()
        if chunks and len(chunks[-1]) + len(part) + 1 <= limit:
            chunks[-1] += " " + part
        else:
            chunks.append(part)
    return chunks


def request_pcm(text: str, voice: str, role: str, speed: str) -> bytes:
    key = os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if not key:
        raise SystemExit("Нет YANDEX_SPEECHKIT_API_KEY. Добавьте ключ в секреты или запустите с --silent.")
    hints: list[dict] = [{"voice": voice}]
    if role:
        hints.append({"role": role})
    body: dict = {
        "text": text,
        "hints": hints,
        "outputAudioSpec": {"rawAudio": {"audioEncoding": "LINEAR16_PCM", "sampleRateHertz": str(RATE)}},
        "loudnessNormalizationType": "LUFS",
    }
    if voice in LIVETTS_VOICES:
        body["model"] = "livetts"
    else:
        hints.append({"speed": speed})
    headers = {"Authorization": f"Api-Key {key}", "Content-Type": "application/json"}
    if os.environ.get("YANDEX_FOLDER_ID"):
        headers["x-folder-id"] = os.environ["YANDEX_FOLDER_ID"]
    req = urllib.request.Request(TTS_URL, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as err:
        raise SystemExit(f"SpeechKit ответил {err.code}: {err.read().decode(errors='replace')}") from err

    pcm = bytearray()
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(raw):
        while pos < len(raw) and raw[pos].isspace():
            pos += 1
        if pos >= len(raw):
            break
        message, pos = decoder.raw_decode(raw, pos)
        if "error" in message:
            raise SystemExit(f"SpeechKit вернул ошибку: {message['error']}")
        chunk = message.get("result", message).get("audioChunk")
        if chunk:
            pcm += base64.b64decode(chunk["data"])
    if not pcm:
        raise SystemExit(f"SpeechKit не вернул звук для текста: {text[:80]}…")
    return bytes(pcm)


def synthesize(text: str, dest: Path, voice: str, role: str, speed: str) -> None:
    pause = b"\x00\x00" * int(RATE * SENTENCE_GAP)
    pcm = bytearray()
    for i, chunk in enumerate(sentences(text)):
        if i:
            pcm += pause
        pcm += request_pcm(chunk, voice, role, speed)
    with wave.open(str(dest), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(pcm))


def silence(text: str, dest: Path) -> None:
    seconds = max(3.0, len(text.split()) / 2.3)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.2f}",
         "-c:a", "libopus", str(dest)])


def audio_for(work: Path, index: int, text: str, voice: str, role: str, speed: str, silent: bool) -> Path:
    audio = work / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    tag = "silent" if silent else f"{voice}-{role}-{speed}"
    digest = hashlib.sha1(f"{tag}|{text}".encode()).hexdigest()[:10]
    dest = audio / f"{index:02d}-{digest}.{'ogg' if silent else 'wav'}"
    if not dest.exists():
        if silent:
            silence(text, dest)
        else:
            synthesize(text, dest, voice, role, speed)
    return dest


def segment(frame: Path, audio: Path, dest: Path) -> None:
    delay = int(LEAD_IN * 1000)
    run([
        "ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(frame), "-i", str(audio),
        "-af", f"adelay={delay}|{delay},apad=pad_dur={TAIL}",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-shortest", str(dest),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="03", help="номер модуля: 01, 02, 03")
    parser.add_argument("--only", help="номера слайдов через запятую, например 1,3,5")
    parser.add_argument("--silent", action="store_true", help="без озвучки, паузы по длине текста")
    parser.add_argument("--voice", default=os.environ.get("YANDEX_TTS_VOICE", "denis"))
    parser.add_argument("--role", default=os.environ.get("YANDEX_TTS_ROLE", ""),
                        help="амплуа голоса; у denis: neutral, formal, casual, sales")
    parser.add_argument("--speed", default=os.environ.get("YANDEX_TTS_SPEED", "1.0"),
                        help="темп; голоса LiveTTS (denis и др.) его не поддерживают")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    number = args.module.zfill(2)
    script = f"build_alp{number}_from_book"
    try:
        scenario = importlib.import_module(script)
    except ModuleNotFoundError as err:
        raise SystemExit(f"Нет сценария presentations/{script}.py") from err
    pptx, slides = scenario.OUT, scenario.SLIDES
    if not pptx.exists():
        raise SystemExit(f"Сначала соберите презентацию: python3 presentations/{script}.py")
    work = BUILD / f"m{number}"
    work.mkdir(parents=True, exist_ok=True)
    frames = render_slides(pptx, work)
    if len(frames) != len(slides):
        raise SystemExit(f"Слайдов в PDF {len(frames)}, а в сценарии {len(slides)}.")

    wanted = range(1, len(slides) + 1)
    if args.only:
        wanted = [int(n) for n in args.only.split(",")]

    parts = work / "parts"
    if parts.exists():
        shutil.rmtree(parts)
    parts.mkdir()
    listing = []
    for n in wanted:
        text = speech_text(slides[n - 1].narration)
        audio = audio_for(work, n, text, args.voice, args.role, args.speed, args.silent)
        part = parts / f"{n:02d}.mp4"
        segment(frames[n - 1], audio, part)
        listing.append(f"file '{part.as_posix()}'")
        print(f"слайд {n:02d} готов")

    concat = parts / "list.txt"
    concat.write_text("\n".join(listing) + "\n")
    suffix = "-proba" if args.only else ""
    out = args.out or BUILD / f"{pptx.stem.replace('-naglyadno', '')}-video{suffix}.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy",
         "-movflags", "+faststart", str(out)])
    print(f"видео: {out}")


if __name__ == "__main__":
    main()
