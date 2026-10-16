"""Authenticated Flip Hunter V2 with DEV read-only page."""
import sys
from pathlib import Path

from jinja2 import ChoiceLoader, FileSystemLoader

DEV = Path("/opt/olx-bot-budget-dev")
sys.path.insert(0, "/opt/olx-bot")

from webapp_v2 import app

sys.path.insert(0, str(DEV))
from flip_gui_data_dev import get_data

from flask import render_template, request

original_loader = app.jinja_loader
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(str(DEV / "gui_templates_dev")),
    original_loader,
])

@app.get("/dev/flip-hunter")
def flip_hunter_dev():
    from flask import abort
    from app_v2 import config
    from app_v2.security import auth_configured, logged_in

    if not config.AUTH_REQUIRED or not auth_configured():
        abort(503)
    if not logged_in():
        abort(403)

    view = request.args.get("view", "candidates")

    if view not in ("candidates", "incomplete"):
        view = "candidates"

    return render_template(
        "flip_dev.html",
        page="flip_dev",
        data=get_data(),
        view=view,
    )


# FLIPRADAR PRIVATE INVENTORY V1
from personal_inventory_v1 import bp as inventory_bp
app.register_blueprint(inventory_bp)
# FLIPRADAR_PREMIUM_UI_V2
from premium_radar_v2 import bp as premium_radar_bp
from premium_inventory_stats_v2 import private_inventory_stats as _private_stats
app.register_blueprint(premium_radar_bp)
@app.context_processor
def _flipradar_premium_context():
    return {'private_inventory_stats': _private_stats}
# FLIPRADAR_MULTIUSER_V2
from multiuser_v2 import install as _install_flipradar_multiuser_v2
_install_flipradar_multiuser_v2(app)

# FLIPRADAR_USER_ONE_SEARCH_V3
from user_one_search_v3 import install as install_user_v3
install_user_v3(app)

# FLIPRADAR_V4_LIVE_INSTALL
from workspace_v4_live import install as install_v4_live
install_v4_live(app)

# FLIPRADAR_GUI_V5_INSTALL
from flipradar_gui_v5 import install as install_gui_v5
install_gui_v5(app)

# FLIPRADAR_GUIDE_V7_INSTALL
from guide_v7 import install as install_guide_v7
install_guide_v7(app)
# FLIPRADAR_MONITOR_V8_INSTALL
from monitor_v8_web import install as install_monitor_v8
install_monitor_v8(app)

# FLIPRADAR_USER_SEARCH_V9_INSTALL
from flipradar_user_web_v9 import install as install_user_v9
install_user_v9(app)

# FLIPRADAR_ACCOUNTS_V10_INSTALL
from accounts_v10 import install as install_accounts_v10
install_accounts_v10(app)

# FLIPRADAR_UI_V11_INSTALL
from v11_ui import install as install_ui_v11
install_ui_v11(app)
