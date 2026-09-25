---
name: transcribe-audio
description: Use when the user wants an audio or video file (wav, mp3, m4a, mp4, …) transcribed to text or to word-level timestamps / captions (HyperFrames, HeyGen), or wants to check a transcript by playing it back.
---

# Transcribe audio with `wav_to_transcript`

`wav_to_transcript` (installed in `~/local/bin` by `just install` in the
audiotranscribe repo) runs faster-whisper locally and writes word-level JSON.

## Transcribe

```sh
wav_to_transcript path/to/file.wav [more files…] [-l fr] [-m small]
```

- Output: `<file stem>.transcript.json` next to each input. `-o out.json` works only with a single input.
- Model (`-m`): the default is `small.en`, which is **English only**. For any other language, or if you don't know the language, pass a multilingual model (`-m small`, `-m medium`, `-m large-v3`) and set `-l <code>` if you know it.
- The first run downloads the model. Transcription takes a while on CPU, so run long batches in the background.
- Input: faster-whisper decodes any format ffmpeg can read. If decoding fails, convert first: `ffmpeg -i in.m4a -ac 1 -ar 16000 in.wav`.

## Output format

```json
[{ "id": "w0", "text": "Hello", "start": 0.24, "end": 0.72 }, …]
```

Times are in seconds. To get plain text, join the `text` fields with spaces.

## Verify (interactive, the user has to run it)

The karaoke player is a curses TUI, so you can't drive it yourself. Give the user the command:

```sh
wav_to_transcript play file.transcript.json --wav file.wav   # one file
wav_to_transcript play some/folder/                         # picker over folder
```

In the player, q/ESC goes back to the file list. In the file list, q/ESC quits.

## If the command is missing

The user needs to run `just install` in the audiotranscribe repo. It needs the `audiotranscribe` conda env (see that repo's README).
