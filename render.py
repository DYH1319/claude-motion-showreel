"""Render the reel.

  python3 render.py sheet 0.2 1.1 ...   -> contact sheet of stills at given seconds (out/sheet.png)
  python3 render.py video [--samples N] -> out/showreel.mp4 (with soundtrack from audio.py)
"""
import os
import subprocess
import sys
import time
from multiprocessing import get_context

import reel

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
SAMPLES = 1


def _frame(i):
    return bytes(reel.render_frame(i, SAMPLES).get_data())


def _still(args):
    t, path = args
    reel.render_frame(round(t * reel.FPS)).write_to_png(path)


def sheet(times):
    d = os.path.join(OUT, "stills")
    os.makedirs(d, exist_ok=True)
    jobs = [(t, os.path.join(d, f"s{n:03d}.png")) for n, t in enumerate(times)]
    with get_context("fork").Pool(min(len(jobs), os.cpu_count())) as p:
        p.map(_still, jobs)
    cols = 4
    rows = (len(jobs) + cols - 1) // cols
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(d, "s%03d.png"), "-vf",
                    f"scale=640:-1,tile={cols}x{rows}:padding=6:color=white", "-frames:v", "1",
                    os.path.join(OUT, "sheet.png")], check=True)


def video(samples):
    global SAMPLES
    SAMPLES = samples
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "soundtrack.wav")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(OUT), "audio.py"), wav], check=True)
    n = int(reel.DUR * reel.FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr0", "-s", f"{reel.W}x{reel.H}",
        "-r", str(reel.FPS), "-i", "-", "-i", wav,
        "-vf", "format=yuv444p,noise=c0s=5:c0f=t+u,vignette=angle=0.28,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-tune", "film",
        "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
        os.path.join(OUT, "showreel.mp4")], stdin=subprocess.PIPE)
    t0 = time.time()
    with get_context("fork").Pool(os.cpu_count()) as p:
        for k, buf in enumerate(p.imap(_frame, range(n), chunksize=2)):
            ff.stdin.write(buf)
            if k % 60 == 0:
                print(f"frame {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    if sys.argv[1] == "sheet":
        sheet([float(x) for x in sys.argv[2:]])
    else:
        video(int(sys.argv[sys.argv.index("--samples") + 1]) if "--samples" in sys.argv else 4)
