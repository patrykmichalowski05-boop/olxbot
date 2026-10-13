import json
from pathlib import Path

from valuation import (
    CPU_VALUES, GPU_VALUES,
    normalize_cpu, normalize_gpu,
)
from app_v2.seller_questions_preview_v1 import safe_url

SNAPSHOT = Path(
    "/opt/olx-bot/app_v2/pc_valuation_snapshot_v1.json"
)

VARIANT_GPU = {
    "GTX 960", "GTX 1060",
    "RX 470", "RX 480", "RX 570",
    "RX 580", "RX 5500 XT",
}

REVIEW_CPU = {
    "RYZEN 7 5600G",
    "RYZEN 7 3700",
}


def get_report():
    data = json.loads(
        SNAPSHOT.read_text(encoding="utf-8")
    )

    unknown = [
        r for r in data.get("rows", [])
        if r.get("group") == "unknown"
    ]

    models = {}
    categories = {
        "cpu_only": 0,
        "gpu_only": 0,
        "both": 0,
        "unclassified": 0,
    }

    for offer in unknown:
        cpu = normalize_cpu(offer.get("cpu"))
        gpu = normalize_gpu(offer.get("gpu"))

        missing = []

        if cpu and cpu not in CPU_VALUES:
            missing.append(("CPU", cpu))

        if gpu and gpu not in GPU_VALUES:
            missing.append(("GPU", gpu))

        if len(missing) == 2:
            categories["both"] += 1
        elif len(missing) == 1:
            categories[
                "cpu_only" if missing[0][0] == "CPU"
                else "gpu_only"
            ] += 1
        else:
            categories["unclassified"] += 1

        for kind, model in missing:
            key = (kind, model)

            if key not in models:
                models[key] = {
                    "kind": kind,
                    "model": model,
                    "affected": 0,
                    "unlock_alone": 0,
                    "examples": [],
                    "variant_review": (
                        (kind == "GPU" and model in VARIANT_GPU)
                        or
                        (kind == "CPU" and model in REVIEW_CPU)
                    ),
                }

            item = models[key]
            item["affected"] += 1

            if len(missing) == 1:
                item["unlock_alone"] += 1

            if len(item["examples"]) < 3:
                item["examples"].append({
                    "title": offer.get("title") or "",
                    "price": offer.get("purchase_zl"),
                    "url": safe_url(offer.get("url")),
                })

    ranked = sorted(
        models.values(),
        key=lambda r: (
            -r["unlock_alone"],
            -r["affected"],
            r["kind"],
            r["model"],
        )
    )

    return {
        "generated": data.get("generated_utc", ""),
        "unknown_total": len(unknown),
        "categories": categories,
        "models": ranked,
        "cpu_models": sum(
            x["kind"] == "CPU" for x in ranked
        ),
        "gpu_models": sum(
            x["kind"] == "GPU" for x in ranked
        ),
    }
