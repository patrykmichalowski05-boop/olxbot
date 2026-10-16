import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv("/opt/olx-bot/.env")

client = None


def get_client():
    global client
    if client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("Odzyskiwanie specyfikacji AI nie jest skonfigurowane")
        client = OpenAI(api_key=key)
    return client

MODEL = os.getenv(
    "OPENAI_SPEC_MODEL",
    "gpt-6-luna"
)

MIN_CONFIDENCE = 0.75


def clean_text(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def evidence_exists(source, evidence):
    """
    AI musi podać dokładny fragment tekstu,
    na podstawie którego rozpoznało podzespół.

    Jeżeli fragmentu nie ma w ogłoszeniu,
    nie ufamy wynikowi.
    """

    source = clean_text(
        source
    ).lower()

    evidence = clean_text(
        evidence
    ).lower()

    if len(evidence) < 2:
        return False

    return evidence in source


def missing_specs(details):

    missing = []

    if not details.get("cpu"):
        missing.append("cpu")

    if not details.get("gpu"):
        missing.append("gpu")

    ram = details.get("ram")

    if (
        ram is None
        or
        ram == 0
    ):
        missing.append("ram")

    return missing


def recover_missing_specs(details):

    missing = missing_specs(
        details
    )

    if not missing:

        return {
            "ok": True,
            "used_ai": False,
            "details": details,
            "filled": [],
            "rejected": []
        }

    title = clean_text(
        details.get("title")
    )

    description = clean_text(
        details.get("description")
    )

    # Nie wysyłamy ogromnego tekstu.
    description = description[:6000]

    source_text = (
        f"{title}\n{description}"
    )

    if len(
        clean_text(source_text)
    ) < 3:

        return {
            "ok": False,
            "used_ai": False,
            "details": details,
            "filled": [],
            "rejected": [],
            "reason":
                "Brak tekstu do analizy"
        }

    prompt = f"""
Jesteś parserem specyfikacji używanego komputera
z ogłoszenia OLX.

Twoim zadaniem jest WYŁĄCZNIE odnalezienie
jawnie podanych parametrów sprzętu.

NIE WOLNO:
- zgadywać modelu CPU,
- zgadywać modelu GPU,
- wnioskować RAM z innych parametrów,
- zakładać konfiguracji na podstawie nazwy komputera,
- uzupełniać czegoś, czego nie ma w tekście.

Jeżeli informacji nie ma, zwróć null.

Normalizuj nazwy:

"r5 5600"
→ "Ryzen 5 5600"

"5600x"
jeżeli tekst jasno mówi o Ryzen
→ "Ryzen 5 5600X"

"i5 10400f"
→ "i5-10400F"

"3060ti"
→ "RTX 3060 Ti"

"rx6650xt"
→ "RX 6650 XT"

RAM podaj jako samą liczbę GB.

Dla KAŻDEGO rozpoznanego parametru podaj również
krótki DOKŁADNY cytat z ogłoszenia będący dowodem.
Nie parafrazuj cytatu.

TYTUŁ:
{title}

OPIS:
{description}

Zwróć JSON zgodny ze schematem.
"""

    schema = {
        "type": "object",
        "properties": {
            "cpu": {
                "type": [
                    "string",
                    "null"
                ]
            },
            "cpu_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "cpu_evidence": {
                "type": "string"
            },

            "gpu": {
                "type": [
                    "string",
                    "null"
                ]
            },
            "gpu_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "gpu_evidence": {
                "type": "string"
            },

            "ram_gb": {
                "type": [
                    "integer",
                    "null"
                ]
            },
            "ram_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "ram_evidence": {
                "type": "string"
            },

            "notes": {
                "type": "string"
            }
        },

        "required": [
            "cpu",
            "cpu_confidence",
            "cpu_evidence",

            "gpu",
            "gpu_confidence",
            "gpu_evidence",

            "ram_gb",
            "ram_confidence",
            "ram_evidence",

            "notes"
        ],

        "additionalProperties": False
    }

    try:

        response = get_client().responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "pc_specification",
                    "strict": True,
                    "schema": schema
                }
            }
        )

        result = json.loads(
            response.output_text
        )

    except Exception as e:

        return {
            "ok": False,
            "used_ai": True,
            "details": details,
            "filled": [],
            "rejected": [],
            "reason": str(e)
        }

    new_details = dict(
        details
    )

    filled = []
    rejected = []

    # ======================================
    # CPU
    # ======================================

    if not new_details.get("cpu"):

        cpu = result.get("cpu")

        confidence = float(
            result.get(
                "cpu_confidence",
                0
            )
        )

        evidence = result.get(
            "cpu_evidence",
            ""
        )

        if (
            cpu
            and
            confidence >= MIN_CONFIDENCE
            and
            evidence_exists(
                source_text,
                evidence
            )
        ):

            new_details["cpu"] = (
                clean_text(cpu)
            )

            filled.append({
                "field": "cpu",
                "value": new_details["cpu"],
                "confidence": confidence,
                "evidence": evidence
            })

        elif cpu:

            rejected.append({
                "field": "cpu",
                "value": cpu,
                "confidence": confidence,
                "evidence": evidence
            })

    # ======================================
    # GPU
    # ======================================

    if not new_details.get("gpu"):

        gpu = result.get("gpu")

        confidence = float(
            result.get(
                "gpu_confidence",
                0
            )
        )

        evidence = result.get(
            "gpu_evidence",
            ""
        )

        if (
            gpu
            and
            confidence >= MIN_CONFIDENCE
            and
            evidence_exists(
                source_text,
                evidence
            )
        ):

            new_details["gpu"] = (
                clean_text(gpu)
            )

            filled.append({
                "field": "gpu",
                "value": new_details["gpu"],
                "confidence": confidence,
                "evidence": evidence
            })

        elif gpu:

            rejected.append({
                "field": "gpu",
                "value": gpu,
                "confidence": confidence,
                "evidence": evidence
            })

    # ======================================
    # RAM
    # ======================================

    current_ram = new_details.get(
        "ram"
    )

    if (
        current_ram is None
        or
        current_ram == 0
    ):

        ram = result.get(
            "ram_gb"
        )

        confidence = float(
            result.get(
                "ram_confidence",
                0
            )
        )

        evidence = result.get(
            "ram_evidence",
            ""
        )

        ram_valid = (
            isinstance(ram, int)
            and
            1 <= ram <= 512
        )

        if (
            ram_valid
            and
            confidence >= MIN_CONFIDENCE
            and
            evidence_exists(
                source_text,
                evidence
            )
        ):

            new_details["ram"] = ram

            filled.append({
                "field": "ram",
                "value": ram,
                "confidence": confidence,
                "evidence": evidence
            })

        elif ram is not None:

            rejected.append({
                "field": "ram",
                "value": ram,
                "confidence": confidence,
                "evidence": evidence
            })

    return {
        "ok": True,
        "used_ai": True,
        "details": new_details,
        "filled": filled,
        "rejected": rejected,
        "notes": result.get(
            "notes",
            ""
        )
    }
