#!/usr/bin/env python3
"""
Energy‑envelope pressure‑cooker whistle counter.

pip install sounddevice numpy
"""
import argparse, time, sys
import numpy as np
import sounddevice as sd

# ----------------------------------------------------------------------
# Command‑line parameters
# ----------------------------------------------------------------------
P = argparse.ArgumentParser()
P.add_argument("--fs",    type=int,   default=16_000,
               help="sample rate (Hz)")
P.add_argument("--chunk", type=int,   default=1024,
               help="frames per audio callback")
P.add_argument("--min",   type=float, default=2.0,
               help="minimum whistle length (s)")
P.add_argument("--max",   type=float, default=15.0,
               help="maximum whistle length (s)")
P.add_argument("--rise",  type=float, default=6.0,
               help="energy multiple above noise floor to start a whistle")
P.add_argument("--fall",  type=float, default=3.0,
               help="multiple to end a whistle (must be < rise)")
P.add_argument("--hold",  type=float, default=0.4,
               help="seconds energy must stay low before ending whistle")
P.add_argument("--alpha", type=float, default=0.01,
               help="noise‑floor smoothing (0.0–1.0)")
args = P.parse_args()

assert args.fall < args.rise, "--fall must be lower than --rise"

# ----------------------------------------------------------------------
# State variables
# ----------------------------------------------------------------------
noise_floor = 1e-6                 # initialise very low
state       = "IDLE"               # or "IN_WHISTLE"
whistle_t0  = 0.0
low_since   = None
count       = 0

def rms(x: np.ndarray) -> float:
    return np.sqrt(np.mean(x**2) + 1e-12)

def callback(indata, frames, time_info, status):
    global noise_floor, state, whistle_t0, count, low_since

    if status:
        print(status, file=sys.stderr)

    now  = time_info.inputBufferAdcTime
    x    = indata[:, 0]
    e    = rms(x)

    # ------------------- update adaptive noise floor -------------------
    noise_floor = (1 - args.alpha) * noise_floor + args.alpha * e

    if state == "IDLE":
        if e > args.rise * noise_floor:
            # ----------- whistle starts -----------
            whistle_t0 = now
            state      = "IN_WHISTLE"
            low_since  = None
            print(f"Whistle start at {now:.1f}s (energy {e:.3f})")

    else:  # IN_WHISTLE
        if e < args.fall * noise_floor:
            low_since = low_since or now
            if now - low_since >= args.hold:
                duration = now - whistle_t0
                state    = "IDLE"
                if args.min <= duration <= args.max:
                    count += 1
                    print(f"Whistle #{count}  duration {duration:.1f}s")
                else:
                    print(f"Ignored whistle ({duration:.1f}s ‑ out of range)")
        else:
            low_since = None   # energy bounced back up – still in whistle

try:
    with sd.InputStream(channels=1,
                        samplerate=args.fs,
                        blocksize=args.chunk,
                        dtype="float32",
                        callback=callback):
        print("Listening…  Ctrl‑C to exit.")
        while True:
            time.sleep(1)
except KeyboardInterrupt:
    print("\nStopped. Total whistles:", count)
