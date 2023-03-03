import unittest
from market_date_utils import (is_date_week_end)

class test_config(unittest.TestCase):

    def test_is_date_week_end(self):
        self.assertTrue(is_date_week_end("2023-03-03"))
        self.assertTrue(is_date_week_end("2023-04-06"))
        self.assertTrue(is_date_week_end("2024-03-28"))
        self.assertTrue(is_date_week_end("2025-04-17"))

        self.assertFalse(is_date_week_end("2023-03-04"))
        self.assertFalse(is_date_week_end("2023-03-07"))