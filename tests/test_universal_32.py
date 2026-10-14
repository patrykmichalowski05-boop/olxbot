import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from universal_v2.bridge_config import BridgeConfig


class Test32(unittest.TestCase):

    def test_env_requires_separate_directory(self):
        with patch.dict(
            'os.environ',
            {},
            clear=True
        ):
            with self.assertRaises(RuntimeError):
                BridgeConfig.from_env()

        with patch.dict(
            'os.environ',
            {
                'FLIP_API_AUTH_DB': '/tmp/owner.db',
                'FLIP_API_DATA_ROOT': '/tmp',
                'FLIP_UNIVERSAL_DEV_DIR': '/opt/olx-bot/dev',
            },
            clear=True
        ):
            with self.assertRaises(RuntimeError):
                BridgeConfig.from_env()

    def test_manual_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(
                'os.environ',
                {
                    'FLIP_API_AUTH_DB': str(
                        Path(d) / 'auth.db'
                    ),
                    'FLIP_API_DATA_ROOT': d,
                    'FLIP_UNIVERSAL_DEV_DIR': d,
                },
                clear=True
            ):
                self.assertFalse(
                    BridgeConfig.from_env().manual_enabled
                )
