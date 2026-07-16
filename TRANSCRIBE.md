# Usage guide

> Full reference for transcribing audio and verifying transcripts with the
> TUI karaoke player.

`wav_to_transcript.py` generates [HyperFrames](https://hyperframes.ai/)- and
HeyGen-compatible word-level timestamps from `.wav` files, and can play a
transcript back in the terminal to verify it.

## Output format

HyperFrames (and HeyGen's export) consume a **flat JSON array of word objects**,
one file per input `.wav`:

```json
[
  { "id": "w0", "text": "La",     "start": 0.24, "end": 0.72 },
  { "id": "w1", "text": "France", "start": 0.72, "end": 1.0  }
]
```

`start` / `end` are in **seconds**. `id` (`w0`, `w1`, …) gives stable references
for caption overrides. Each input `foo.wav` produces `foo.transcript.json` next
to it.

## Setup

```sh
pip install -r requirements.txt   # or: pip install faster-whisper
# ffmpeg must be on PATH (faster-whisper decodes audio through it)
# macOS `afplay` (built in) is used by `play --wav`; optional
```

`play` uses only the Python stdlib (`curses`) — no `faster-whisper` needed.

## Transcribe the folder

```sh
python wav_to_transcript.py audio/*.wav --model small --language fr
```

- `transcribe` is the default subcommand, so the word can be omitted.
- Writes `audio/1.transcript.json`, `audio/2.transcript.json`, … one per `.wav`.
- Bad/missing files are skipped with an error; the rest of the batch still runs.

### Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `-m, --model` | `small.en` | `tiny(.en)`, `base(.en)`, `small(.en)`, `medium(.en)`, `large-v3`. `.en` variants are English-only. |
| `-l, --language` | auto-detect | Language code (`fr`, `en`, `es`, …). |
| `-o, --output` | `<input>.transcript.json` | Force a single output path (only with **one** input). |
| `--device` | `auto` | `cpu`, `cuda`, or `auto`. |
| `--compute-type` | `default` | `int8`, `float16`, `float32`. |

> **Language matters.** The `.en` models transcribe non-English audio as garbled
> English. For French audio use a multilingual model **and** the language flag:
> `--model small --language fr`.

## Verify — TUI playback

Play a transcript back karaoke-style: each word highlights at its `start` time,
with a real-time progress bar.

```sh
python wav_to_transcript.py play audio                                   # pick from a folder
python wav_to_transcript.py play audio/1.transcript.json                 # visual only
python wav_to_transcript.py play audio/1.transcript.json --wav audio/1.wav   # with synced audio
python wav_to_transcript.py play audio/1.transcript.json --wav audio/1.wav --speed 1.5
```

- **Folder argument** → a picker lists every eligible `.wav` + transcript pair
  (`<name>.wav` with a matching `<name>.transcript.json` or `<name>.json`).
  Navigate with **↑/↓** or **j/k**, **Enter** to play (the matching `.wav` is
  auto-paired), **q** to quit.
- Words are colored **spoken** (past) / **active** (now) / **upcoming** (future).
- `--wav` plays the audio alongside via macOS `afplay`; `--speed` scales both.
- Press `q` or `ESC` to quit; the final frame holds until a key is pressed.

`play` also accepts wrapped transcript shapes (e.g. `audio_meta.json`'s
`voices[].words`, `caption_groups.json`'s `groups[].words`), not just the flat
array.

## Notes

- A harmless `float16 … converted to float32` line may appear — it just means the
  CPU has no efficient float16 path. Output is unaffected.
- `hyperframes transcribe` (the built-in CLI) covers the transcription half too;
  this script is a dependency-light, scriptable equivalent plus the playback
  verifier the CLI doesn't have.
