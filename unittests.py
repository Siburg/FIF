"""unit tests for FIF.py"""

from FIF import *
import unittest
#from unittest import mock
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext

class TestShare(unittest.TestCase):
    def setUp(self):
        self.someshare = Shareholding("some")
        self.emb = Shareholding('EMB', '11', '100.', '110.')
        self.robeco = Shareholding('Robeco', '1.2345', '111.11', '111.22', 'EUR')

    def test_existence(self):
        self.assertIsInstance(self.someshare, Shareholding)
        self.assertIsInstance(self.emb, Shareholding)
        self.assertIsInstance(self.robeco, Shareholding)

    def test_share_code(self):
        """test share name"""
        self.assertEqual(self.someshare.code, 'some')
        self.assertEqual(self.robeco.code, 'Robeco')

    def test_currency(self):
        self.assertAlmostEqual(self.someshare.currency, 'USD')
        self.assertEqual(self.robeco.currency, 'EUR')

    def test_start_holding(self):
        self.assertEqual(self.someshare.start_holding, '0')
        self.assertEqual(self.robeco.start_holding, '1.2345')

    def test_representation(self):
        self.assertEqual(repr(self.someshare), 'some shareholding is 0 shares')
        self.assertEqual(repr(self.emb), 'EMB shareholding is 11 shares')
        self.assertEqual(repr(self.robeco), 'Robeco shareholding is 1.2345 shares')


class TestTrade(unittest.TestCase):
    def setUp(self):
        self.veu_trade = Trade('VEU', "jan", '10', '115.0', '1.23')

    def test_existence(self):
        self.assertIsInstance(self.veu_trade, Trade)

    def test_representation(self):
        self.assertEqual(repr(self.veu_trade), 'trade for 10 shares of VEU on jan at 115.0 with costs of 1.23')


class TestDividend(unittest.TestCase):
    def setUp(self):
        self.emb_div = Dividend("EMB", 'feb', '0.023', '0.46')

    def test_existence(self):
        self.assertIsInstance(self.emb_div, Dividend)

    def test_representation(self):
        self.assertEqual(repr(self.emb_div), 'dividend of 0.46 on feb for EMB at 0.023 per share')


class TestGetOpeningPositions(unittest.TestCase):

    def setUp(self):
        self.robeco = Shareholding('Robeco', '1.2345', '111.11', '111.22', 'EUR')
        self.emb = Shareholding('EMB', '11', '100.', '110.')
        self.opening_positions = [self.robeco, self.emb]

    def test_return_type(self):
        self.assertEqual(type(self.opening_positions),list)

    def test_list_length(self):
        self.assertEqual(len(self.opening_positions), 2)


class TestCalcFDRBasic(unittest.TestCase):

    def test_return_exists(self):
        self.opening_positions = []
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        # review this for improvement
        self.assertTrue(FDR_basic >= 0)

    def test_single_share(self):
        self.opening_positions = [Shareholding('share1', '100', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('5.00'))

        self.opening_positions = [Shareholding('share2', '1.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.06'))

        self.opening_positions = [Shareholding('share3', '1.399', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.06'))

        self.opening_positions = [Shareholding('share4', '0.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))

        self.opening_positions = [Shareholding('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.00'))

    def test_more_shares(self):
        self.opening_positions = [Shareholding('share1', '100', '1.00'), Shareholding('share1', '100', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('10.00'))

        self.opening_positions = [Shareholding('share1', '100', '1.00'), Shareholding('share2', '1.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('5.06'))

        self.opening_positions = [Shareholding('share3', '1.399', '1.00'), Shareholding('share3', '1.399', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.13'))

        self.opening_positions = [Shareholding('share5', '0.2', '0.99'), Shareholding('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))




if __name__ == '__main__':
    unittest.main()
