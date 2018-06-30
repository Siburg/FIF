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
        add comments
        """
        self.holding += Decimal(increase)
        return self.holding

    def __repr__(self):
        return "%s shareholding is %s shares" % (self.code, self.holding)


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
        return "trade for %s shares of %s on %s at %s with costs of %s"\
               % (self.share_change, self.code, self.date, self.price, self.costs)


class Dividend:
    def __init__(self, code, date, per_share, paid):
        self.code = code
        # add functions to parse date into a datetime object
        self.date = date
        self.per_share = per_share
        self.paid = paid

    def __repr__(self):
        return "dividend of %s on %s for %s at %s per share"\
               % (self.paid, self.date, self.code, self.per_share)


def get_opening_positions():
    opening_positions = []
    return opening_positions


def calc_FDR_basic(opening_positions, FDR_rate):
    # consider testing if FDR_rate is a string; which is at
    # least strongly recommended
    #ignoring currencies for now
    FDR_basic = Decimal('0')
    for position in opening_positions:
        FDR_basic += Decimal(position.start_holding) * Decimal(position.start_price)
    return (FDR_basic * Decimal(FDR_rate)).quantize(Decimal('0.01'), rounding = ROUND_DOWN)


def main():
    FDR_RATE = Decimal('0.05')
    opening_positions = get_opening_positions()


if __name__ == '__main__':
    main()
