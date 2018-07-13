"""
A program to calculate Foreign Investment Fund (FIF) income in
accordance with tax rules in New Zealand. It calculates FIF income
using the Fair Dividend Rate (FDR) method and the Comparative Value
(CV) method. The minimum from those two methods is used as final
result for FIF income.

Note that some tax payers may use other methods as well or instead.
Such other methods are not covered by this program.

by Jelle Sjoerdsma
July 2018
version 0.2

No license (yet), but program is intended for public domain and may
be considered open source

Note: current version does not yet deal properly with exchange rates.
It does not yet have adequate functionality for dates and times.
It completely ignores, and will not work properly, with transactions
such as share splits or share reorganisations.
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext
from collections import namedtuple
from operator import attrgetter
import csv
#import json
from tkinter import filedialog, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

FAIR_DIVIDEND_RATE = '0.05'   # statutory Fair Dividend Rate of 5%


class Share:
    """
    Holds information on shares and shareholdings.
    Input arguments:
    code: a code, abbreviation or symbol to identify the share issuer.
    currency: currency of the share prices.
    opening_holding : number of shares held at start of the tax period.
    opening_price: price per share at start of the tax period.

    Other instance variables that are available:
    holding: current number of shares held, as calculated from other
        inputs.
    closing_price: price per share at end of the tax period.
    opening_value: to be calculated, and remembered.
    gross_income_from_dividends: to be calculated, and remembered.
    cost_of_trades: to be calculated, and remembered.
    closing_value: to be calculated, and remembered.
    quick_sale_adjustments: to be calculated,  if needed, and
        remembered.

    All numerical values are stored as Decimals. It is strongly
    recommended to pass numerical values for them as strings (or
    already in the form of Decimals), so they can be accurately
    converted to Decimals.

    The full share name or description is not currently a variable in
    this class. Consider it for addition later. Also consider splitting
    the class later into a Share class and a Holding class, or have
    a list of shareholdings over time inside the class.
    """
    def __init__(self, code, full_name, currency='USD', opening_holding='0', opening_price='0.00'):
        """
        Constructor function with defaults set to zero for numerical
        values. Default for currency is USD. Change that if you wish
        another default currency, e.g. AUD.
        """
        self.code = code
        self.full_name = full_name
        self.currency = currency
        self.opening_holding = Decimal(opening_holding)
        self.opening_price = Decimal(opening_price)

        # Variables below are not immediately needed when creating the
        # object, but will be used later. They are set up here in
        # preparation and for clarity.
        self.holding = Decimal(opening_holding)
        # holding is set to opening_holding (after conversion to
        # Decimal) at initialisation
        self.closing_price = Decimal('0.00')
        self.opening_value = Decimal('0.00')
        self.gross_income_from_dividends = Decimal('0.00')
        self.cost_of_trades = Decimal('0.00')
        self.closing_value = Decimal('0.00')
        self.quick_sale_adjustments = None  # most shares won't need it
        return

    def re_initialise_with_prior_year_closing_values(self):
        """
        Function that can be used at the start of a tax year to reset
        shares with closing values read in from a prior tax year. The
        opening values are set to those prior closing values, and
        closing values are reinitialised.
        Nothing happens if closing_value is not positive, on the
        assumption that this means the share has been re-initialised
        already, or is not a valid prior year share.
        """
        if self.closing_value > 0:
            self.opening_holding = self.holding
            self.opening_price = self.closing_price
            self.opening_value = self.closing_value
            self.closing_price = Decimal('0.00')
            self.gross_income_from_dividends = Decimal('0.00')
            self.cost_of_trades = Decimal('0.00')
            self.closing_value = Decimal('0.00')
            self.quick_sale_adjustments = None  # most shares won't need it
        return

    def increase_holding(self, increase):
        """
        Adds Decimal value of increase to holding. This means a
        positive value will increase holding, and a negative value
        will decrease it.
        increase: number of shares to increase/(decrease) holding with
        return: holding after the increase, in Decimal

        increase should be passed as a string (or as Decimal already)
        but will also accept an integer value.
        """
        self.holding += Decimal(increase)
        return self.holding

    def __repr__(self):
        return '{} shareholding is {} shares'.format(
            self.code, self.holding)


class Trade:
    """
    add comments
    """
    def __init__(self, code, date, number_of_shares, share_price, trade_costs):
        self.code = code
        # add functions to parse date into a datetime object
        self.date = date
        self.number_of_shares = Decimal(number_of_shares)
        self.share_price = Decimal(share_price)
        self.trade_costs = Decimal(trade_costs)
        self.charge = self.number_of_shares * self.share_price + self.trade_costs

    def __repr__(self):
        return 'trade for {:,f} shares of {} on {} at {:,.2f} with costs of {:,.2f}'.format(
               self.number_of_shares, self.code, self.date, self.share_price, self.trade_costs)


class Dividend:
    """
    Holds information on dividens.
    Could conceivably be replaced with a dict, or a namedtuple, or
    another type of object.

    Input arguments:
    code: a code, abbreviation or symbol to identify the share.
    full_name: the full name, or description, for the share.
    date: the payment date for the dividend (not the declaration date
        or other type of date). This should be in the form of a
        datetime object.
    per_share: the dividend per share, in its native currency, as
        declared by the issues.
    paid: the gross sum paid, before any withholding or other taxes,
        in its native currency, for the dividend.

    Other instance variables that are available:
    eligible_shares: the number of shares for which the dividend was
        paid; calculated as paid / per_share. Note that this number
        can be different from the shares held on the payment date,
        because not all of those may have been eligible (yet) for the
        dividend.

    All numerical values are stored as Decimals. It is strongly
    recommended to pass numerical values for them as strings (or
    already in the form of Decimals), so they can be accurately
    converted to Decimals.

    The class does not yet hold information on withholding or other
    taxes on dividends. This probably still needs to be added.
    """
    def __init__(self, code, date, per_share, paid):
        self.code = code
        # add functions to parse date into a datetime object
        self.date = date
        self.per_share = Decimal(per_share)
        self.paid = Decimal(paid)
        # consider something for tax
        # Note that self.paid should be gross before tax, or the
        # calculation below will need to be modified for tax effects.
        self.eligible_shares = self.paid / self.per_share

    def __repr__(self):
        return 'dividend of {:,.2f} on {} for {} at {} per share'.format(
               self.paid, self.date, self.code, self.per_share)


def get_opening_positions():
    opening_positions = []
    return opening_positions


def process_opening_positions(opening_shares, fair_dividend_rate):
    """
    Calculates NZD value of each share held at opening, sets that value
    for the share, and calculates total NZD value across shares. Also
    calculates FRD basic income (without quick sale adjustments).
    First for each share individually, and then the combined total.
    Prints inputs and results in a tabular format.

    arguments:
    opening_shares: list of shares, as obtained from
        get_opening_positions (i.e. without any updates from trades)
    fair_dividend_rate: the statutory Fair Dividend Rate. This should
        be provided as a string or a Decimal.

    return: (tuple with)
    total_opening_value: in NZD
    FDR_basic_income: total from calculations (and roundings) per share

    other data changes (to mutable objects in arguments):
    opening_value for each Share in opening_shares is set.

    Code is ignoring currencies for now. An exchange rate of 1 is
    temporarily used for all currencies.
    """
    total_opening_value = Decimal('0.00')
    FDR_basic_income = Decimal('0.00')
    # Need to do something better for setting date below
    previous_closing_date = '31 Mar 2017'

    header_format_string = '{:15} {:>12} {:>10} {:>15} {:8} {:>15}'
    share_format_string = '{:15} {:12,} {:10,.2f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the opening_value line width.
    print('\nOpening positions, based on previous closing positions for {}'.format(
        previous_closing_date))
    print(header_format_string.format(
        'share code', 'shares held', 'price', 'foreign value', 'currency', 'NZD value'))

    for share in opening_shares:
        foreign_value = (share.opening_holding * share.opening_price).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Note that we are first rounding off the value in foreign
        # currency, before additional rounding below. This can only
        # be an issue for shares with fractional holdings.

        currency_FX_rate = FX_rate(share.currency, '31-3-2017', 'month-end')
        # obviously this needs work

        # Make this a separate rounding as well.
        NZD_value = (foreign_value * currency_FX_rate).quantize(
            Decimal('0.01'), ROUND_HALF_UP)

        # Next statement stores the result in Share object
        share.opening_value = NZD_value
        total_opening_value += NZD_value

        FDR_basic_income += (NZD_value * Decimal(fair_dividend_rate)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        # It appears that FIF needs to be calculated for each security.
        # That's why final rounding is done per share, after
        # multiplying eachshare with the fair_dividend_rate.

        print(share_format_string.format(
            share.code, share.opening_holding, share.opening_price, foreign_value, share.currency,
            NZD_value))

    print('{:>80}'.format('---------------'))
    print('{:40}{:>40,.2f}\n'.format('total opening value', total_opening_value))
    return total_opening_value, FDR_basic_income


def get_trades(shares):
    """
    ADD COMMENTS
    :return:
    """
    trades = []
    return trades


def process_trades(shares, trades):
    """

    :param trades:
    :return:
    """
    total_cost_of_trades = Decimal('0.00')
    any_quick_sale_adjustment = False
    # trades.sort(key = lambda trade: trade.date)
    trades.sort(key = attrgetter('date'))   # faster key implementation
    # Sorting the trades by date is necessary to work out the need for
    # a quick sale adjustment, and to properly calculate such an
    # adjustment later if needed.
    # The sort is done in place, and trades is a mutable object, so the
    # sorting should be retained for later use of the trades list
    # outside this function as well.

    for trade in trades:
        # check if we already have a matching share code
        # there may be a more Pythonic solution, but this works for now
        new_share = True
        for share in shares:
            if trade.code == share.code:
                new_share = False
                break   # only need to find it once

        if new_share:
            # do stuff to add a new share
            print(trade.__repr__() + ' is for a share that is not yet in the system.')
            currency = input('Enter the currency code in which that share trades (e.g. USD): ')
            # next line is a temporary fix
            currency_list = ['USD', 'EUR', 'AUD', 'GBP']
            while not currency in currency_list:
                print('The system does not have any information for currency code ' + currency)
                currency = input('Please enter a valid code for an existing currency')

            full_name = input('Enter the full share name or description for ' +
                    trade.code + ' : ')

            share = Share(trade.code, full_name, currency)
            shares.append(share)

    # After this we should have a share instance to match every trade.
    # For cosmetic output reasons, and probably greater efficiency,
    # we now process all trades aggregated by share.

    header_format_string = '{:15} {:14} {:>12} {:>10} {:>11} {:>15} {:8} {:>15}'
    trade_format_string = '{:15} {:14} {:12,f} {:10,.2f} {:11,.2f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the opening_value line width.
    print('\nTrades: share acquisitions (positive) and disposals (negative)')
    print(header_format_string.format(
        'share code', 'trade date', 'shares', 'price', 'fees', 'foreign value',
        'currency', 'NZD value'))

    for share in shares:
        share_cost_of_trades = Decimal('0.00')
        shares_acquired = False
        for trade in trades:
            if trade.code == share.code:
                currency_FX_rate = FX_rate(share.currency, trade.date, 'mid-month')
                # obviously this needs work

                NZD_value = (trade.charge * currency_FX_rate).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)

                # This is why there is an outer loop. If a separate
                # total by share is not needed then the inner loop
                # would be enough.
                share_cost_of_trades += NZD_value

                if trade.number_of_shares > Decimal('0'):
                    shares_acquired = True
                elif shares_acquired and trade.number_of_shares < Decimal('0'):
                    share.quick_sale_adjustments = True
                # Here we are enjoying Python's duck typing, changing
                # value from None to True, in preparation for later
                # assigning a Decimal value to quick_sale_adjustments.
                # The test for number_of_shares < 0 may be overkill,
                # but is there just in case we encounter a bizarre
                # situation where a trade record would be for 0 shares.

                print(trade_format_string.format(
                    share.code, trade.date, trade.number_of_shares, trade.share_price,
                    trade.trade_costs, trade.charge, share.currency, NZD_value))

        share.cost_of_trades = share_cost_of_trades
        # update the quick sale adjustment to something else than None
        # E.g. use -1 as value to indicate it needs to be calculated
        total_cost_of_trades += share_cost_of_trades
        if share.quick_sale_adjustments:
            any_quick_sale_adjustment = True

    print('{:>107}'.format('---------------'))
    print('{:67}{:>40,.2f}\n'.format('total cost of trades / (proceeds from disposals)',
        total_cost_of_trades))
    # cost_of_trades in share instances have been
    # updated as well. Because shares is a mutable list, this does not
    # need to be part of the return.
    return total_cost_of_trades, any_quick_sale_adjustment


def get_dividends(shares):
    """
    ADD COMMENTS
    :return:
    """
    dividends = []
    return dividends


def process_dividends(shares, dividends):
    """

    :param dividends:
    :return:
    """
    total_income_from_dividends = Decimal('0.00')

    header_format_string = '{:15} {:14} {:>12} {:>10} {:>15} {:8} {:>15}'
    dividend_format_string = '{:15} {:14} {:12,f} {:10,f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the opening_value line width.
    print('\nDividends')
    print(header_format_string.format(
        'share code', 'payment date', 'shares', 'dividend', 'foreign value', 'currency',
        'NZD value'))

    for share in shares:
        share_income_from_dividends = Decimal('0.00')
        for dividend in dividends:
            if dividend.code == share.code:
                currency_FX_rate = FX_rate(share.currency, dividend.date, 'mid-month')
                # obviously this needs work

                NZD_value = (dividend.paid * currency_FX_rate).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)

                # This is why there is an outer loop. If a separate
                # total by share is not needed then the inner loop
                # would be enough.
                share_income_from_dividends += NZD_value

                print(dividend_format_string.format(
                    share.code, dividend.date, dividend.eligible_shares, dividend.per_share,
                    dividend.paid, share.currency, NZD_value))

        share.gross_income_from_dividends = share_income_from_dividends
        total_income_from_dividends += share_income_from_dividends

    print('{:>95}'.format('---------------'))
    print('{:55}{:>40,.2f}\n'.format('total income from dividends', total_income_from_dividends))
    # gross_income_from_dividends in share instances have been
    # updated as well. Because shares is a mutable list, this does not
    # need to be part of the return.
    return total_income_from_dividends


def get_closing_prices(shares):
    """

    :return:
    """
    closing_prices = []
    closing_price_info = namedtuple('closing_price_info', 'code, price')
    return closing_prices


def process_closing_prices(shares, closing_prices):
    """

    :param shares:
    :return:
    """
    total_closing_value = Decimal('0.00')
    closing_date = '31 Mar 2018'  # revise to get an actual date

    header_format_string = '{:15} {:>12} {:>10} {:>15} {:8} {:>15}'
    share_format_string = '{:15} {:12,} {:10,.2f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the opening_value line width.
    print('\nClosing positions for {}'.format(closing_date))
    print(header_format_string.format(
        'share code', 'shares held', 'price', 'foreign value', 'currency', 'NZD value'))

    for closing_price_info in closing_prices:
        # assume that we did indeed obtain a closing price for every
        # share with a closing holding > 0
        for share in shares:
            # assume the lists are not sorted by share code
            if share.code == closing_price_info.code:
                share.closing_price = Decimal(closing_price_info.price)

                foreign_value = (share.holding * share.closing_price).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)
                # Note that we are first rounding off the value in foreign
                # currency, before additional rounding below. This can only
                # be an issue for shares with fractional holdings.

                currency_FX_rate = FX_rate(share.currency, '31-3-2018', 'month-end')
                # obviously this needs work

                # Make this a separate rounding as well.
                NZD_value = (foreign_value * currency_FX_rate).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)

                # Next statement stores the result in Share object
                share.closing_value = NZD_value
                total_closing_value += NZD_value

                print(share_format_string.format(
                    share.code, share.holding, share.closing_price, foreign_value,
                    share.currency, NZD_value))

                # no need to continue inner loop after having the share
                # matching the closing_price_info.code. There is only
                # one closing price per share.
                break

    # Also print shares that do not have a closing price or value.
    # This could risk double printing if a zero price is included in
    # the closing_prices list, but is otherwise harmless.
    for share in shares:
        if share.closing_price == Decimal(0) or share.holding == Decimal(0):
            print(share_format_string.format(
                share.code, share.holding, share.closing_price, 0,
                share.currency, 0))

    print('{:>80}'.format('---------------'))
    print('{:40}{:>40,.2f}\n'.format('total closing value', total_closing_value))

    # closing_price and closing_value in share instances have been
    # updated as well. Because shares is a mutable list, this does not
    # need to be part of the return.
    return total_closing_value


def save_closing_positions(shares):
    """

    :param shares:
    :return:
    """
    if len(shares) == 0:
        print('nothing to save')
        return  # early exit

    Tk().withdraw
    filename = asksaveasfilename()
    share_fields = shares[0].__dict__.keys()
    with open(filename, 'w') as shares_save_file:
        writer = csv.DictWriter(shares_save_file, fieldnames=share_fields)
        writer.writeheader()
        for share in shares:
            writer.writerow(share.__dict__)

    # for share in shares:
    #     json_item = json.dumps(share, default = lambda x: x.__dict__)
    #     print(json_item)
    return


def calc_QSA(shares, trades, dividends):
    """

    :return:
    """
    quick_sale_adjustments = Decimal('0.00')
    return quick_sale_adjustments


def FX_rate(currency, date, conversion_method):
    """

    :param currency:
    :param date:
    :param conversion_method:
    :return:
    """
    exchange_rate = Decimal('1.0000')
    return exchange_rate


def main():
    shares = get_opening_positions()
    # get exchange rates
    opening_value, FDR_basic_income = process_opening_positions(shares, FAIR_DIVIDEND_RATE)
    # Need to process trades first, to get info on shares purchased
    # during the year, which might receive dividends later.
    trades = get_trades(shares)
    cost_of_trades, any_quick_sale_adjustment = process_trades(shares, trades)
    dividends = get_dividends(shares)
    gross_income_from_dividends = process_dividends(shares, dividends)
    closing_prices = get_closing_prices(shares)
    closing_value = process_closing_prices(shares, closing_prices)
    save_closing_positions(shares)
    CV_income = closing_value + gross_income_from_dividends - (opening_value + cost_of_trades)

    if any_quick_sale_adjustment:
        quick_sale_adjustments = calc_QSA(shares, trades, dividends)
    else:
        quick_sale_adjustments = Decimal('0.00')

    FDR_income = FDR_basic_income + quick_sale_adjustments
    FIF_income = max(0, min(FDR_income, CV_income))


if __name__ == '__main__':
    main()
