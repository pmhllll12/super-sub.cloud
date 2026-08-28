#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
out=/mnt/d/supersub-phaseA/probe_val.tsv
: > "$out"
tail -n +2 ann/hb_val.csv | tr -d '"' | while IFS=, read -r label yid ts te split cc; do
  info=$(yt-dlp --skip-download --no-warnings --print "%(width)sx%(height)s|%(fps)s|%(duration)s|%(title)s" \
        "https://www.youtube.com/watch?v=$yid" 2>&1 | head -1)
  if [[ "$info" == *"|"* ]]; then
    echo -e "$yid\tOK\t$ts\t$te\t$info" >> "$out"
  else
    echo -e "$yid\tDEAD\t$ts\t$te\t$(echo "$info" | head -c 120)" >> "$out"
  fi
done
echo "done"
