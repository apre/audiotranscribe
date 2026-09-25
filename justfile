env := "audiotranscribe"
rec := "test.wav"
# miniconda install dir; override with CONDA_ROOT=... (no `conda init` needed)
conda_root := env_var_or_default("CONDA_ROOT", home_directory() / "local/opt/miniconda3")
py := conda_root / "envs" / env / "bin/python"

default:
    @just --list

# install `wav_to_transcript` into ~/local/bin (conda env python) + the claude skill
install:
    #!/bin/sh
    set -e
    py="{{py}}"
    [ -x "$py" ] || { echo "$py missing — create the '{{env}}' conda env (README) or set CONDA_ROOT" >&2; exit 1; }
    mkdir -p ~/local/bin
    rm -f ~/local/bin/wav_to_transcript
    printf '#!/bin/sh\nexec "%s" "%s" "$@"\n' "$py" "{{justfile_directory()}}/wav_to_transcript.py" \
      > ~/local/bin/wav_to_transcript
    chmod +x ~/local/bin/wav_to_transcript
    echo "installed: wav_to_transcript -> $py"
    mkdir -p ~/.claude/skills
    ln -sfn "{{justfile_directory()}}/skill" ~/.claude/skills/transcribe-audio
    echo "installed: claude skill transcribe-audio"

# list microphones (index to pass to `record`)
mics:
    -ffmpeg -hide_banner -f avfoundation -list_devices true -i "" 2>&1 | sed -n '/audio devices/,$p' | sed -n 's/.*\] \(\[[0-9]*\] .*\)/\1/p'

# record a test audio file (press q to stop); mic = index from `just mics`
record file=rec mic="0":
    ffmpeg -hide_banner -y -f avfoundation -i ":{{mic}}" -ac 1 {{file}}

# transcribe a wav (default: the recorded file); lang e.g. fr/en, empty = auto-detect; extra args go to the script
transcribe file=rec lang="" *args:
    "{{py}}" wav_to_transcript.py {{file}} -m medium {{ if lang != "" { "-l " + lang } else { "" } }} {{args}}

# TUI file picker over the .wav + transcript pairs in a folder
pick dir=".":
    "{{py}}" wav_to_transcript.py play {{dir}}

# karaoke playback of the recorded file
play file=rec:
    "{{py}}" wav_to_transcript.py play {{without_extension(file)}}.transcript.json --wav {{file}}
