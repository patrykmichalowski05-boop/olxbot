import json

from .smoke import run as smoke
from .integration_status import catalog


def report():
    check = smoke()

    return {
        'offline_smoke': check['status'],
        'offline_decision': check['decision'],

        'platforms_automatic': sum(
            x.auto_discovery_available
            for x in catalog()
        ),

        'iphone_e2e_verified': False,
        'android_e2e_verified': False,
        'production_https_verified': False,
        'subscriptions_ready': False,
        'production_ready': False
    }


if __name__ == '__main__':
    print(
        json.dumps(
            report(),
            indent=2,
            ensure_ascii=False
        )
    )
