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
        self.assertAlmostEqual(self.emb.currency, 'USD')
        self.assertEqual(self.robeco.currency, 'EUR')

    def test_start_holding(self):
        self.assertEqual(self.someshare.opening_holding, Decimal('0'))
        self.assertEqual(self.emb.opening_holding, Decimal('11'))
        self.assertEqual(self.robeco.opening_holding, Decimal('1.2345'))

    def test_holding(self):
        self.assertEqual(self.someshare.holding, Decimal('0'))
        self.assertEqual(self.emb.holding, Decimal('11'))
        self.assertEqual(self.robeco.holding, Decimal('1.2345'))

    def test_start_price(self):
        self.assertEqual(self.someshare.opening_price, Decimal('0'))
        self.assertEqual(self.emb.opening_price, Decimal('100'))
        self.assertEqual(self.robeco.opening_price, Decimal('111.11'))

    def test_end_price(self):
        self.assertEqual(self.someshare.closing_price, Decimal('0'))
        self.assertEqual(self.emb.closing_price, Decimal('110'))
        self.assertEqual(self.robeco.closing_price, Decimal('111.22'))

    def test_representation(self):
        self.assertEqual(repr(self.someshare), 'some shareholding is 0 shares')
        self.assertEqual(repr(self.emb), 'EMB shareholding is 11 shares')
        self.assertEqual(repr(self.robeco), 'Robeco shareholding is 1.2345 shares')

    def test_increase_holding(self):
        self.assertEqual(self.someshare.increase_holding('0'), Decimal('0'))
        self.assertEqual(self.emb.increase_holding(Decimal('0')), Decimal('11'))
        self.assertEqual(self.robeco.increase_holding(0), Decimal('1.2345'))
        self.assertEqual(self.someshare.increase_holding('1'), Decimal('1'))
        self.assertEqual(self.someshare.increase_holding(1), Decimal('2'))
        self.assertEqual(self.someshare.increase_holding('1.23'), Decimal('3.23'))
        self.assertEqual(self.robeco.increase_holding('1'), Decimal('2.2345'))
        self.assertEqual(self.robeco.increase_holding('.00006'), Decimal('2.23456'))
        self.assertEqual(self.robeco.increase_holding('-.23456'), Decimal('2'))
        self.assertEqual(self.robeco.increase_holding(-1), Decimal('1'))
        self.assertEqual(self.robeco.increase_holding('.99'), Decimal('1.99000'))
        self.assertEqual(self.robeco.holding, Decimal('1.99'))
        self.assertEqual(self.robeco.holding, Decimal('1.99000'))


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
        # self.robeco = Shareholding('Robeco', '1.2345', '111.11', '111.22', 'EUR')
        # self.emb = Shareholding('EMB', '11', '100.', '110.')
        # self.opening_positions = [self.robeco, self.emb]
        pass

    def test_return_type(self):
        self.assertEqual(type(get_opening_positions()),list)

    # def test_list_length(self):
    #     openings = get_opening_positions()
    #     self.assertEqual(len(openings), 2)


class TesProcessOpeningPositions(unittest.TestCase):

    def setUp(self):
        self.someshare = Shareholding("some")
        self.emb = Shareholding('EMB', '1100', '1000.', '110.')
        self.robeco = Shareholding('Robeco', '1.2345', '111.11', '111.22', 'EUR')
        self.opening_positions = [self.someshare, self.emb, self.robeco]

    def test_return(self):
        self.assertEqual(process_opening_positions(self.opening_positions), Decimal('1100137.17'))

    # test the rest visually for now from output to console generated
    # by test above



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
        self.assertEqual(FDR_basic, Decimal('0.07'))

        self.opening_positions = [Shareholding('share4', '0.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))

        self.opening_positions = [Shareholding('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))

    def test_more_shares(self):
        self.opening_positions = [Shareholding('share1', '100', '1.00'), Shareholding('share1', '100', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('10.00'))

        self.opening_positions = [Shareholding('share1', '100', '1.00'), Shareholding('share2', '1.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('5.06'))

        self.opening_positions = [Shareholding('share3', '1.399', '1.00'), Shareholding('share3', '1.399', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.14'))

        self.opening_positions = [Shareholding('share5', '0.2', '0.99'), Shareholding('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.02'))


class TestGetTrades(unittest.TestCase):

    def test_return_type(self):
        self.assertEqual(type(get_trades()),list)


if __name__ == '__main__':
    unittest.main()
