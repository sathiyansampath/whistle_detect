#!/usr/bin/env python3
"""
Energy‑envelope pressure‑cooker whistle counter
==============================================

Counts every whistle blast **exactly once**, no matter how long it lasts.

Quick start
-----------
$ python3 -m pip install sounddevice numpy
$ python3 detect_whistles.py           # defaults usually work
# or, e.g.:
$ python3 detect_whistles.py --min 0.8 --max 10 --rise 5 --fall 3

Tunable options (see argparse in code):
  --fs            sample‑rate (Hz)            [16 000]
  --chunk         frames per callback         [1024]
  --min / --max   accepted whistle length (s) [1.0 / 15.0]
  --rise          start whistle at   rise×noise [6]
  --fall          end   whistle below fall×noise [3]
  --hold          silence needed to close (s) [0.4]
  --alpha         noise‑floor smoothing       [0.02]
  --warmup        seconds at start to learn baseline [1.0]
"""

import argparse, time, sys
import numpy as np
import sounddevice as sd

# ----------------------------------------------------------------------
# Command‑line parameters
# ----------------------------------------------------------------------
P = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
P.add_argument("--fs",    type=int,   default=16_000, help="sample rate (Hz)")
P.add_argument("--chunk", type=int,   default=1024,   help="frames per audio callback")
P.add_argument("--min",   type=float, default=1.0,    help="minimum whistle length (s)")
P.add_argument("--max",   type=float, default=15.0,   help="maximum whistle length (s)")
P.add_argument("--rise",  type=float, default=6.0,    help="energy ×noise_floor to START a whistle")
P.add_argument("--fall",  type=float, default=3.0,    help="energy ×noise_floor to END   a whistle")
P.add_argument("--hold",  type=float, default=0.4,    help="quiet seconds required to close whistle")
P.add_argument("--alpha", type=float, default=0.02,   help="noise‑floor smoothing (0‑1)")
P.add_argument("--warmup",type=float, default=1.0,    help="baseline‑learning period at start (s)")
args = P.parse_args()

if args.fall >= args.rise:
    sys.exit("--fall must be smaller than --rise (hysteresis)")

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def rms(x: np.ndarray) -> float:
    """root‑mean‑square energy of a mono chunk"""
    return float(np.sqrt(np.mean(x**2) + 1e-12))

# ----------------------------------------------------------------------
# Global state
# ----------------------------------------------------------------------
noise_floor = None           # unknown until seeded
stream_t0   = None           # absolute time when first callback arrives
state       = "IDLE"         # or "IN_WHISTLE"
whistle_t0  = 0.0
low_since   = None
count       = 0

# ----------------------------------------------------------------------
# Audio callback (runs in PortAudio thread)
# ----------------------------------------------------------------------
def callback(indata, frames, time_info, status):
    global noise_floor, stream_t0, state, whistle_t0, low_since, count

    if status:
        # XRuns or overflow – print once, still keep going
        print(status, file=sys.stderr)

    now = time_info.inputBufferAdcTime  # seconds since audio backend started
    if stream_t0 is None:
        stream_t0 = now                 # first ever timestamp

    x = indata[:, 0]                    # mono
    e = rms(x)                          # short‑term energy

    # ---------- 1. seed or update noise floor ----------
    if noise_floor is None:
        noise_floor = e                 # seed with first chunk
        return                          # don't detect on this buffer

    # warm‑up period: adapt floor but don't detect
    if now - stream_t0 < args.warmup:
        noise_floor = (1 - args.alpha) * noise_floor + args.alpha * e
        return

    # regular adaptive noise floor
    noise_floor = (1 - args.alpha) * noise_floor + args.alpha * e

    # ---------- 2. state machine ----------
    if state == "IDLE":
        if e > args.rise * noise_floor:
            # whistle starts
            whistle_t0 = now
            state      = "IN_WHISTLE"
            low_since  = None
            print(f"[{now - stream_t0:6.2f}s] Whistle start")

    else:  # IN_WHISTLE
        if e < args.fall * noise_floor:
            # potential end, start/extend quiet timer
            low_since = low_since or now
            if now - low_since >= args.hold:
                # whistle finished
                duration = now - whistle_t0
                state    = "IDLE"
                if args.min <= duration <= args.max:
                    count += 1
                    print(f"[{now - stream_t0:6.2f}s] Whistle #{count}  "
                          f"duration {duration:.2f}s")
                else:
                    print(f"[{now - stream_t0:6.2f}s] Ignored whistle "
                          f"({duration:.2f}s out of range)")
        else:
            low_since = None   # energy bounced back – still in whistle

# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    print("Listening…  press Ctrl‑C to exit.")
    try:
        with sd.InputStream(channels=1,
                            samplerate=args.fs,
                            blocksize=args.chunk,
                            dtype="float32",
                            callback=callback):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\nStopped. Total whistles counted: {count}")

if __name__ == "__main__":
    main()
