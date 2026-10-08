import unittest

from unittest.mock import (
    patch,
)

import watchdog


class TestWatchdogV3(
    unittest.TestCase
):

    def healthy_timer(
        self,
        unit,
    ):

        if unit.endswith(
            ".timer"
        ):

            return "active"

        return "inactive"


    def healthy_market(
        self,
    ):

        return {
            "total": 100,
            "active": 100,
            "inactive": 0,
            "price_changes": 0,
            "last_seen":
                "2026-10-04T12:00:00",
            "age_hours": 1,
        }


    def healthy_queue(
        self,
    ):

        return {
            "pending": 0,
            "processing": 0,
            "done": 10,
            "failed": 0,
            "stale_processing": 0,
        }


    # ========================================================
    # HEALTHY
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_healthy_system(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        mock_state.side_effect = (
            self.healthy_timer
        )

        mock_result.return_value = (
            "success"
        )

        def logs(
            unit,
            since="",
        ):

            if unit == (
                "olx-fast.service"
            ):

                return (
                    "FAST RADAR GOTOWY"
                )

            if unit == (
                "olx-deep.service"
            ):

                return (
                    "DEEP WORKER GOTOWY"
                )

            if unit == (
                "olx-bundle.service"
            ):

                return (
                    "BUNDLE FAST RADAR — KONIEC"
                )

            if unit == (
                "olx-market.service"
            ):

                return (
                    "MARKET COLLECTOR V2 — KONIEC"
                )

            return ""

        mock_logs.side_effect = logs

        mock_queue.return_value = (
            self.healthy_queue()
        )

        mock_market.return_value = (
            self.healthy_market()
        )

        result = watchdog.analyze()

        self.assertEqual(
            result[
                "problems"
            ],
            []
        )

        self.assertEqual(
            result[
                "warnings"
            ],
            []
        )


    # ========================================================
    # TIMER DOWN
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_bundle_timer_down(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        def state(unit):

            if unit == (
                "olx-bundle.timer"
            ):

                return "inactive"

            return "active"

        mock_state.side_effect = state

        mock_result.return_value = (
            "success"
        )

        mock_logs.side_effect = (
            lambda unit, since="":
            (
                "FAST RADAR GOTOWY"
                if unit ==
                "olx-fast.service"
                else
                "DEEP WORKER GOTOWY"
                if unit ==
                "olx-deep.service"
                else
                ""
            )
        )

        mock_queue.return_value = (
            self.healthy_queue()
        )

        mock_market.return_value = (
            self.healthy_market()
        )

        result = watchdog.analyze()

        self.assertTrue(
            any(
                "olx-bundle.timer"
                in problem
                for problem
                in result[
                    "problems"
                ]
            )
        )


    # ========================================================
    # FAST HEARTBEAT
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_missing_fast(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        mock_state.side_effect = (
            self.healthy_timer
        )

        mock_result.return_value = (
            "success"
        )

        def logs(
            unit,
            since="",
        ):

            if unit == (
                "olx-deep.service"
            ):

                return (
                    "DEEP WORKER GOTOWY"
                )

            return ""

        mock_logs.side_effect = logs

        mock_queue.return_value = (
            self.healthy_queue()
        )

        mock_market.return_value = (
            self.healthy_market()
        )

        result = watchdog.analyze()

        self.assertTrue(
            any(
                "FAST RADAR"
                in problem
                for problem
                in result[
                    "problems"
                ]
            )
        )


    # ========================================================
    # QUEUE WARNING
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_queue_warning(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        mock_state.side_effect = (
            self.healthy_timer
        )

        mock_result.return_value = (
            "success"
        )

        def logs(
            unit,
            since="",
        ):

            if unit == (
                "olx-fast.service"
            ):

                return (
                    "FAST RADAR GOTOWY"
                )

            if unit == (
                "olx-deep.service"
            ):

                return (
                    "DEEP WORKER GOTOWY"
                )

            return ""

        mock_logs.side_effect = logs

        queue = (
            self.healthy_queue()
        )

        queue[
            "pending"
        ] = 20

        mock_queue.return_value = queue

        mock_market.return_value = (
            self.healthy_market()
        )

        result = watchdog.analyze()

        self.assertFalse(
            result[
                "problems"
            ]
        )

        self.assertTrue(
            result[
                "warnings"
            ]
        )


    # ========================================================
    # QUEUE ERROR
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_queue_error(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        mock_state.side_effect = (
            self.healthy_timer
        )

        mock_result.return_value = (
            "success"
        )

        def logs(
            unit,
            since="",
        ):

            if unit == (
                "olx-fast.service"
            ):

                return (
                    "FAST RADAR GOTOWY"
                )

            if unit == (
                "olx-deep.service"
            ):

                return (
                    "DEEP WORKER GOTOWY"
                )

            return ""

        mock_logs.side_effect = logs

        queue = (
            self.healthy_queue()
        )

        queue[
            "pending"
        ] = 50

        mock_queue.return_value = queue

        mock_market.return_value = (
            self.healthy_market()
        )

        result = watchdog.analyze()

        self.assertTrue(
            result[
                "problems"
            ]
        )


    # ========================================================
    # MARKET STALE
    # ========================================================

    @patch(
        "watchdog.market_stats"
    )
    @patch(
        "watchdog.queue_stats"
    )
    @patch(
        "watchdog.get_logs"
    )
    @patch(
        "watchdog.service_result"
    )
    @patch(
        "watchdog.system_state"
    )
    def test_market_stale(
        self,
        mock_state,
        mock_result,
        mock_logs,
        mock_queue,
        mock_market,
    ):

        mock_state.side_effect = (
            self.healthy_timer
        )

        mock_result.return_value = (
            "success"
        )

        def logs(
            unit,
            since="",
        ):

            if unit == (
                "olx-fast.service"
            ):

                return (
                    "FAST RADAR GOTOWY"
                )

            if unit == (
                "olx-deep.service"
            ):

                return (
                    "DEEP WORKER GOTOWY"
                )

            return ""

        mock_logs.side_effect = logs

        mock_queue.return_value = (
            self.healthy_queue()
        )

        market = (
            self.healthy_market()
        )

        market[
            "age_hours"
        ] = 50

        mock_market.return_value = market

        result = watchdog.analyze()

        self.assertTrue(
            any(
                "MARKET DB"
                in problem
                for problem
                in result[
                    "problems"
                ]
            )
        )


if __name__ == "__main__":

    unittest.main(
        verbosity=2
    )
