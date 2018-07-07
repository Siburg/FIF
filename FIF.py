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
    opening_holding : number of shares held at start of the tax period.
    holding: current number of shares held, as calculated from other
        inputs.
    opening_price: price per share at start of the tax period.
    closing_price: price per share at end of the tax period.
    currency: currency of the share prices.

    The numerical values for shareholdings and prices are stored as
    Decimals. It is strongly recommended to pass numerical values for
    them as strings (or already in the form of Decimals), so they can
    be accurately converted to Decimals.

    The full share name is not currently a variable in this class.
    Consider it for addition later, or consider splitting the class
    later into a Share class and a Holding class.
    """
    def __init__(self, code, opening_holding='0', opening_price='0.00', closing_price='0.00',
                 currency='USD'):
        """
        Constructor function with defaults set to zero for numerical
        values. Default for currency is USD. Change that if you wish
        another default currency, e.g. AUD.
        """
        self.code = code
        self.opening_holding = Decimal(opening_holding)
        # holding is set to opening_holding (after conversion to Decimal)
        # at initialisation
        self.holding = Decimal(opening_holding)
        self.opening_price = Decimal(opening_price)
        self.closing_price = Decimal(closing_price)
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


def process_opening_positions(opening_shareholdings, FDR_rate):
    """
    Prints opening positions in a tabular format, followed by a opening_value
    value in NZD.

    opening_shareholdings: list of shareholdings, as obtained from
    get_opening_positions (i.e. without any updates from trades)

    Code is ignoring currencies for now. An exchange rate of 1 is
    temporarily used for all currencies.
    """
    header_format_string = '{:15} {:>12} {:>10} {:>15} {:8} {:>15}'
    share_format_string = '{:15} {:12,} {:10,.2f} {:15,.2f} {:8} {:15,.2f}'
    # Note there are spaces between the {} items, so don't forget to
    # count those spaces for the opening_value line width.

    opening_value = Decimal('0.00')
    FDR_basic_income = Decimal('0.00')

    print('Opening positions')
    print(header_format_string.format(
        'share code', 'shares held', 'price', 'foreign value', 'currency', 'NZD value'))

    for share in opening_shareholdings:
        foreign_value = (share.opening_holding * share.opening_price).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Note that we are first rounding off the value in foreign
        # currency, before additional rounding below. This can only
        # be an issue for shares with fractional holdings.

        currency_FX_rate = Decimal('1') # obviously this needs work
        NZD_value = (foreign_value * currency_FX_rate).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Make this a separate rounding as well.
        opening_value += NZD_value

        FDR_basic_income += (NZD_value * Decimal(FDR_rate)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        # It appears that FIF needs to be calculated for each security.
        # That's why final rounding is done per share, after
        # multiplying eachshare with the FDR_rate.

        print(share_format_string.format(
            share.code, share.opening_holding, share.opening_price, foreign_value, share.currency,
            NZD_value))

    print(('{:>80}').format('---------------'))
    print(('{:40}{:>40,.2f}').format('opening_value NZD value', opening_value))
    return opening_value, FDR_basic_income


def get_trades():
    """
    ADD COMMENTS
    :return:
    """
    trades = []
    return trades


def process_trades(trades):
    """

    :param trades:
    :return:
    """
    cost_of_trades = Decimal('0.00')
    return cost_of_trades


def get_dividends():
    """
    ADD COMMENTS
    :return:
    """
    dividends = []
    return dividends


def process_dividends(dividends):
    """

    :param dividends:
    :return:
    """
    net_income_from_dividends = Decimal('0.00')
    return net_income_from_dividends


def get_closing_prices():
    """

    :return:
    """
    return


# consider new function to calculate closing value,
# or refactor the opening value function to generalise it for cloasing as well
def process_closing_prices(shareholdings):
    """

    :param shareholdings:
    :return:
    """
    closing_value = Decimal('0.00')
    return closing_value


def calc_QSA_adjustments():
    """

    :return:
    """
    return


def main():
    shareholdings = get_opening_positions()
    opening_value, FDR_basic_income = process_opening_positions(shareholdings, FDR_RATE)
    trades = get_trades()
    cost_of_trades = process_trades(trades)
    dividends = get_dividends()
    net_income_from_dividends = process_dividends(dividends)
    get_closing_prices(shareholdings)
    closing_value = process_closing_prices(shareholdings)
    # think if we need separate closing function, or generalise opening
    CV_income = closing_value + net_income_from_dividends - (opening_value + cost_of_trades)
    # calculate quick sale adjustments
    QSA_income = calc_QSA_adjustments()
    FDR_income = FDR_basic_income + QSA_income
    FIF_income = max(0, min(FDR_income, CV_income))


if __name__ == '__main__':
    main()
