#!/usr/bin/env python3
"""Unit tests for mkplan helpers."""

from __future__ import annotations

import unittest
from unittest import mock

from ops.plan import mkplan


class MkplanHealthPollingTests(unittest.TestCase):
    @mock.patch("ops.plan.mkplan.time.sleep")
    @mock.patch("ops.plan.mkplan.time.monotonic")
    @mock.patch("ops.plan.mkplan.subprocess.check_output")
    def test_poll_core_container_health_waits_for_healthy(
        self,
        mock_check_output: mock.Mock,
        mock_monotonic: mock.Mock,
        mock_sleep: mock.Mock,
    ) -> None:
        mock_check_output.side_effect = [
            '"starting"\n"starting"\n"starting"\n',
            '"healthy"\n"healthy"\n"healthy"\n',
        ]
        mock_monotonic.side_effect = [0.0, 1.0, 2.0]

        exit_code = mkplan.poll_core_container_health()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_check_output.call_count, 2)
        mock_sleep.assert_called_once_with(mkplan.CORE_HEALTH_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
