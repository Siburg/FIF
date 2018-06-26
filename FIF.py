from decimal import Decimal, ROUND_HALF_UP

class Share:
    def __init__(self, code, start_holding='0', start_price='0.00', end_price='0.00', currency='USD'):
        # numerical values are set as string so they can be used in Decimal calculations
        self.code = code
        self.start_holding = start_holding
        self.holding = start_holding
        #note that prices may need to be defined as decimals, but leave out for now
        self.start_price = start_price
        self.end_price = end_price
        self.currency = currency

    def __repr__(self):
        return "%s shareholding is %s" % (self.code, self.holding)


class Trade:
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
    FDR_basic = Decimal('0')
    return FDR_basic



def main():
    FDR_RATE = Decimal('0.05')
    opening_positions = get_opening_positions()


if __name__ == '__main__':
    main()
