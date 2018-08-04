"""unit tests for FIF.py"""

from FIF import *
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
import io
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext
from collections import namedtuple
from datetime import date

item_format = namedtuple('item_output_format', 'header, width, precision')
output_format = {}
output_format['code'] = item_format('share code', 16, 16)
output_format['full_name'] = item_format('name / description', 27, 27)
output_format['price'] = item_format('price', 10, 999)
output_format['holding'] = item_format('shares', 13, 999)
output_format['value'] = item_format('value', 16, 2)
# Next 2 lines are a bit of kludge to combine " currency rate" in
# the header. We also want a space after printing the previous
# value, so that is why we are right-aligning the 3-letter
# currency in a field with a width of 4.
output_format['currency'] = item_format(' cur', 4, 4)
output_format['FX rate'] = item_format('rency rate', 10, 4)
output_format['fees'] = item_format('fees', 12, 2)
output_format['date'] = item_format(' date ( & time)', 15, 15)
output_format['dividend'] = item_format('gross dividend', 22, 999)
output_format['total width'] = 112


class TestShare(unittest.TestCase):
    def setUp(self):
        self.someshare = Share('some', 'some share')
        self.emb = Share('EMB', 'Emerging Market Bonds', 'USD', '1100', '1000.')
        self.robeco = Share('Robeco', 'Robeco Emerging Stars', 'EUR', '1.2345', '111.11')

    def test_existence(self):
        self.assertIsInstance(self.someshare, Share)
        self.assertIsInstance(self.emb, Share)
        self.assertIsInstance(self.robeco, Share)

    def test_share_code(self):
        """test share name"""
        self.assertEqual(self.someshare.code, 'some')
        self.assertEqual(self.robeco.code, 'Robeco')

    def test_full_name(self):
        """test share name"""
        self.assertEqual(self.someshare.full_name, 'some share')
        self.assertEqual(self.robeco.full_name, 'Robeco Emerging Stars')

    def test_currency(self):
        self.assertAlmostEqual(self.someshare.currency, 'USD')
        self.assertAlmostEqual(self.emb.currency, 'USD')
        self.assertEqual(self.robeco.currency, 'EUR')

    def test_start_holding(self):
        self.assertEqual(self.someshare.opening_holding, Decimal('0'))
        self.assertEqual(self.emb.opening_holding, Decimal('1100'))
        self.assertEqual(self.robeco.opening_holding, Decimal('1.2345'))

    def test_holding(self):
        self.assertEqual(self.someshare.holding, Decimal('0'))
        self.assertEqual(self.emb.holding, Decimal('1100'))
        self.assertEqual(self.robeco.holding, Decimal('1.2345'))

    def test_start_price(self):
        self.assertEqual(self.someshare.opening_price, Decimal('0'))
        self.assertEqual(self.emb.opening_price, Decimal('1000'))
        self.assertEqual(self.robeco.opening_price, Decimal('111.11'))

    def test_representation(self):
        self.assertEqual(repr(self.someshare), 'some shareholding is 0 shares')
        self.assertEqual(repr(self.emb), 'EMB shareholding is 1100 shares')
        self.assertEqual(repr(self.robeco), 'Robeco shareholding is 1.2345 shares')

    def test_other_initialisations(self):
        self.assertEqual(self.someshare.closing_price, Decimal('0'))
        self.assertEqual(self.emb.opening_value, Decimal('0'))
        self.assertEqual(self.robeco.gross_income_from_dividends, Decimal('0'))
        self.assertEqual(self.someshare.cost_of_trades, Decimal('0'))
        self.assertEqual(self.emb.closing_value, Decimal('0'))
        self.assertIs(self.robeco.quick_sale_adjustments, None)

    def test_re_initialise_with_prior_year_closing_values(self):
        self.someshare.quick_sale_adjustments = 1
        self.emb.closing_price = Decimal('1200')
        self.emb.closing_value = Decimal('2400000')
        self.emb.holding = Decimal('2000')
        self.emb.gross_income_from_dividends = Decimal('1234')
        self.emb.cost_of_trades = Decimal('1100000')
        self.emb.quick_sale_adjustments = Decimal('99')
        self.someshare.re_initialise_with_prior_year_closing_values()
        self.emb.re_initialise_with_prior_year_closing_values()
        #self.assertEqual(self.someshare.quick_sale_adjustments, 1)
        # because it should not have changed
        self.assertEqual(self.emb.opening_price, Decimal('1200'))
        self.assertEqual(self.emb.opening_value, Decimal('2400000'))
        self.assertEqual(self.emb.opening_holding, Decimal('2000'))
        self.assertEqual(self.emb.gross_income_from_dividends, Decimal('0'))
        self.assertEqual(self.emb.cost_of_trades, Decimal('0'))
        self.assertIs(self.emb.quick_sale_adjustments, None)

    def test_increase_holding(self):
        self.assertEqual(self.someshare.increase_holding('0'), Decimal('0'))
        self.assertEqual(self.emb.increase_holding(Decimal('0')), Decimal('1100'))
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


class TestDividend(unittest.TestCase):
    def setUp(self):
        self.emb_div = Dividend("EMB", 'feb', '0.023', '0.46')
        self.large_div = Dividend('large', '30-11-2017', '100', '100000')
        self.partial_div = Dividend('partial', '1 Mar 2018', '10', '1.23')

    def test_existence(self):
        self.assertIsInstance(self.emb_div, Dividend)

    def test_representation(self):
        self.assertEqual(repr(self.emb_div), 'dividend of 0.46 on feb for EMB at 0.023 per share')
        self.assertEqual(repr(self.large_div),
            'dividend of 100,000.00 on 30-11-2017 for large at 100 per share')
        self.assertEqual(repr(self.partial_div),
            'dividend of 1.23 on 1 Mar 2018 for partial at 10 per share')

    def test_variables(self):
        self.assertEqual(self.emb_div.per_share, Decimal('0.023'))
        self.assertEqual(self.emb_div.gross_paid, Decimal('0.46'))

    def test_eligible_shares(self):
        self.assertEqual(type(self.emb_div.eligible_shares), Decimal)
        self.assertEqual(self.emb_div.eligible_shares, Decimal('20'))
        self.assertEqual(self.large_div.eligible_shares, Decimal('1000'))
        self.assertEqual(self.partial_div.eligible_shares, Decimal('0.123'))


class TestTrade(unittest.TestCase):
    def setUp(self):
        self.veu_trade = Trade('VEU', "jan", '10', '115', '1.23')
        self.emb_trade = Trade('EMB', '01-02-18', '-1000', '90.99', '4.56')

    def test_existence(self):
        self.assertIsInstance(self.veu_trade, Trade)

    def test_representation(self):
        self.assertEqual(repr(self.veu_trade),
            'trade for 10 shares of VEU on jan at 115.00 with costs of 1.23')
        self.assertEqual(repr(self.emb_trade),
            'trade for -1,000 shares of EMB on 01-02-18 at 90.99 with costs of 4.56')

    def test_variables(self):
        self.assertEqual(self.veu_trade.number_of_shares, Decimal('10'))
        self.assertEqual(self.veu_trade.share_price, Decimal('115'))
        self.assertEqual(self.veu_trade.trade_costs, Decimal('1.23'))
        self.assertEqual(self.emb_trade.number_of_shares, Decimal('-1000'))
        self.assertEqual(self.emb_trade.share_price, Decimal('90.99'))
        self.assertEqual(self.emb_trade.trade_costs, Decimal('4.56'))

    def test_charge_calculation(self):
        self.assertEqual(self.veu_trade.charge, Decimal('1151.23'))
        self.assertEqual(self.emb_trade.charge, Decimal('-90985.44'))


class TestYesOrNo(unittest.TestCase):

    def setUp(self):
        self.print_redirect = io.StringIO()
        sys.stdout = self.print_redirect

    @patch('builtins.input', MagicMock(side_effect=['y']))
    def test_type(self):
        self.assertIsInstance(yes_or_no('what?'), bool)

    def test_inputs(self):
        with mock.patch('builtins.input', side_effect=['y']):
            self.assertTrue(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['Y']):
            self.assertTrue(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['yes']):
            self.assertTrue(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['YES']):
            self.assertTrue(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['yEs']):
            self.assertTrue(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['n']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['N']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['no']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['NO']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['nO']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['yess', 'n']):
            self.assertFalse(yes_or_no('q'))
            printed = self.print_redirect.getvalue()
            self.assertEqual(printed, 'That is not a valid response; please try again.\n')
        with mock.patch('builtins.input', side_effect=['ye', 'n']):
            self.assertFalse(yes_or_no('q'))
        with mock.patch('builtins.input', side_effect=['noo', 'y']):
            self.assertTrue(yes_or_no('q'))


    # Test below does not work. Use of a mock for input seems to
    # obliterate the input prompt.
    # def test_question(self):
    #     with mock.patch('builtins.input', side_effect=['x']):
    #         yes_or_no('what?')
    #     printed = self.print_redirect.getvalue()
    #     self.assertEqual(printed, 'what?')

    def tearDown(self):
        self.print_redirect.__del__()
        sys.stdout = sys.__stdout__


@unittest.skip
class TestGetTaxYear(unittest.TestCase):
    pass


class TestGetFXRates(unittest.TestCase):
    def test_fx_rates(self):
        fx_rates = get_fx_rates()
        self.assertTrue(isinstance(fx_rates,dict))


#@unittest.skip
class TestGetClosingDateFunctions(unittest.TestCase):

    def test_returns(self):
        previous_result = previous_closing_date(2016)
        self.assertTrue(isinstance(previous_result, date))
        self.assertEqual(previous_result.month,3)
        self.assertEqual(previous_result.day,31)
        self.assertEqual(previous_result.year,2015)

        result = closing_date(2016)
        self.assertTrue(isinstance(result, date))
        self.assertEqual(result.year,2016)


#@unittest.skip
class TestGetOpeningPositions(unittest.TestCase):

    def setUp(self):
        # self.robeco = Share('Robeco', 'robeco', 'EUR', '1.2345', '111.11')
        # self.emb = Share('EMB', 'emb', 'USD', '11', '100.')
        # self.opening_positions = [self.robeco, self.emb]
        # need to provide mock input to test with
        self.result = get_opening_positions(2016)

    def test_return_type(self):
        self.assertTrue(isinstance(self.result,list))
        if len(self.result) > 0:
            self.assertTrue(isinstance(self.result[0],Share))

    def test_list_length(self):
        self.assertEqual(len(self.result), 13) # that's for current hard-coded file


@unittest.skip
class TestProcessOpeningPositions(unittest.TestCase):

    def setUp(self):
        self.someshare = Share('some', 'some share')
        self.emb = Share('EMB', 'Emerging Markets Bonds', 'USD', '1100', '1000.')
        self.robeco = Share('Robeco', 'Robeco Emerging Stars', 'EUR', '1.2345', '111.11')
        self.opening_positions = [self.someshare, self.emb, self.robeco]
        self.result = process_opening_positions(self.opening_positions, {}, '0.05', 2015,
                output_format)
        return self.opening_positions

    def test_return(self):
        self.assertEqual(type(self.result), tuple)
        self.assertEqual(self.result, (Decimal('1100137.17'), Decimal('55006.86')))

    def test_share_opening_values(self):
        #these will be updated values after the process ran in the setup
        self.assertEqual(self.someshare.opening_value, Decimal('0'))
        self.assertEqual(self.emb.opening_value, Decimal('1100000'))
        self.assertEqual(self.robeco.opening_value, Decimal('137.17'))

    @unittest.skip
    def test_FDR_basic_income_calculations(self):
        pass
        # copy tests from the skipped tests for TestCalcFDRBasic below,
        # but do something
        # to avoid print output every time a test is run

    # test the rest visually for now from output to console generated
    # by test above


@unittest.skip  #need to revise this after integrating it with previous function
# also need to add full_name to all share instantiations if it is integrated
class TestCalcFDRBasic(unittest.TestCase):

    def test_single_share(self):
        self.opening_positions = [Share('share1', '100', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('5.00'))

        self.opening_positions = [Share('share2', '1.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.06'))

        self.opening_positions = [Share('share3', '1.399', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.07'))

        self.opening_positions = [Share('share4', '0.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))

        self.opening_positions = [Share('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.01'))

    def test_more_shares(self):
        self.opening_positions = [Share('share1', '100', '1.00'), Share('share1', '100', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('10.00'))

        self.opening_positions = [Share('share1', '100', '1.00'), Share('share2', '1.2', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('5.06'))

        self.opening_positions = [Share('share3', '1.399', '1.00'), Share('share3', '1.399', '1.00')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.14'))

        self.opening_positions = [Share('share5', '0.2', '0.99'), Share('share5', '0.2', '0.99')]
        FDR_basic = calc_FDR_basic(self.opening_positions, '0.05')
        self.assertEqual(FDR_basic, Decimal('0.02'))


class TestGetTrades(unittest.TestCase):

    def test_return_type(self):
        self.assertEqual(type(get_trades()),list)


@unittest.skip
class TestProcessTrades(unittest.TestCase):

    def setUp(self):
        self.shares = TestProcessOpeningPositions.setUp(self)
        self.robeco_trade = Trade('Robeco', "jan", '10', '115', '1.23')
        self.emb_trade2 = Trade('EMB', '02 Mar 18', '-1000', '90.99', '4.56')
        self.emb_trade1 = Trade('EMB', '01 Mar 18', '3000', '100', '12.34')
        self.trades = [self.emb_trade2, self.robeco_trade, self.emb_trade1]

    def test_return(self):
        result = process_trades(self.shares, self.trades)
        self.assertEqual(type(result[0]), Decimal)
        self.assertEqual(type(result[1]), bool)
        self.assertEqual(result[0], Decimal('210178.13'))
        self.assertIs(result[1], True)

    def test_share_updates(self):
        self.result = process_trades(self.shares, self.trades)
        self.assertEqual(self.someshare.cost_of_trades, Decimal('0'))
        # should not have changed
        self.assertEqual(self.robeco.cost_of_trades, Decimal('1151.23'))
        self.assertEqual(self.emb.cost_of_trades, Decimal('209026.9'))
        self.assertIs(self.robeco.quick_sale_adjustments, None)
        self.assertIs(self.emb.quick_sale_adjustments, True)

    def test_trade_for_new_share(self):
        new_trade = Trade('new','01-10-17', '100', '9.99', '1.00')
        self.trades.append(new_trade)
        with mock.patch('builtins.input', side_effect=['USD', 'new share name']):
            result = process_trades(self.shares, self.trades)
        self.assertEqual(result[0], Decimal('211178.13'))
        self.assertEqual(self.shares[-1].cost_of_trades, Decimal('1000'))
        self.assertIs(self.shares[-1].quick_sale_adjustments, None)

    # need to add a test for creation of new shares as result of trade
    # purchase of a share that was not part of opening position

    # test the rest visually for now from output to console generated
    # by test above


class TestGetDividends(unittest.TestCase):

    def test_return_type(self):
        self.assertEqual(type(get_dividends()),list)


@unittest.skip
class TestProcessDividends(unittest.TestCase):

    def setUp(self):
        self.emb_div = Dividend("EMB", 'feb', '0.023', '0.46')
        self.large_div = Dividend('EMB', '30-11-2017', '100', '100000')
        self.partial_div = Dividend('Robeco', '1 Mar 2018', '10', '1.23')
        self.dividends = [self.large_div, self.partial_div, self.emb_div]
        self.shares = TestProcessOpeningPositions.setUp(self)
        self.result = process_dividends(self.shares, self.dividends)

    def test_return(self):
        self.assertEqual(type(self.result), Decimal)
        self.assertEqual(self.result, Decimal('100001.69'))

    def test_share_updates(self):
        self.assertEqual(self.someshare.gross_income_from_dividends, Decimal('0'))
        # should not have changed
        self.assertEqual(self.robeco.gross_income_from_dividends, Decimal('1.23'))
        self.assertEqual(self.emb.gross_income_from_dividends, Decimal('100000.46'))

    # test the rest visually for now from output to console generated
    # by test above


@unittest.skip
class TestProcessClosingPrices(unittest.TestCase):

    def setUp(self):
        self.shares = TestProcessOpeningPositions.setUp(self)
        self.emb.holding = Decimal('2000')
        self.robeco.holding = Decimal('1.9876')
        closing_price_info = namedtuple('closing_price_info', 'code, price')
        embprice = closing_price_info('EMB', '1200.00')
        robecoprice = closing_price_info('Robeco', '122.22')
        dummyprice = closing_price_info('dummy', '99')
        self.closing_prices = [robecoprice, dummyprice, embprice]
        # closing_price order mixed up
        self.result = process_closing_prices(self.shares, self.closing_prices, 2016)

    def test_return(self):
        self.assertEqual(type(self.result), Decimal)
        self.assertEqual(self.result, Decimal('2400242.92'))

    def test_closing_prices(self):
        self.assertEqual(self.emb.closing_price, Decimal('1200'))
        self.assertEqual(self.robeco.closing_price, Decimal('122.22'))
        self.assertEqual(self.someshare.closing_price, Decimal('0'))
        # should not have changed

    def test_closing_values(self):
        self.assertEqual(self.emb.closing_value, Decimal('2400000'))
        self.assertEqual(self.robeco.closing_value, Decimal('242.92'))
        self.assertEqual(self.someshare.closing_value, Decimal('0'))
        # should not have changed

    # test the rest visually for now from output to console generated
    # by test above


@unittest.skip
class TestSaveClosingPositions(unittest.TestCase):

    def setUp(self):
        self.shares = TestProcessOpeningPositions.setUp(self)
        self.emb.holding = Decimal('2000')
        self.robeco.holding = Decimal('1.9876')
        self.result = save_closing_positions(self.shares)

    def test_return(self):
        pass


class TestGetNewShareNameAndCurrency(unittest.TestCase):

    def setUp(self):
        self.new_trade = Trade('new', '01-10-17', '100', '9.99', '1.00')

    def test_return_values(self):
        """ check that we get 2 return values for normal input"""
        with mock.patch('builtins.input', side_effect=['USD', 'share name']):
            values = get_new_share_currency_and_full_name(self.new_trade)
        self.assertIs(type(values), tuple)
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0], 'share name')
        self.assertEqual(values[1], 'USD')

    def test_invalid_currency_rejection(self):
        with mock.patch('builtins.input', side_effect=['usd', 'USD', 'share name']):
            values = get_new_share_currency_and_full_name(self.new_trade)
        self.assertEqual(values[0], 'share name')
        self.assertEqual(values[1], 'USD')


@unittest.skip
class TestMain(unittest.TestCase):

    def setUp(self):
        result = main()

    def test_main(self):
        pass

    def test_nothing(self):
        pass


if __name__ == '__main__':
    unittest.main()
