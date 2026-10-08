import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "scan-test.log"

cpu = None
gpu = None
title = None
link = None

missing = Counter()

with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for raw in f:
        line = raw.strip()

        if line.startswith("[LOCAL]") or line.startswith("[POLSKA]"):
            title = line

        elif line.startswith("LINK:"):
            link = line[5:].strip()

        elif line.startswith("CPU:"):
            cpu = line[4:].strip()

        elif line.startswith("GPU:"):
            gpu = line[4:].strip()

        elif "[ODRZUT WYCENA]" in line:
            key = (
                cpu or "BRAK CPU",
                gpu or "BRAK GPU",
                title or "",
                link or "",
            )
            missing[key] += 1

print("\n=== BRAKUJĄCE WYCENY ===\n")

if not missing:
    print("Brak.")
    raise SystemExit

for (cpu, gpu, title, link), count in missing.most_common():
    print(f"{cpu} | {gpu} | x{count}")
    if title:
        print(title)
    if link:
        print(link)
    print()
