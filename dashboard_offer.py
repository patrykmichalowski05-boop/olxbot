import json
import sqlite3

from flask import (
    Blueprint,
    abort,
    render_template_string,
)

from purchase_checklist import (
    get_checklist,
    calculate_adjustment,
)

from seller_questions import (
    build_questions,
    build_message,
)

from deal_crm import (
    ensure_deal,
    status_for_offer,
)

from crm_followup import (
    active_for_offer,
)

from crm_history import (
    history_for_offer,
)

from pickup_checklist import (
    get_checklist as get_pickup_checklist,
    readiness as pickup_readiness,
)

from sale_prep import (
    summary as sale_prep_summary,
)

from listing_generator import (
    build_listing,
)

from sale_pricing import (
    calculate_sale_prices,
)

from sale_listing_tracker import (
    get_listing,
    price_advice,
    price_history,
)

from negotiation_helper import (
    calculate_negotiation,
)

from negotiation_message import (
    build_negotiation_message,
)

from negotiation_variants import (
    build_variants,
)


offer_bp = Blueprint(
    "offer_dashboard",
    __name__,
)


ALERT_DB = "/opt/olx-bot/alert_history.db"

SNAPSHOT_DB = (
    "/opt/olx-bot/"
    "offer_snapshots.db"
)


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    if value is None:
        return "-"

    try:
        value = int(
            round(
                float(value)
            )
        )

        return (
            f"{value:,}"
            .replace(",", " ")
            + " zł"
        )

    except Exception:
        return "-"


def load_json(value):
    try:
        return json.loads(
            value or "{}"
        )
    except Exception:
        return {}


HTML = """
<!doctype html>

<html lang="pl">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>{{ alert.title }}</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0b0e12;
    color: #edf1f5;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 1250px;
    margin: auto;
    padding: 24px;
}

a {
    color: #75baff;
    text-decoration: none;
}

.top {
    display: flex;
    justify-content: space-between;
    gap: 20px;
}

.card {
    margin-top: 20px;
    padding: 20px;
    background: #171c22;
    border: 1px solid #29313a;
    border-radius: 15px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(175px, 1fr)
        );
    gap: 12px;
}

.metric {
    background: #10151a;
    border-radius: 10px;
    padding: 14px;
}

.label {
    color: #89949f;
    font-size: 12px;
}

.value {
    margin-top: 6px;
    font-size: 22px;
    font-weight: bold;
}

.good {
    color: #68db91;
}

.warn {
    color: #ffd166;
}

.bad {
    color: #ff7272;
}

.action {
    font-size: 30px;
    font-weight: bold;
}

ul {
    line-height: 1.7;
}

.message {
    white-space: pre-wrap;
    background: #10151a;
    border-radius: 10px;
    padding: 15px;
}

button {
    border: 0;
    background: #2563eb;
    color: white;
    border-radius: 8px;
    padding: 9px 13px;
    margin-top: 10px;
    cursor: pointer;
}

table {
    width: 100%;
    border-collapse: collapse;
}

td,
th {
    padding: 10px;
    border-bottom: 1px solid #29313a;
    text-align: left;
}

th {
    color: #89949f;
    font-size: 12px;
}

@media(max-width:700px) {

    .container {
        padding: 12px;
    }

    .top {
        display: block;
    }

}

</style>

</head>


<body>

<div class="container">


<div class="top">

<div>

<h1>
{{ alert.title }}
</h1>

<div class="label">
Alert #{{ alert.id }}
</div>

</div>


<div>

<a href="/control">
← Control Center
</a>

&nbsp; | &nbsp;

{% if alert.url %}

<a
    href="{{ alert.url }}"
    target="_blank"
>
OLX
</a>

{% endif %}

</div>

</div>


<div class="card">

{% if action.get('label') %}

<div class="
action
{% if action.get('action') == 'BUY_NOW' %}
bad
{% elif action.get('action') == 'BUY' %}
good
{% elif action.get('action') == 'NEGOTIATE' %}
warn
{% endif %}
">

{{ action.get('label') }}

</div>

{% endif %}


<div class="grid">


<div class="metric">

<div class="label">
Deal Score
</div>

<div class="value">
{{ alert.score or "-" }}/100
</div>

</div>


<div class="metric">

<div class="label">
Cena OLX
</div>

<div class="value">
{{ money(alert.price) }}
</div>

</div>


<div class="metric">

<div class="label">
Quick Sale
</div>

<div class="value">
{{ money(valuation.get('quick_sale')) }}
</div>

</div>


<div class="metric">

<div class="label">
Zysk
</div>

<div class="value good">
{{ money(valuation.get('profit')) }}
</div>

</div>


<div class="metric">

<div class="label">
ROI
</div>

<div class="value">

{% if action.get('roi') is not none %}

{{ "%.1f"|format(action.get('roi')) }}%

{% elif alert.roi is not none %}

{{ "%.1f"|format(alert.roi) }}%

{% else %}

-

{% endif %}

</div>

</div>


<div class="metric">

<div class="label">
MAX BUY
</div>

<div class="value good">
{{ money(adjusted_max_buy) }}
</div>

</div>


<div class="metric">

<div class="label">
Start negocjacji
</div>

<div class="value warn">
{{ money(adjusted_opening) }}
</div>

</div>


<div class="metric">

<div class="label">
Cel zysku
</div>

<div class="value">
{{ money(action.get('target_profit')) }}
</div>

</div>


</div>

</div>


{% if details %}

<div class="card">

<h2>
🖥 Specyfikacja
</h2>

<div class="grid">

<div class="metric">
<div class="label">CPU</div>
<div class="value">
{{ details.get('cpu') or "-" }}
</div>
</div>

<div class="metric">
<div class="label">GPU</div>
<div class="value">
{{ details.get('gpu') or "-" }}
</div>
</div>

<div class="metric">
<div class="label">RAM</div>
<div class="value">

{% if details.get('ram') %}
{{ details.get('ram') }} GB
{% else %}
-
{% endif %}

</div>
</div>

<div class="metric">
<div class="label">Dyski</div>
<div class="value">

{% if details.get('disks') %}

{% for disk in details.get('disks') %}
{{ disk }}
{% if not loop.last %}
<br>
{% endif %}
{% endfor %}

{% else %}
-
{% endif %}

</div>
</div>

</div>

</div>

{% endif %}


<div class="card">

<h2>
📊 Wiarygodność wyceny
</h2>

<table>

<tr>
<td>Źródło</td>
<td>
{{ valuation.get('valuation_source') or "-" }}
</td>
</tr>

<tr>
<td>Pewność</td>
<td>
{{ valuation.get('confidence') or "-" }}
</td>
</tr>

<tr>
<td>Identyczne oferty</td>
<td>
{{ valuation.get('exact_samples') or "-" }}
</td>
</tr>

<tr>
<td>Podobne oferty</td>
<td>
{{ valuation.get('similar_samples') or "-" }}
</td>
</tr>

<tr>
<td>Podobne GPU</td>
<td>
{{ valuation.get('neighbor_samples') or "-" }}
</td>
</tr>

<tr>
<td>Próbki rynku</td>
<td>
{{ valuation.get('market_samples') or "-" }}
</td>
</tr>

</table>

</div>


<div class="card">

<h2>
🤖 AI — stan i ryzyko
</h2>

<div class="grid">

<div class="metric">

<div class="label">
Stan
</div>

<div class="value">
{{ valuation.get('ai_condition') or "-" }}
</div>

</div>


<div class="metric">

<div class="label">
Korekta wyceny
</div>

<div class="value">

{% if valuation.get('ai_adjustment_percent') is not none %}

{{ valuation.get('ai_adjustment_percent') }}%

{% else %}
-
{% endif %}

</div>

</div>

</div>


{% if valuation.get('ai_summary') %}

<h3>
Podsumowanie
</h3>

<p>
{{ valuation.get('ai_summary') }}
</p>

{% endif %}


{% if valuation.get('ai_issues') %}

<h3 class="bad">
Ryzyka
</h3>

<ul>

{% for item in valuation.get('ai_issues') %}

<li>
{{ item }}
</li>

{% endfor %}

</ul>

{% endif %}


{% if valuation.get('ai_missing_info') %}

<h3 class="warn">
Do sprawdzenia u sprzedającego
</h3>

<ul>

{% for item in valuation.get('ai_missing_info') %}

<li>
{{ item }}
</li>

{% endfor %}

</ul>

{% endif %}

</div>


<div class="card">

<h2>
🎯 WARIANTY NEGOCJACJI
</h2>

{% if negotiation_variants %}

<div class="grid">

{% for variant in negotiation_variants %}

<div class="metric">

<div class="label">
{{ variant.label }}
</div>

<div
    class="value"
    style="font-size:28px"
>
{{ "%.0f"|format(
    variant.price
) }} zł
</div>

<br>

<div
    class="message"
    id="variant_{{ loop.index }}"
>{{ variant.message }}</div>

<br>

<button
    type="button"
    onclick="copyVariant(
        'variant_{{ loop.index }}'
    )"
>
📋 KOPIUJ
</button>

<br><br>

<form
    method="post"
    action="/offer/{{ alert.id }}/history/add"
>

<input
    type="hidden"
    name="kind"
    value="MY_OFFER"
>

<input
    type="hidden"
    name="amount"
    value="{{ '%.0f'|format(variant.price) }}"
>

<input
    type="hidden"
    name="note"
    value="Użyłem wariantu {{ variant.label }}"
>

<button
    type="submit"
>
✅ UŻYŁEM TEJ OFERTY
</button>

</form>

</div>

{% endfor %}

</div>

{% else %}

<div class="label">
Brak danych do wyliczenia wariantów.
</div>

{% endif %}

</div>


<div class="card">

<h2>
✉️ WIADOMOŚĆ NEGOCJACYJNA
</h2>

<div
    class="message"
    id="negotiationMessage"
>{{ negotiation_message }}</div>

<br>

<button
    type="button"
    onclick="copyNegotiationMessage()"
>
📋 KOPIUJ WIADOMOŚĆ
</button>

</div>


<div class="card">

<h2>
💬 HISTORIA NEGOCJACJI
</h2>


<form
    method="post"
    action="/offer/{{ alert.id }}/history/add"
>

<select name="kind">

<option value="NOTE">
📝 Notatka
</option>

<option value="MESSAGE">
💬 Wiadomość
</option>

<option value="MY_OFFER">
💰 Moja oferta
</option>

<option value="SELLER_OFFER">
🏷 Oferta sprzedającego
</option>

</select>


<input
    type="number"
    name="amount"
    step="1"
    placeholder="Cena (opcjonalnie)"
>


<input
    type="text"
    name="note"
    placeholder="Treść / notatka..."
    style="
        padding:8px;
        width:350px;
        background:#10151a;
        color:white;
        border:1px solid #303841;
        border-radius:7px;
    "
>


<button type="submit">
DODAJ
</button>

</form>


<br>


{% if deal_history %}

<table>

<tr>
<th>Data</th>
<th>Typ</th>
<th>Cena</th>
<th>Notatka</th>
</tr>


{% for h in deal_history %}

<tr>

<td>
{{ h.created_at }}
</td>


<td>

{% if h.kind == "MY_OFFER" %}
💰 MOJA OFERTA

{% elif h.kind == "SELLER_OFFER" %}
🏷 SPRZEDAJĄCY

{% elif h.kind == "MESSAGE" %}
💬 WIADOMOŚĆ

{% else %}
📝 NOTATKA

{% endif %}

</td>


<td>

{% if h.amount %}
{{ "%.0f"|format(h.amount) }} zł
{% else %}
-
{% endif %}

</td>


<td>
{{ h.note or "-" }}
</td>

</tr>

{% endfor %}

</table>


{% else %}

<div class="label">
Brak historii dla tej oferty.
</div>

{% endif %}

</div>


<div class="card">

<h2>
⏰ FOLLOW-UP CRM
</h2>

{% if active_followup %}

<div class="metric">

<div class="label">
Zaplanowany kontakt
</div>

<div class="value warn">
{{ active_followup.due_at }}
</div>

{% if active_followup.note %}

<p>
{{ active_followup.note }}
</p>

{% endif %}

</div>

{% else %}

<div class="label">
Brak aktywnego przypomnienia.
</div>

{% endif %}

<br>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/followup/1h"
>

<input
    type="hidden"
    name="note"
    value="Ponowny kontakt ze sprzedającym"
>

<button type="submit">
ZA 1H
</button>

</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/followup/3h"
>

<input
    type="hidden"
    name="note"
    value="Ponowny kontakt ze sprzedającym"
>

<button type="submit">
ZA 3H
</button>

</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/followup/tomorrow"
>

<input
    type="hidden"
    name="note"
    value="Follow-up następnego dnia"
>

<button type="submit">
JUTRO 09:00
</button>

</form>


<br><br>


<form
    method="post"
    action="/offer/{{ alert.id }}/followup/custom"
>

<input
    type="datetime-local"
    name="due_at"
    required
>

<input
    type="text"
    name="note"
    placeholder="Notatka..."
    style="
        padding:8px;
        width:280px;
        background:#10151a;
        color:white;
        border:1px solid #303841;
        border-radius:7px;
    "
>

<button type="submit">
USTAW
</button>

</form>

</div>


<div class="card">

<h2>
📌 STATUS TRANSAKCJI
</h2>

<div class="value">

{% if crm_status == "NEW" %}
🆕 NOWY

{% elif crm_status == "CONTACTED" %}
💬 KONTAKT

{% elif crm_status == "NEGOTIATING" %}
🤝 NEGOCJACJE

{% elif crm_status == "PICKUP" %}
🚗 DO ODBIORU

{% elif crm_status == "BOUGHT" %}
📦 KUPIONY

{% elif crm_status == "SOLD" %}
💰 SPRZEDANY

{% elif crm_status == "SKIPPED" %}
❌ ODPUSZCZONY

{% else %}
{{ crm_status }}
{% endif %}

</div>

<br>

<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/crm/CONTACTED"
>
<button type="submit">
💬 KONTAKT
</button>
</form>

<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/crm/NEGOTIATING"
>
<button
    type="submit"
    style="background:#8a6a18"
>
🤝 NEGOCJACJE
</button>
</form>

<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/crm/SKIPPED"
>
<button
    type="submit"
    style="background:#963838"
>
❌ ODPUŚĆ
</button>
</form>

</div>


{% if crm_status == "READY_TO_SELL" %}

<div
    class="card"
    style="
        border:2px solid #3d8bfd;
    "
>

<h2>
</h2>


<h3>
TYTUŁ
</h3>

<div
    class="message"
    id="saleTitle"
>{{ sale_listing.title }}</div>

<br>

<button
    type="button"
    onclick="copySaleText('saleTitle')"
>
</button>


<br><br>


<h3>
OLX
</h3>

<div
    class="message"
    id="saleOlx"
    style="
        white-space:pre-wrap;
    "
>{{ sale_listing.olx }}</div>

<br>

<button
    type="button"
    onclick="copySaleText('saleOlx')"
>
</button>


<br><br>


<h3>
FACEBOOK
</h3>

<div
    class="message"
    id="saleFacebook"
    style="
        white-space:pre-wrap;
    "
>{{ sale_listing.facebook }}</div>

<br>

<button
    type="button"
    onclick="copySaleText('saleFacebook')"
>
</button>

</div>

{% endif %}


{% if crm_status in [
    "BOUGHT",
    "PREPARING",
    "READY_TO_SELL",
    "LISTED"
] %}

<div
    class="card"
    style="
        border:2px solid #238636;
    "
>

<h2>
🔧 PRZYGOTOWANIE DO SPRZEDAŻY
</h2>


<div class="grid">

<div class="metric">
<div class="label">
CENA ZAKUPU
</div>
<div class="value">
{{ "%.0f"|format(
    sale_prep.purchase_price
) }} zł
</div>
</div>


<div class="metric">
<div class="label">
KOSZTY PRZY ZAKUPIE
</div>
<div class="value">
{{ "%.0f"|format(
    sale_prep.purchase_extra
) }} zł
</div>
</div>


<div class="metric">
<div class="label">
PRZYGOTOWANIE
</div>
<div class="value warn">
{{ "%.0f"|format(
    sale_prep.prep_cost
) }} zł
</div>
</div>


<div class="metric">
<div class="label">
ŁĄCZNY KOSZT
</div>
<div class="value">
{{ "%.0f"|format(
    sale_prep.total_investment
) }} zł
</div>
</div>


<div class="metric">
<div class="label">
CENA WYSTAWIENIA
</div>
<div class="value good">

{% if sale_prep.target_price is not none %}

{{ "%.0f"|format(
    sale_prep.target_price
) }} zł

{% else %}
-
{% endif %}

</div>
</div>


<div class="metric">
<div class="label">
PROGNOZOWANY ZYSK
</div>
<div class="value good">

{% if sale_prep.projected_profit is not none %}

{{ "%.0f"|format(
    sale_prep.projected_profit
) }} zł

{% else %}
-
{% endif %}

</div>
</div>

</div>


<br>

<h3>
💸 DODAJ KOSZT
</h3>

<form
    method="post"
    action="/offer/{{ alert.id }}/prep/cost"
>

<select name="kind">

<option value="SSD">SSD</option>
<option value="RAM">RAM</option>
<option value="CASE">Obudowa</option>
<option value="PASTE">Pasta</option>
<option value="CLEANING">Czyszczenie</option>
<option value="REPAIR">Naprawa</option>
<option value="OTHER">Inne</option>

</select>

<input
    type="number"
    name="cost"
    min="0"
    step="1"
    placeholder="Koszt"
    required
>

<input
    type="text"
    name="note"
    placeholder="np. SSD NVMe 1TB"
>

<button type="submit">
DODAJ KOSZT
</button>

</form>


{% if sale_prep.costs %}

<br>

<table>

<tr>
<th>Rodzaj</th>
<th>Koszt</th>
<th>Opis</th>
<th></th>
</tr>

{% for cost in sale_prep.costs %}

<tr>

<td>
{{ cost.kind }}
</td>

<td>
{{ "%.0f"|format(cost.cost) }} zł
</td>

<td>
{{ cost.note or "-" }}
</td>

<td>

<form
    method="post"
    action="/offer/{{ alert.id }}/prep/cost/{{ cost.id }}/delete"
>

<button
    type="submit"
    style="background:#8f3535"
>
USUŃ
</button>

</form>

</td>

</tr>

{% endfor %}

</table>

{% endif %}


<br>

<div
    style="
        padding:18px;
        margin-top:20px;
        margin-bottom:20px;
        border:1px solid #3d8bfd;
        border-radius:10px;
    "
>

<h3>
🧠 REKOMENDACJA CENY
</h3>


<div class="grid">

<div class="metric">

<div class="label">
WYSTAW ZA
</div>

<div
    class="value good"
    style="font-size:30px"
>
{{ "%.0f"|format(
    sale_price_recommendation.target_price
) }} zł
</div>

</div>


<div class="metric">

<div class="label">
MINIMUM
</div>

<div class="value warn">
{{ "%.0f"|format(
    sale_price_recommendation.minimum_price
) }} zł
</div>

</div>


<div class="metric">

<div class="label">
ZYSK DOCELOWY
</div>

<div class="value good">
{{ "%.0f"|format(
    sale_price_recommendation.target_profit
) }} zł
</div>

</div>


<div class="metric">

<div class="label">
ZYSK PRZY MINIMUM
</div>

<div class="value">
{{ "%.0f"|format(
    sale_price_recommendation.minimum_profit
) }} zł
</div>

</div>

</div>


{% if sale_price_recommendation.quick_sale %}

<br>

<div class="label">
Wycena QUICK SALE
</div>

<div class="value">
{{ "%.0f"|format(
    sale_price_recommendation.quick_sale
) }} zł
</div>

{% endif %}


{% if sale_price_recommendation.warning %}

<br>

<div class="bad">
⚠️ {{ sale_price_recommendation.warning }}
</div>

{% endif %}


<br>


<form
    method="post"
    action="/offer/{{ alert.id }}/prep/plan"
>

<input
    type="hidden"
    name="target_price"
    value="{{ '%.0f'|format(
        sale_price_recommendation.target_price
    ) }}"
>

<input
    type="hidden"
    name="minimum_price"
    value="{{ '%.0f'|format(
        sale_price_recommendation.minimum_price
    ) }}"
>

<button
    type="submit"
    style="
        background:#238636;
        padding:12px 20px;
    "
>
✅ UŻYJ REKOMENDOWANYCH CEN
</button>

</form>

</div>


<h3>
🏷 PLAN SPRZEDAŻY
</h3>

<form
    method="post"
    action="/offer/{{ alert.id }}/prep/plan"
>

<input
    type="number"
    name="target_price"
    min="1"
    step="1"
    placeholder="Cena wystawienia"
    value="{% if sale_prep.target_price is not none %}{{ '%.0f'|format(sale_prep.target_price) }}{% endif %}"
    required
>

<input
    type="number"
    name="minimum_price"
    min="1"
    step="1"
    placeholder="Minimalna cena"
    value="{% if sale_prep.minimum_price is not none %}{{ '%.0f'|format(sale_prep.minimum_price) }}{% endif %}"
    required
>

<button type="submit">
ZAPISZ PLAN
</button>

</form>


{% if sale_prep.minimum_price is not none %}

<br>

<div class="label">
ZYSK PRZY MINIMALNEJ CENIE
</div>

<div class="value">

{{ "%.0f"|format(
    sale_prep.minimum_profit
) }} zł

</div>

{% endif %}


{% if sale_prep.has_plan %}

<br><br>

<form
    method="post"
    action="/offer/{{ alert.id }}/prep/ready"
>

<button
    type="submit"
    style="
        background:#238636;
        font-size:18px;
        padding:12px 20px;
    "
>
🏷 GOTOWY DO SPRZEDAŻY
</button>

</form>

{% endif %}

</div>

{% endif %}


{% if crm_status == "PICKUP" %}

<div
    class="card"
    style="
        border:2px solid #e3a008;
    "
>

<h2>
🚗 TRYB ODBIORU
</h2>

<div class="label">
Sprawdź komputer przed przekazaniem pieniędzy.
</div>

<br>

<div class="grid">

<div class="metric">
<div class="label">SPRAWDZONE</div>
<div class="value good">
{{ pickup_state.ok }}/{{ pickup_state.total }}
</div>
</div>

<div class="metric">
<div class="label">OCZEKUJĄCE</div>
<div class="value warn">
{{ pickup_state.pending }}
</div>
</div>

<div class="metric">
<div class="label">PROBLEMY</div>
<div class="value bad">
{{ pickup_state.problems }}
</div>
</div>

</div>


<br>


<table>

<tr>
<th>Kontrola</th>
<th>Status</th>
<th>Akcja</th>
</tr>


{% for item in pickup_checklist %}

<tr>

<td>
{{ item.label }}
</td>

<td>

{% if item.status == "OK" %}

<span class="good">
✅ OK
</span>

{% elif item.status == "PROBLEM" %}

<span class="bad">
❌ PROBLEM
</span>

{% else %}

<span class="warn">
⏳ DO SPRAWDZENIA
</span>

{% endif %}

</td>


<td>

<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/pickup/check/{{ item.key }}/OK"
>
<button type="submit">
✅ OK
</button>
</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/pickup/check/{{ item.key }}/PROBLEM"
>
<button
    type="submit"
    style="background:#8f3535"
>
❌ PROBLEM
</button>
</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/pickup/check/{{ item.key }}/PENDING"
>
<button type="submit">
↩ RESET
</button>
</form>

</td>

</tr>

{% endfor %}

</table>


<br>


{% if pickup_state.ready %}

<div class="good">

✅ KOMPUTER PRZESZEDŁ CAŁĄ KONTROLĘ

</div>

<br>

<form
    method="post"
    action="/control/buy/{{ alert.id }}"
>

<div class="label">
Cena zakupu
</div>

<input
    type="number"
    name="purchase_price"
    step="1"
    min="1"
    value="{% if negotiation.seller_offer is not none %}{{ '%.0f'|format(negotiation.seller_offer) }}{% endif %}"
    required
>


<div class="label">
Dodatkowe koszty
</div>

<input
    type="number"
    name="extra_cost"
    step="1"
    min="0"
    value="0"
>


<br><br>

<button
    type="submit"
    style="
        font-size:20px;
        padding:14px 24px;
        background:#238636;
    "
>
✅ WSZYSTKO OK → KUPIONY
</button>

</form>


{% else %}

<div class="warn">

⚠️ Przycisk zakupu pojawi się po oznaczeniu
wszystkich {{ pickup_state.total }} punktów jako OK.

</div>

{% endif %}

</div>

{% endif %}


<div class="card">

<h2>
✅ CHECKLISTA PRZED ZAKUPEM
</h2>

<div class="grid">

<div class="metric">

<div class="label">
Sprawdzone
</div>

<div class="value">
{{ checklist_result.checked }}
/
{{ checklist_result.total }}
</div>

</div>


<div class="metric">

<div class="label">
OK
</div>

<div class="value good">
{{ checklist_result.ok_count }}
</div>

</div>


<div class="metric">

<div class="label">
Brak danych
</div>

<div class="value warn">
{{ checklist_result.missing_count }}
</div>

</div>


<div class="metric">

<div class="label">
Problemy
</div>

<div class="value bad">
{{ checklist_result.problem_count }}
</div>

</div>


<div class="metric">

<div class="label">
Korekta ceny
</div>

<div class="value bad">

{% if checklist_result.penalty > 0 %}

-{{ money(checklist_result.penalty) }}

{% else %}

0 zł

{% endif %}

</div>

</div>


<div class="metric">

<div class="label">
MAX BUY po kontroli
</div>

<div class="value good">
{{ money(adjusted_max_buy) }}
</div>

</div>

</div>


<table>

<tr>
<th>Element</th>
<th>Status</th>
<th>Kara BRAK</th>
<th>Kara PROBLEM</th>
<th>Akcja</th>
</tr>


{% for item in checklist %}

<tr>

<td>
{{ item.label }}
</td>

<td>

{% if item.status == "OK" %}

<span class="good">
<b>OK</b>
</span>

{% elif item.status == "MISSING" %}

<span class="warn">
<b>BRAK</b>
</span>

{% elif item.status == "PROBLEM" %}

<span class="bad">
<b>PROBLEM</b>
</span>

{% else %}

-

{% endif %}

</td>


<td>
-{{ money(item.missing_penalty) }}
</td>


<td>
-{{ money(item.problem_penalty) }}
</td>


<td>

<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/check/{{ item.key }}/OK"
>

<button type="submit">
OK
</button>

</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/check/{{ item.key }}/MISSING"
>

<button
    type="submit"
    style="background:#8a6a18"
>
BRAK
</button>

</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/check/{{ item.key }}/PROBLEM"
>

<button
    type="submit"
    style="background:#963838"
>
PROBLEM
</button>

</form>


<form
    style="display:inline"
    method="post"
    action="/offer/{{ alert.id }}/check/{{ item.key }}/UNKNOWN"
>

<button
    type="submit"
    style="background:#444"
>
RESET
</button>

</form>

</td>

</tr>

{% endfor %}

</table>


{% if checklist_result.problems %}

<h3>
Wpływ na cenę
</h3>

<ul>

{% for problem in checklist_result.problems %}

<li>

{{ problem.label }}

—

{{ problem.status }}

—

<span class="bad">
-{{ money(problem.penalty) }}
</span>

</li>

{% endfor %}

</ul>

{% endif %}

</div>


<div class="card">

<h2>
❓ PYTANIA DO SPRZEDAJĄCEGO
</h2>

{% if seller_questions %}

<div class="label">
Bot wykrył {{ seller_questions|length }}
brakujących informacji.
</div>

<ul>

{% for question in seller_questions %}

<li>
{{ question }}
</li>

{% endfor %}

</ul>

<div
    class="message"
    id="sellerQuestionsMessage"
>{{ seller_message }}</div>

<button
    onclick="copySellerQuestions()"
>
KOPIUJ PYTANIA
</button>

{% else %}

<div class="good">

✅ Wszystkie kluczowe informacje
z checklisty zostały już sprawdzone.

</div>

{% endif %}

</div>


<div class="card">

<h2>
💬 Gotowa wiadomość
</h2>

<div
    class="message"
    id="message"
>Dzień dobry, czy ogłoszenie jest nadal aktualne?

Jeżeli komputer jest w pełni sprawny i zgodny z opisem, mogę zaproponować {{ money(adjusted_opening) }}.

Mogę sprawnie sfinalizować zakup. Jeśli ta kwota jest za niska, proszę dać znać jaka byłaby najniższa możliwa cena.</div>

<button
    onclick="copyMessage()"
>
KOPIUJ WIADOMOŚĆ
</button>

</div>


<div class="card">

<h2>
📉 Historia ceny / analiz
</h2>

<table>

<tr>
<th>Data</th>
<th>Cena</th>
<th>Score</th>
<th>Zysk</th>
<th>Akcja</th>
</tr>


{% for row in snapshots %}

<tr>

<td>
{{ row.created_at }}
</td>

<td>
{{ money(row.price) }}
</td>

<td>
{{ row.score }}
</td>

<td>
{{ money(row.profit) }}
</td>

<td>
{{ row.action }}
</td>

</tr>

{% endfor %}

</table>

</div>


</div>


<script>

function copySaleText(id) {

    const element =
        document.getElementById(id);

    if (!element) {
        return;
    }

    navigator.clipboard.writeText(
        element.innerText
    );
}


function copyVariant(id) {

    const element =
        document.getElementById(id);

    if (!element) {
        return;
    }

    navigator.clipboard.writeText(
        element.innerText
    );
}


function copyNegotiationMessage() {

    const element =
        document.getElementById(
            "negotiationMessage"
        );

    if (!element) {
        return;
    }

    navigator.clipboard.writeText(
        element.innerText
    );
}


function copySellerQuestions() {

    const element =
        document.getElementById(
            "sellerQuestionsMessage"
        );

    if (!element) {
        return;
    }

    navigator.clipboard.writeText(
        element.innerText
    );
}


function copyMessage() {

    navigator.clipboard.writeText(
        document
            .getElementById("message")
            .innerText
    );

}

</script>

</body>

</html>
"""


@offer_bp.route(
    "/offer/<int:alert_id>"
)
def offer_details(alert_id):

    conn = connect(
        ALERT_DB
    )

    alert = conn.execute("""
        SELECT *
        FROM alerts
        WHERE id = ?
    """, (
        alert_id,
    )).fetchone()

    conn.close()

    if alert is None:
        abort(404)


    details = {}
    valuation = {}
    action = {}
    snapshots = []


    try:

        conn = connect(
            SNAPSHOT_DB
        )

        rows = conn.execute("""
            SELECT *
            FROM snapshots

            WHERE offer_key = ?

            ORDER BY id DESC
        """, (
            alert[
                "offer_key"
            ],
        )).fetchall()

        conn.close()


        if rows:

            latest = rows[0]

            details = load_json(
                latest[
                    "details_json"
                ]
            )

            valuation = load_json(
                latest[
                    "valuation_json"
                ]
            )

            action = load_json(
                latest[
                    "action_json"
                ]
            )


            for row in rows:

                row_action = load_json(
                    row[
                        "action_json"
                    ]
                )

                row_valuation = load_json(
                    row[
                        "valuation_json"
                    ]
                )

                snapshots.append({
                    "created_at":
                        row[
                            "created_at"
                        ],

                    "price":
                        row[
                            "price"
                        ],

                    "score":
                        row[
                            "score"
                        ],

                    "profit":
                        row_valuation.get(
                            "profit"
                        ),

                    "action":
                        row_action.get(
                            "label"
                        )
                        or
                        row_action.get(
                            "action"
                        )
                        or
                        "-",
                })


    except Exception as e:

        print(
            "[OFFER SNAPSHOT ERROR]",
            e,
        )


    # Fallback dla starych alertów
    if not valuation:

        valuation = {
            "quick_sale":
                alert["quick_sale"],

            "profit":
                alert["profit"],
        }


    ensure_deal(
        offer_key=alert["offer_key"],
        alert_id=alert["id"],
        title=alert["title"],
        url=alert["url"],
    )

    crm_status = status_for_offer(
        alert["offer_key"]
    )

    active_followup = active_for_offer(
        alert["offer_key"]
    )

    deal_history = history_for_offer(
        alert["offer_key"]
    )


    pickup_checklist = get_pickup_checklist(
        alert["offer_key"]
    )

    pickup_state = pickup_readiness(
        pickup_checklist
    )


    sale_prep = sale_prep_summary(
        alert["offer_key"],
        alert["id"],
        valuation.get(
            "quick_sale"
        ),
    )


    sale_price_recommendation = (
        calculate_sale_prices(
            sale_prep.get(
                "total_investment"
            ),
            valuation.get(
                "quick_sale"
            ),
        )
    )

    sale_listing = build_listing(
        details,
        sale_prep,
    )


    active_sale_listing = get_listing(
        alert["offer_key"]
    )

    listing_advice = price_advice(
        active_sale_listing,
        sale_prep.get(
            "minimum_price"
        ),
    )


    listing_price_history = price_history(
        alert["offer_key"]
    )


    checklist = get_checklist(
        alert["offer_key"]
    )

    checklist_result = (
        calculate_adjustment(
            action.get(
                "max_buy"
            ),
            alert["price"],
            checklist,
        )
    )


    negotiation = calculate_negotiation(
        deal_history,
        checklist_result.get(
            "adjusted_max_buy"
        ),
        checklist_result.get(
            "adjusted_opening"
        ),
    )


    negotiation_message = (
        build_negotiation_message(
            negotiation
        )
    )


    negotiation_variants = (
        build_variants(
            negotiation,
            checklist_result.get(
                "adjusted_opening"
            ),
        )
    )

    seller_questions = (
        build_questions(
            checklist
        )
    )

    seller_message = (
        build_message(
            checklist
        )
    )


    return render_template_string(
        HTML,

        alert=alert,

        details=details,

        valuation=valuation,

        action=action,

        checklist=checklist,

        checklist_result=
            checklist_result,

        seller_questions=
            seller_questions,

        seller_message=
            seller_message,

        crm_status=
            crm_status,

        active_followup=
            active_followup,

        deal_history=
            deal_history,

        pickup_checklist=
            pickup_checklist,

        pickup_state=
            pickup_state,

        sale_prep=
            sale_prep,

        sale_listing=
            sale_listing,

        active_sale_listing=
            active_sale_listing,

        listing_advice=
            listing_advice,

        listing_price_history=
            listing_price_history,

        sale_price_recommendation=
            sale_price_recommendation,

        negotiation=
            negotiation,

        negotiation_message=
            negotiation_message,

        negotiation_variants=
            negotiation_variants,

        adjusted_max_buy=
            checklist_result[
                "adjusted_max_buy"
            ],

        adjusted_opening=
            checklist_result[
                "adjusted_opening"
            ],

        snapshots=snapshots,

        money=money,
    )
