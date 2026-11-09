#!/usr/bin/env python3
"""Видео модуля 3: слайды презентации и озвучка текста из заметок.

Каждый слайд держится на экране, пока звучит его текст. Голос — Yandex SpeechKit,
ключ берётся из YANDEX_SPEECHKIT_API_KEY (и YANDEX_FOLDER_ID, если он задан).

    python3 presentations/make_alp03_video.py               # всё видео
    python3 presentations/make_alp03_video.py --only 1,3,5  # проба на нескольких слайдах
    python3 presentations/make_alp03_video.py --silent      # проверить сборку без озвучки

Нужны LibreOffice (soffice), poppler (pdftoppm) и ffmpeg.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_alp03_from_book import OUT as PPTX, SLIDES  # noqa: E402

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
LEAD_IN = 0.5
TAIL = 0.9


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def render_slides() -> list[Path]:
    frames = BUILD / "frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(BUILD), str(PPTX)])
    pdf = BUILD / (PPTX.stem + ".pdf")
    run(["pdftoppm", "-png", "-scale-to-x", "1920", "-scale-to-y", "1080", str(pdf), str(frames / "slide")])
    return sorted(frames.glob("slide-*.png"))


def speech_text(narration: str) -> str:
    return narration.replace("«", "").replace("»", "")


def synthesize(text: str, dest: Path, voice: str, speed: str) -> None:
    key = os.environ.get("YANDEX_SPEECHKIT_API_KEY")
    if not key:
        raise SystemExit("Нет YANDEX_SPEECHKIT_API_KEY. Добавьте ключ в секреты или запустите с --silent.")
    form = {"text": text, "lang": "ru-RU", "voice": voice, "speed": speed, "format": "oggopus"}
    if os.environ.get("YANDEX_FOLDER_ID"):
        form["folderId"] = os.environ["YANDEX_FOLDER_ID"]
    req = urllib.request.Request(
        TTS_URL,
        data=urllib.parse.urlencode(form).encode(),
        headers={"Authorization": f"Api-Key {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dest.write_bytes(resp.read())
    except urllib.error.HTTPError as err:
        raise SystemExit(f"SpeechKit ответил {err.code}: {err.read().decode(errors='replace')}") from err


def silence(text: str, dest: Path) -> None:
    seconds = max(3.0, len(text.split()) / 2.3)
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.2f}",
         "-c:a", "libopus", str(dest)])


def audio_for(index: int, text: str, voice: str, speed: str, silent: bool) -> Path:
    audio = BUILD / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    tag = "silent" if silent else f"{voice}-{speed}"
    digest = hashlib.sha1(f"{tag}|{text}".encode()).hexdigest()[:10]
    dest = audio / f"{index:02d}-{digest}.ogg"
    if not dest.exists():
        if silent:
            silence(text, dest)
        else:
            synthesize(text, dest, voice, speed)
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
    parser.add_argument("--only", help="номера слайдов через запятую, например 1,3,5")
    parser.add_argument("--silent", action="store_true", help="без озвучки, паузы по длине текста")
    parser.add_argument("--voice", default=os.environ.get("YANDEX_TTS_VOICE", "alena"))
    parser.add_argument("--speed", default=os.environ.get("YANDEX_TTS_SPEED", "1.0"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if not PPTX.exists():
        raise SystemExit("Сначала соберите презентацию: python3 presentations/build_alp03_from_book.py")
    BUILD.mkdir(exist_ok=True)
    frames = render_slides()
    if len(frames) != len(SLIDES):
        raise SystemExit(f"Слайдов в PDF {len(frames)}, а в сценарии {len(SLIDES)}.")

    wanted = range(1, len(SLIDES) + 1)
    if args.only:
        wanted = [int(n) for n in args.only.split(",")]

    parts = BUILD / "parts"
    if parts.exists():
        shutil.rmtree(parts)
    parts.mkdir()
    listing = []
    for n in wanted:
        text = speech_text(SLIDES[n - 1].narration)
        audio = audio_for(n, text, args.voice, args.speed, args.silent)
        part = parts / f"{n:02d}.mp4"
        segment(frames[n - 1], audio, part)
        listing.append(f"file '{part.as_posix()}'")
        print(f"слайд {n:02d} готов")

    concat = parts / "list.txt"
    concat.write_text("\n".join(listing) + "\n")
    suffix = "-proba" if args.only else ""
    out = args.out or BUILD / f"ALP-03_laviny-video{suffix}.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy",
         "-movflags", "+faststart", str(out)])
    print(f"видео: {out}")


if __name__ == "__main__":
    main()
