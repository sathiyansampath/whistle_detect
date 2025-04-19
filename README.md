# whistle_detect
Detects pressure cooker whistles

Usage

python detect_whistles.py \
    --min 1.0  --max 8        \  # duration window
    --rise 5   --fall 3       \  # energy thresholds
    --hold 0.3 --alpha 0.02      # gap & noise‑floor adaptation
