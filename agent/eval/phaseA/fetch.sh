#!/bin/bash
# Kinetics-400 "hitting baseball" val 클립 확보 (READ-ONLY 분석용)
# 영상은 각 YouTube 업로더 저작물 — 저장소에 커밋하지 않는다.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/supersub-phaseA
log=fetch.log; : > "$log"
grep -P '\tOK\t' probe_val.tsv | while IFS=$'\t' read -r yid st ts te info; do
  out="clips/${yid}.mp4"
  [[ -s "$out" ]] && { echo "skip $yid" >> "$log"; continue; }
  yt-dlp --quiet --no-warnings \
    -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b" \
    --download-sections "*${ts}-${te}" --force-keyframes-at-cuts \
    --merge-output-format mp4 -o "$out" \
    "https://www.youtube.com/watch?v=$yid" >> "$log" 2>&1 \
    && echo "ok $yid" >> "$log" || echo "fail $yid" >> "$log"
done
echo "FETCH DONE"
