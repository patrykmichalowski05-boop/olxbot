
let page = 1;
let pages = 1;

const $ = id => document.getElementById(id);
const fmt = n => n == null ? "—" :
  Number(n).toLocaleString("pl-PL") + " zł";

function cell(row, value) {
  const td = document.createElement("td");
  td.textContent = value == null || value === "" ? "—" : String(value);
  row.appendChild(td);
  return td;
}

async function loadSummary() {
  const response = await fetch("/flip-radar/api/summary", {
    credentials: "same-origin"
  });
  if (!response.ok) throw new Error("Nie można pobrać statystyk");
  const data = await response.json();

  $("total").textContent = data.total ?? 0;
  $("olx").textContent = data.olx ?? 0;
  $("facebook").textContent = data.facebook ?? 0;
  $("expensive").textContent = data.over_1500 ?? 0;
  $("updated").textContent =
    "Ostatni import danych: " + (data.last_import_utc || "brak");
}

async function loadOffers() {
  const params = new URLSearchParams({
    q: $("query").value,
    source: $("source").value,
    sort: $("sort").value,
    page: String(page)
  });

  const response = await fetch(
    "/flip-radar/api/offers?" + params.toString(),
    {credentials: "same-origin"}
  );

  if (!response.ok) throw new Error("Nie można pobrać ofert");

  const data = await response.json();
  pages = Math.max(1, data.pages);

  const body = $("offers");
  body.replaceChildren();

  for (const item of data.items) {
    const tr = document.createElement("tr");

    const title = cell(tr, "");
    if (item.url) {
      const a = document.createElement("a");
      a.href = item.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = item.title || item.listing_id;
      title.appendChild(a);
    } else {
      title.textContent = item.title || item.listing_id;
    }

    const meta = document.createElement("small");
    meta.textContent = " " + item.source.toUpperCase()
      + " · " + item.listing_id;
    title.appendChild(document.createElement("div"));
    title.appendChild(meta);

    cell(tr, fmt(item.price_zl));
    cell(tr, (item.cpu || "CPU nieznany") + " / "
      + (item.gpu || "GPU nieznane"));
    cell(tr, item.ram_gb == null ? "—" : item.ram_gb + " GB");
    cell(tr, fmt(item.minimum_resale_needed_zl));
    cell(tr, item.technical_review ||
      item.detail_status || item.status || "Do sprawdzenia");

    body.appendChild(tr);
  }

  $("info").textContent = "Znaleziono ofert: " + data.total;
  $("paging").textContent = "Strona " + page + " z " + pages;
  $("previous").disabled = page <= 1;
  $("next").disabled = page >= pages;
}

$("filters").addEventListener("submit", async event => {
  event.preventDefault();
  page = 1;
  try { await loadOffers(); }
  catch (error) { $("info").textContent = error.message; }
});

$("previous").addEventListener("click", async () => {
  if (page > 1) { page--; await loadOffers(); }
});

$("next").addEventListener("click", async () => {
  if (page < pages) { page++; await loadOffers(); }
});

Promise.all([loadSummary(), loadOffers()]).catch(error => {
  $("info").textContent = error.message;
});
