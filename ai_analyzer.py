import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def parse_json(text):

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"```$",
        "",
        text
    )

    text = text.strip()

    try:
        return json.loads(text)
    except:
        return None


def analyze_offer(details):

    title = details.get("title", "")
    cpu = details.get("cpu", "")
    gpu = details.get("gpu", "")
    ram = details.get("ram", "")
    disks = details.get("disks", [])
    description = str(
        details.get("description", "")
    )[:7000]

    prompt = f"""
Analizujesz używany komputer stacjonarny z OLX
pod kątem zakupu do dalszej odsprzedaży.

NIE podawaj ceny komputera w złotówkach.
Cena rynkowa jest liczona przez market.db.

Masz tylko:
- ocenić stan,
- wykryć ryzyka,
- ocenić opisane podzespoły pomocnicze,
- podać procentową korektę wartości.

Tytuł:
{title}

CPU:
{cpu}

GPU:
{gpu}

RAM:
{ram}

Dyski:
{disks}

Opis:
{description}

Zasady:
- nie wymyślaj brakujących danych,
- brak informacji o PSU nie oznacza złego PSU,
- GPU po kopaniu: zwykle -5 do -12%,
- artefakty / niestabilność GPU: -15 do -35%,
- problemy z temperaturami: -5 do -20%,
- uszkodzenia mechaniczne: -3 do -15%,
- słaby/no-name PSU: -5 do -10%,
- brak SSD: -3 do -6%,
- uszkodzony dysk: -5 do -15%,
- dobry PSU/płyta: maksymalnie +3%,
- normalny sprawny komputer: 0%,
- zakres adjustment_percent: od -40 do +5.

Zwróć WYŁĄCZNIE JSON:

{{
  "condition": "good|normal|risk|bad",
  "adjustment_percent": 0,
  "confidence": 0.0,
  "issues": [],
  "missing_info": [],
  "psu_assessment": "unknown|good|average|poor",
  "summary": "krótkie podsumowanie po polsku"
}}
"""

    try:

        response = client.responses.create(
            model="gpt-6-luna",
            input=prompt
        )

        result = parse_json(
            response.output_text
        )

        if not result:
            return {
                "ok": False,
                "reason": "Niepoprawny JSON AI"
            }

        adjustment = float(
            result.get(
                "adjustment_percent",
                0
            )
        )

        adjustment = max(
            -40,
            min(5, adjustment)
        )

        confidence = float(
            result.get(
                "confidence",
                0
            )
        )

        confidence = max(
            0,
            min(1, confidence)
        )

        return {
            "ok": True,
            "condition": result.get(
                "condition",
                "normal"
            ),
            "adjustment_percent": adjustment,
            "confidence": confidence,
            "issues": result.get(
                "issues",
                []
            ),
            "missing_info": result.get(
                "missing_info",
                []
            ),
            "psu_assessment": result.get(
                "psu_assessment",
                "unknown"
            ),
            "summary": result.get(
                "summary",
                ""
            )
        }

    except Exception as e:

        return {
            "ok": False,
            "reason": str(e)
        }


def apply_ai_adjustment(
    valuation,
    ai_result
):

    if not ai_result.get("ok"):
        return valuation

    adjustment = (
        ai_result.get(
            "adjustment_percent",
            0
        )
        / 100
    )

    before = valuation["quick_sale"]

    after = round(
        before * (1 + adjustment)
    )

    total_cost = (
        valuation["total_cost"]
    )

    profit = (
        after - total_cost
    )

    result = dict(valuation)

    result["quick_sale_before_ai"] = before
    result["quick_sale"] = after
    result["profit"] = profit

    result["profitable"] = (
        profit >= 400
    )

    result["hot"] = (
        profit >= 700
    )

    result["ai_adjustment_percent"] = (
        ai_result.get(
            "adjustment_percent"
        )
    )

    result["ai_condition"] = (
        ai_result.get(
            "condition"
        )
    )

    result["ai_confidence"] = (
        ai_result.get(
            "confidence"
        )
    )

    result["ai_issues"] = (
        ai_result.get(
            "issues",
            []
        )
    )

    result["ai_missing_info"] = (
        ai_result.get(
            "missing_info",
            []
        )
    )

    result["ai_summary"] = (
        ai_result.get(
            "summary",
            ""
        )
    )

    return result
