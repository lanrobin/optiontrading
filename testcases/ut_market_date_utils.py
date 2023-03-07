import unittest
from market_date_utils import (is_date_week_end, get_next_nth_friday)
from datetime import datetime, time, date

class TestConfig(unittest.TestCase):

    def test_is_date_week_end(self):
        self.assertTrue(is_date_week_end("2023-03-03"))
        self.assertTrue(is_date_week_end("2023-04-06"))
        self.assertTrue(is_date_week_end("2024-03-28"))
        self.assertTrue(is_date_week_end("2025-04-17"))

        self.assertFalse(is_date_week_end("2023-03-04"))
        self.assertFalse(is_date_week_end("2023-03-07"))

    def test_next_nth_friday(self):
        current = date.fromisoformat("2023-03-08")
        this_friday = date.fromisoformat("2023-03-10")
        next_friday = date.fromisoformat("2023-03-17")
        next_2rd_friday = date.fromisoformat("2023-03-24")

        self.assertEqual(this_friday, get_next_nth_friday(current, 0))
        self.assertEqual(next_friday, get_next_nth_friday(current, 1))
        self.assertEqual(next_2rd_friday, get_next_nth_friday(current, 2))

        current = date.fromisoformat("2023-03-11")
        this_friday = date.fromisoformat("2023-03-10")
        self.assertEqual(this_friday, get_next_nth_friday(current, 0))