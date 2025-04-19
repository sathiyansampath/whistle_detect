# whistle_detect
Detects and counts pressure cooker whistles

Usage

python detect_whistles.py \
    --min 1.0  --max 8        \  # duration window
    --rise 5   --fall 3       \  # energy thresholds
    --hold 0.3 --alpha 0.02      # gap & noise‑floor adaptation

# Updated in revision-2 with some warmup period.
python3 detect_whistles.py --min 3.0 --max 8 --rise 6 --fall 2 --hold 4 --alpha 0.02 --warmup 2

