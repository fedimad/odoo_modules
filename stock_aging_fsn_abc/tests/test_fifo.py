# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged

from ..wizard.stock_analysis_wizard import StockAnalysisWizard as W


@tagged('post_install', '-at_install')
class TestAnalysisLogic(TransactionCase):
    BOUNDS = [30, 60, 90, 180]
    TODAY = date(2026, 10, 14)

    def test_bucket_index(self):
        self.assertEqual(W._bucket_index(0, self.BOUNDS), 0)
        self.assertEqual(W._bucket_index(30, self.BOUNDS), 0)
        self.assertEqual(W._bucket_index(31, self.BOUNDS), 1)
        self.assertEqual(W._bucket_index(180, self.BOUNDS), 3)
        self.assertEqual(W._bucket_index(181, self.BOUNDS), 4)

    def test_fifo_uses_newest_receipts_first(self):
        # 10 received 5 days ago, 10 received 200 days ago, 12 sold since -> 8 left
        inbound = [(date(2026, 10, 9), 10.0), (date(2026, 3, 27), 10.0)]
        res = W._fifo_allocate(inbound, 8.0, self.TODAY, self.BOUNDS)
        self.assertEqual(res, [8.0, 0.0, 0.0, 0.0, 0.0])
        res = W._fifo_allocate(inbound, 15.0, self.TODAY, self.BOUNDS)
        self.assertEqual(res, [10.0, 0.0, 0.0, 0.0, 5.0])

    def test_fifo_unexplained_stock_is_oldest(self):
        res = W._fifo_allocate([(self.TODAY, 2.0)], 5.0, self.TODAY, self.BOUNDS)
        self.assertEqual(res, [2.0, 0.0, 0.0, 0.0, 3.0])

    def test_abc_class(self):
        self.assertEqual(W._abc_class(0.0, 100.0, 80, 15), 'A')
        self.assertEqual(W._abc_class(79.9, 10.0, 80, 15), 'A')
        self.assertEqual(W._abc_class(80.0, 10.0, 80, 15), 'B')
        self.assertEqual(W._abc_class(95.0, 1.0, 80, 15), 'C')
        self.assertEqual(W._abc_class(10.0, 0.0, 80, 15), 'C')

    def test_fsn_class(self):
        self.assertEqual(W._fsn_class(0, 10, 1.0), 'N')
        self.assertEqual(W._fsn_class(10, 10, 1.0), 'F')
        self.assertEqual(W._fsn_class(3, 10, 1.0), 'S')
        self.assertEqual(W._fsn_class(3, 0, 1.0), 'F')
