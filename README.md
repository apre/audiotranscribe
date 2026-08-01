# audiotranscribe

> ⚠️ **Disclaimer: this is an ai generated project**

**Word-level audio transcription for HyperFrames & HeyGen captions.**

`audiotranscribe` converts `.wav` files into timestamped word-level JSON — the
format consumed by [HyperFrames](https://hyperframes.ai/) and HeyGen's caption
overlays. It comes with a terminal-based karaoke playback mode to verify results.

## Features

- **Accurate transcription** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2-accelerated Whisper)
- **Word-level timestamps** — every word gets `start` and `end` in seconds
- **Batch processing** — transcribe many `.wav` files in one command
- **Language-aware** — auto-detect or specify language; English-only and multilingual models
- **TUI karaoke verifier** — play back transcripts in the terminal with synced audio (`play` subcommand, zero external dependencies)
- **HyperFrames-compatible output** — flat JSON array of `{id, text, start, end}` objects
- **Silence filtering** — VAD filter tightens onset timing automatically

## Quick start

```sh
pip install faster-whisper
# ffmpeg must be on PATH (brew install ffmpeg / apt install ffmpeg)
```

```sh
# Transcribe
python wav_to_transcript.py audio/*.wav --model small --language fr

# Verify in the terminal
python wav_to_transcript.py play audio/1.transcript.json --wav audio/1.wav
```

## Output format

Each input `foo.wav` produces `foo.transcript.json`:

```json
[
  { "id": "w0", "text": "La",     "start": 0.24, "end": 0.72 },
  { "id": "w1", "text": "France", "start": 0.72, "end": 1.0  }
]
```

`start` / `end` are in seconds. The `id` field (`w0`, `w1`, …) gives stable
references for caption overrides.

## Documentation

- [TRANSCRIBE.md](TRANSCRIBE.md) — full setup, usage, options, and TUI playback guide

## License

[WTFPL](LICENSE) — Do What The Fuck You Want To Public License.
