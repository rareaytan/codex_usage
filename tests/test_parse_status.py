import unittest

from codex_tmux_status_watch import parse_status, status_needs_limit_refresh


class ParseStatusTest(unittest.TestCase):
    def test_keeps_primary_limits_when_pro_status_includes_spark_limits(self):
        text = """
│  Account:                     rareay.tan@gmail.com (Plus)                    │
│                                                                              │
│  5h limit:                    [█████████████████░░░] 86% left (resets 20:53) │
│  Weekly limit:                [██████████████████░░] 92% left                │
│                               (resets 10:53 on 7 Jul)                        │
│  GPT-5.3-Codex-Spark limit:                                                  │
│  5h limit:                    [████████████████████] 100% left               │
│                               (resets 22:06)                                 │
│  Weekly limit:                [████████████████████] 100% left               │
│                               (resets 17:06 on 7 Jul)                        │
"""

        status = parse_status(text)

        self.assertEqual(status["limit_5h_left_percent"], 86)
        self.assertEqual(status["limit_5h_reset"], "20:53")
        self.assertEqual(status["weekly_left_percent"], 92)
        self.assertEqual(status["weekly_reset"], "10:53 on 7 Jul")

    def test_detects_status_limit_refresh_request(self):
        text = """
│  Limits:               refresh requested; run /status again shortly. │
"""

        self.assertTrue(status_needs_limit_refresh(text))

    def test_real_limits_do_not_need_refresh(self):
        text = """
│  5h limit:                    [████████████████████] 100% left           │
│                               (resets 13:43)                             │
│  Weekly limit:                [████████████░░░░░░░░] 58% left            │
│                               (resets 10:53 on 7 Jul)                    │
"""

        self.assertFalse(status_needs_limit_refresh(text))


if __name__ == "__main__":
    unittest.main()
