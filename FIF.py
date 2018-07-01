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

No license (yet), but program is intended for public domain and may
be considered open source
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext

FDR_RATE = '0.05'   # statutory Fair Dividend Rate of 5%

class Shareholding:
    """
    Holds information on shareholdings.
    code: a code or abbreviation to identify the share issuer.
    start_holding : number of shares held at start of the tax period.
    holding: current number of shares held.
    start_price: price per share at start of the tax period.
    end_price: price per share at end of the tax period.
    currency: currency of the share prices.

    The numerical values for shareholdings and prices are stored as
    Decimals. It is strongly recommended to pass numerical values for
    them as strings (or already in the form of Decimals), so they can
    be accurately converted to Decimals.
    """
    def __init__(self, code, start_holding='0', start_price='0.00', end_price='0.00',
                 currency='USD'):
        """
        Constructor function with defaults set to zero for numerical
        values. Default for currency is USD. Change that if you wish
        another default currency, e.g. AUD.
        """
        self.code = code
        self.start_holding = Decimal(start_holding)
        # holding is set to start_holding (after conversion to Decimal)
        # at initialisation
        self.holding = Decimal(start_holding)
        self.start_price = Decimal(start_price)
        self.end_price = Decimal(end_price)
        self.currency = currency
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
        return ('{} shareholding is {} shares').format(
            self.code, self.holding)


class Trade:
    """
    add comments
    """
    def __init__(self, code, date, share_change, price, costs):
        self.code = code
        # add functions to parse date into a datetime object
        self.date = date
        self.share_change = share_change
        self.price = price
        self.costs = costs
        self.charge = Decimal(share_change) * Decimal(price) + Decimal(costs)

    def __repr__(self):
        return ('trade for {} shares of {} on {} at {} with costs of {}').format(
               self.share_change, self.code, self.date, self.price, self.costs)


class Dividend:
    def __init__(self, code, date, per_share, paid):
        self.code = code
        # add functions to parse date into a datetime object
        self.date = date
        self.per_share = per_share
        self.paid = paid

    def __repr__(self):
        return ('dividend of {} on {} for {} at {} per share').format(
               self.paid, self.date, self.code, self.per_share)


def get_opening_positions():
    opening_positions = []
    return opening_positions


def list_opening_positions(opening_positions):
    """
    Prints opening positions in a tabular format, followed by a total
    value in NZD.

    opening_positions: list of shareholdings, as obtained from
    get_opening_positions (i.e. without any updates from trades)

    Code is ignoring currencies for now. An exchange rate of 1 is
    temporarily used for all currencies.
    """
    header_format_string = '{:15} {:>12} {:>10} {:>15} {:8} {:>15}'
    share_format_string = '{:15} {:12,} {:10,.2f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the total line width.
    total = Decimal('0.00')
    print('Opening positions')
    print(header_format_string.format(
        'share code', 'shares held', 'price', 'foreign value', 'currency', 'NZD value'))

    for share in opening_positions:
        value = (share.start_holding * share.start_price).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        NZD_value = value   # assuming temporary FX rate of 1
        print(share_format_string.format(
            share.code, share.start_holding, share.start_price, value, share.currency, NZD_value))
        total += NZD_value

    print(('{:>80}').format('---------------'))
    print(('{:40}{:>40,.2f}').format('total NZD value', total))
    return total


def calc_FDR_basic(opening_positions, FDR_rate):
    """
    ADD BETTER COMMENTS
    :param opening_positions:
    :param FDR_rate:
    :return:
    """
    # ignoring currencies for now
    # this temporarily assumes start_price is in NZD
    FDR_basic = Decimal('0.00')
    currency_FX_rate = Decimal('1')
    for share in opening_positions:
        value = (share.start_holding * share.start_price).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Note that we are first rounding off the value in foreign
        # currency, before additional rounding below. This can only
        # be an issue for shares with fractional holdings.

        FDR_basic += (value * currency_FX_rate * Decimal(FDR_rate)).quantize(
            Decimal('0.01'), rounding = ROUND_HALF_UP)
        # It appears that FIF needs to be calculated for each security.
        # That's why rounding is done per share, after multiplying each
        # share with the FDR_rate.
    return FDR_basic


def get_trades():
    """
    ADD COMMENTS
    :return:
    """
    trades = []
    return trades


def main():
    opening_positions = get_opening_positions()
    list_opening_positions(opening_positions)
    calc_FDR_basic(opening_positions, FDR_RATE)
    trades = get_trades()


if __name__ == '__main__':
    main()
