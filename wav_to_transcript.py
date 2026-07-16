#!/usr/bin/env python3
"""Generate HyperFrames-compatible word-level timestamps from .wav files.

HyperFrames (and HeyGen's export) consume a flat JSON array of word objects:

    [
      { "id": "w0", "text": "Hello", "start": 0.0, "end": 0.5 },
      { "id": "w1", "text": "world.", "start": 0.6, "end": 1.2 }
    ]

`start` / `end` are in seconds. `id` (w0, w1, ...) gives stable references for
caption overrides. This script produces exactly that shape, one transcript.json
per input .wav.

Usage:
    # transcribe (default subcommand — "transcribe" may be omitted):
    python wav_to_transcript.py assets/voice/01.wav
    python wav_to_transcript.py transcribe audio/*.wav --model small
    python wav_to_transcript.py 01.wav --language fr --model medium -o out.json

    # test mode: play a transcript back karaoke-style in the terminal (TUI),
    # optionally alongside its .wav:
    python wav_to_transcript.py play audio/1.transcript.json
    python wav_to_transcript.py play audio/1.transcript.json --wav audio/1.wav

By default a sidecar `<name>.transcript.json` is written next to each input.
Pass -o to force a single output path (only valid with one input).

Requires:
    pip install faster-whisper   # for transcribe; not needed for `play`
    # ffmpeg must be on PATH (faster-whisper decodes audio through it)
    # macOS `afplay` (built in) is used by `play --wav`; optional.

Language note: the multilingual models ("small", "medium", "large-v3") auto-detect
language. The English-only models ("small.en", etc.) will transcribe non-English
audio as garbled English — pass --language / a non-.en model for other languages.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def transcribe_words(wav_path, model_name, language, device, compute_type):
    """Return a flat list of {id, text, start, end} word dicts for one file."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        str(wav_path),
        language=language,          # None => auto-detect
        word_timestamps=True,
        vad_filter=True,            # trims silence, tightens onset timing
    )

    words = []
    for segment in segments:
        # word_timestamps=True populates segment.words; guard in case a segment
        # yields none (e.g. pure music/silence).
        for word in (segment.words or []):
            words.append(
                {
                    "id": f"w{len(words)}",
                    "text": word.word.strip(),
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                }
            )
    return words, info


def default_output(wav_path):
    return wav_path.with_suffix(".transcript.json")


def cmd_transcribe(args, parser):
    if args.output is not None and len(args.inputs) > 1:
        parser.error("-o/--output only works with a single input file.")

    exit_code = 0
    for wav_path in args.inputs:
        if not wav_path.exists():
            print(f"skip: {wav_path} does not exist", file=sys.stderr)
            exit_code = 1
            continue

        try:
            words, info = transcribe_words(
                wav_path, args.model, args.language, args.device, args.compute_type
            )
        except Exception as exc:  # surface, keep going through the batch
            print(f"error: {wav_path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        out_path = args.output or default_output(wav_path)
        out_path.write_text(json.dumps(words, ensure_ascii=False, indent=2))

        lang = getattr(info, "language", args.language) or "?"
        print(
            f"{wav_path} -> {out_path}  "
            f"({len(words)} words, lang={lang}, model={args.model})",
            file=sys.stderr,
        )

    return exit_code


# ---------------------------------------------------------------------------
# Test mode: TUI karaoke playback of a transcript.json
# ---------------------------------------------------------------------------

def load_words(json_path):
    """Load a transcript, tolerating both the flat array and the wrapped shapes
    (e.g. audio_meta.json's {"voices":[{"words":[...]}]})."""
    data = json.loads(Path(json_path).read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("words"), list):
            return data["words"]
        # audio_meta.json / caption_groups.json style
        for key in ("voices", "groups"):
            items = data.get(key)
            if isinstance(items, list) and items and "words" in items[0]:
                words = []
                for item in items:
                    words.extend(item.get("words", []))
                return words
    raise ValueError(f"{json_path}: unrecognized transcript shape")


def find_pairs(folder):
    """Return sorted (wav, transcript_json) tuples in `folder` where both exist.

    A transcript is the wav's `<name>.transcript.json` sidecar, or a plain
    `<name>.json` fallback."""
    folder = Path(folder)
    pairs = []
    for wav in sorted(folder.glob("*.wav")):
        for cand in (wav.with_suffix(".transcript.json"), wav.with_suffix(".json")):
            if cand.exists():
                pairs.append((wav, cand))
                break
    return pairs


def pick_pair(pairs):
    """Curses menu over (wav, json) pairs. Returns the chosen tuple, or None."""
    import curses

    def run(stdscr):
        curses.curs_set(0)
        idx = 0
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            stdscr.addnstr(0, 0, "Select a transcript to play "
                           "(↑/↓ or j/k, Enter, q to quit)", width - 1,
                           curses.A_BOLD)
            for i, (wav, js) in enumerate(pairs):
                if i + 2 >= height:
                    break
                label = f"{wav.name}  →  {js.name}"
                attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
                stdscr.addnstr(i + 2, 2, label, width - 3, attr)
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), 27):
                return None
            if key in (curses.KEY_UP, ord("k")):
                idx = (idx - 1) % len(pairs)
            elif key in (curses.KEY_DOWN, ord("j")):
                idx = (idx + 1) % len(pairs)
            elif key in (curses.KEY_ENTER, 10, 13):
                return pairs[idx]

    return curses.wrapper(run)


def cmd_play(args, parser):
    import curses

    target = Path(args.input)
    wav_override = args.wav

    if target.is_dir():
        pairs = find_pairs(target)
        if not pairs:
            print(f"{target}: no .wav + transcript pairs found", file=sys.stderr)
            return 1
        chosen = pick_pair(pairs)
        if chosen is None:
            return 0
        wav_path_sel, target = chosen
        if wav_override is None:
            wav_override = wav_path_sel  # auto-pair the wav with the transcript

    words = load_words(target)
    if not words:
        print(f"{target}: no words to play", file=sys.stderr)
        return 1

    total = max(float(w["end"]) for w in words)
    speed = args.speed if args.speed and args.speed > 0 else 1.0

    audio_proc = None
    if wav_override:
        wav_path = Path(wav_override)
        if not wav_path.exists():
            print(f"warning: {wav_path} not found, playing silently", file=sys.stderr)
        elif shutil.which("afplay"):
            # afplay -r sets the playback rate; keeps audio in sync with --speed.
            audio_proc = lambda: subprocess.Popen(
                ["afplay", "-r", str(speed), str(wav_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            print("warning: `afplay` not found; playing without audio", file=sys.stderr)

    title = target.name

    def run(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # active
            curses.init_pair(2, curses.COLOR_CYAN, -1)                    # spoken
            curses.init_pair(3, curses.COLOR_WHITE, -1)                   # upcoming

        proc = audio_proc() if audio_proc else None
        start = time.monotonic()
        try:
            while True:
                elapsed = (time.monotonic() - start) * speed
                _draw(stdscr, curses, words, elapsed, total, title)
                if stdscr.getch() in (ord("q"), 27):  # q or ESC
                    break
                if elapsed > total + 0.5:
                    break
                time.sleep(1 / 60)
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
        # hold the final frame until a key is pressed
        stdscr.nodelay(False)
        _draw(stdscr, curses, words, total, total, title, done=True)
        stdscr.getch()

    curses.wrapper(run)
    return 0


def _draw(stdscr, curses, words, elapsed, total, title, done=False):
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    bar_w = max(10, width - 20)
    filled = int(bar_w * min(elapsed, total) / total) if total else 0
    bar = "█" * filled + "·" * (bar_w - filled)
    header = "PLAYING" if not done else "DONE"
    stdscr.addnstr(0, 0, f"{header}  {title}", width - 1, curses.A_BOLD)
    stdscr.addnstr(1, 0, f"[{bar}] {min(elapsed, total):5.2f}/{total:5.2f}s", width - 1)
    stdscr.addnstr(2, 0, "q/ESC to quit", width - 1, curses.A_DIM)

    # word-wrapped karaoke text starting on row 4
    row, col = 4, 0
    for w in words:
        text = str(w.get("text", ""))
        token = text + " "
        if col + len(token) >= width:
            row += 1
            col = 0
        if row >= height:
            break
        start_t, end_t = float(w["start"]), float(w["end"])
        if start_t <= elapsed <= end_t:
            attr = curses.color_pair(1) | curses.A_BOLD  # active
        elif elapsed > end_t:
            attr = curses.color_pair(2)                  # already spoken
        else:
            attr = curses.color_pair(3) | curses.A_DIM   # upcoming
        stdscr.addnstr(row, col, token, width - col - 1, attr)
        col += len(token)

    stdscr.refresh()


def main(argv=None):
    # Default to the `transcribe` subcommand when the first token isn't a
    # recognized command, so `wav_to_transcript.py foo.wav` still works.
    argv = list(sys.argv[1:] if argv is None else argv)
    subcommands = {"transcribe", "play"}
    if argv and argv[0] not in subcommands and not argv[0] in ("-h", "--help"):
        argv = ["transcribe"] + argv

    parser = argparse.ArgumentParser(
        description="Generate & test HyperFrames/HeyGen word-level timestamps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_t = sub.add_parser("transcribe", help="Transcribe .wav files to transcript JSON.")
    p_t.add_argument("inputs", nargs="+", type=Path, help="One or more .wav files.")
    p_t.add_argument(
        "-m", "--model", default="small.en",
        help="Whisper model: tiny(.en), base(.en), small(.en), medium(.en), "
             "large-v3. .en variants are English-only. Default: small.en",
    )
    p_t.add_argument(
        "-l", "--language", default=None,
        help="Language code (e.g. en, fr, es). Omit to auto-detect "
             "(multilingual models only).",
    )
    p_t.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output path. Only valid with a single input file. "
             "Default: <input>.transcript.json next to each input.",
    )
    p_t.add_argument("--device", default="auto", help="cpu, cuda, or auto (default).")
    p_t.add_argument(
        "--compute-type", default="default",
        help="faster-whisper compute type (int8, float16, float32). "
             "Default lets the library choose per device.",
    )

    p_p = sub.add_parser("play", help="TUI karaoke playback of a transcript JSON.")
    p_p.add_argument("input", type=Path,
                     help="A transcript.json, OR a folder — a folder shows a "
                          "picker of eligible .wav + transcript pairs.")
    p_p.add_argument("--wav", type=Path, default=None,
                     help="Optional .wav to play alongside (uses macOS afplay).")
    p_p.add_argument("--speed", type=float, default=1.0,
                     help="Playback speed multiplier (default 1.0).")

    args = parser.parse_args(argv)

    if args.command == "play":
        return cmd_play(args, parser)
    return cmd_transcribe(args, parser)


if __name__ == "__main__":
    sys.exit(main())
