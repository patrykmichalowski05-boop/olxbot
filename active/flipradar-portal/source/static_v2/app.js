(function () {
    var sidebar = document.getElementById('sidebar');
    var toggle = document.querySelector('[data-menu-toggle]');
    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
        });
    }

    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (event) {
            if (!window.confirm(el.getAttribute('data-confirm'))) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll('[data-copy-text]').forEach(function (button) {
        button.addEventListener('click', function () {
            var text = button.getAttribute('data-copy-text') || '';
            navigator.clipboard.writeText(text).then(function () {
                var old = button.textContent;
                button.textContent = 'Skopiowano';
                window.setTimeout(function () { button.textContent = old; }, 1200);
            }).catch(function () {});
        });
    });

    document.querySelectorAll('.clickable-row[data-href]').forEach(function (row) {
        row.addEventListener('click', function (event) {
            if (event.target.closest('a, button, input, select, form')) return;
            window.location.href = row.getAttribute('data-href');
        });
    });

    var healthPill = document.querySelector('[data-health-pill]');
    if (healthPill) {
        var interval = Math.max(5, Number(document.body.dataset.refresh || 15)) * 1000;
        window.setInterval(function () {
            fetch('/api/health', {headers: {'Accept': 'application/json'}})
                .then(function (response) { return response.ok ? response.json() : null; })
                .then(function (data) {
                    if (!data) return;
                    healthPill.textContent = data.status + ' · ' + data.score + '/100';
                    healthPill.className = 'status-pill status-' + String(data.status || 'unknown').toLowerCase();
                    healthPill.setAttribute('data-health-pill', '');
                })
                .catch(function () {});
        }, interval);
    }
})();

// Flip Hunter V2 - aktualizacja dashboardu bez F5.
(function () {
    function startLiveDashboard() {
        const tbody = document.querySelector('[data-live-offers]');
        if (!tbody) return;

        const state = document.querySelector('[data-live-state]');
        let loading = false;
        let lastOffers = '';

        const money = value => {
            if (value === null || value === undefined ||
                value === '' || !Number.isFinite(Number(value))) {
                return '—';
            }
            return new Intl.NumberFormat('pl-PL', {
                maximumFractionDigits: 0
            }).format(Number(value)) + ' zł';
        };

        const valueOf = (obj, path) => {
            return path.split('.').reduce(
                (current, key) => current == null ? undefined : current[key],
                obj
            );
        };

        function refreshCounters(data) {
            document.querySelectorAll('[data-live]').forEach(el => {
                const key = el.dataset.live;
                let value = valueOf(data, key);

                if (value === undefined || value === null) return;

                if ([
                    'realized_profit',
                    'inventory.stats.capital',
                    'inventory.stats.potential_profit'
                ].includes(key)) {
                    value = money(value);
                }

                el.textContent = String(value);

                if (key === 'queue.failed') {
                    el.classList.toggle('danger-text', Number(value) > 0);
                }
            });
        }

        function addCell(row, value, className) {
            const td = document.createElement('td');
            td.textContent = value == null ? '—' : String(value);
            if (className) td.className = className;
            row.appendChild(td);
            return td;
        }

        function refreshOffers(rawOffers) {
            const offers = (Array.isArray(rawOffers) ? rawOffers : [])
                .filter(o => !/^TEST(?:\s+ACTION|[_ -])/i.test(
                    String(o.title || '')
                ))
                .filter(o => !/IDTESTACTION/i.test(String(o.url || '')));

            const fingerprint = JSON.stringify(offers);
            if (fingerprint === lastOffers) return;

            const fragment = document.createDocumentFragment();

            offers.forEach(o => {
                if (o.id === undefined || o.id === null) return;

                const tr = document.createElement('tr');
                tr.className = 'clickable-row';

                const href = '/offer/' + encodeURIComponent(o.id);
                tr.dataset.href = href;
                tr.addEventListener('click', event => {
                    if (event.target.closest('a, button, input, select, form')) return;
                    window.location.href = href;
                });

                const score = Number(o.score) || 0;
                const scoreTd = addCell(tr, '');
                const scoreSpan = document.createElement('span');
                scoreSpan.className = 'score score-' +
                    (score >= 85 ? 'hot' : score >= 75 ? 'good' : 'mid');
                scoreSpan.textContent = String(score);
                scoreTd.appendChild(scoreSpan);

                const titleTd = addCell(tr, '');
                const title = document.createElement('strong');
                title.textContent = String(o.title || 'Bez nazwy');
                titleTd.appendChild(title);

                const date = document.createElement('div');
                date.className = 'subtle';
                date.textContent = String(o.created_at || '');
                titleTd.appendChild(date);

                const sourceTd = addCell(tr, '');
                const source = document.createElement('span');
                const sourceName = String(o.source || 'OLX');
                source.className = 'source source-' +
                    sourceName.toLowerCase().replace(/[^a-z0-9_-]/g, '');
                source.textContent = sourceName;
                sourceTd.appendChild(source);

                addCell(tr, money(o.price));

                const suspicious = Number(o.price) > 0 &&
                    Number(o.quick_sale) >= 2 * Number(o.price);

                const quickTd = addCell(tr, money(o.quick_sale));

                if (suspicious) {
                    const warning = document.createElement('div');
                    warning.className = 'subtle';
                    warning.textContent = '⚠ Wycena do ponownej weryfikacji';
                    quickTd.appendChild(warning);
                }

                const profitTd = addCell(
                    tr,
                    suspicious ? 'Do weryfikacji' : money(o.profit),
                    suspicious ? 'subtle' : 'profit'
                );

                if (suspicious) {
                    profitTd.title = 'Historyczny wynik alertu, niepotwierdzony aktualna wycena';
                }

                const decisionTd = addCell(tr, '');
                const decision = document.createElement('span');
                const action = String(o.decision || 'WATCH');
                decision.className = 'decision decision-' +
                    action.toLowerCase().replace(/[^a-z0-9_-]/g, '');
                decision.textContent = action;
                decisionTd.appendChild(decision);

                fragment.appendChild(tr);
            });

            if (!fragment.childNodes.length) {
                const tr = document.createElement('tr');
                const td = addCell(tr, 'Brak rzeczywistych alertów.', 'empty');
                td.colSpan = 7;
                fragment.appendChild(tr);
            }

            tbody.replaceChildren(fragment);
            lastOffers = fingerprint;
        }

        async function update() {
            if (loading || document.hidden) return;
            loading = true;

            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 8000);

            try {
                const response = await fetch('/api/overview', {
                    credentials: 'same-origin',
                    cache: 'no-store',
                    signal: controller.signal,
                    headers: {'Accept': 'application/json'}
                });

                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }

                const data = await response.json();
                refreshCounters(data);
                refreshOffers(data.offers);

                if (state) {
                    state.textContent = 'Aktualizacja: ' +
                        new Date().toLocaleTimeString('pl-PL');
                }
            } catch (error) {
                if (state) state.textContent = 'Brak aktualizacji danych';
            } finally {
                window.clearTimeout(timeout);
                loading = false;
            }
        }

        update();
        window.setInterval(update, 5000);

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) update();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startLiveDashboard, {once: true});
    } else {
        startLiveDashboard();
    }
})();
