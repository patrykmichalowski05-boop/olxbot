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
