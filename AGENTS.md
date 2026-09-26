# claude-video

Procedural 15s motion-design showreel (Python stdlib + pycairo + PangoCairo + ffmpeg; no numpy).

- `reel.py` — all visuals; scenes are keyed to absolute seconds at 120 BPM (beat = 0.5s).
- `audio.py` — stdlib synth soundtrack, hits aligned to the same timeline.
- `python3 render.py sheet 1.0 2.5 ...` — contact sheet of stills at given seconds -> `out/sheet.png` (fast design check).
- `python3 render.py video --samples 8` — full 1080p60 render with 8-sample motion blur + audio -> `out/showreel.mp4` (~1 min on 16 cores).
