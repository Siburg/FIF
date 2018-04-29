class Share:
    def __init__(self, code, start_holding=0, start_price=0.0, end_price=0.0, currency='USD'):
        self.code = code
        self.start_holding = start_holding
        self.holding = start_holding
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
        self.charge = share_change * price + costs

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



def main():
    emb = Share('EMB', 11, 100., 110.)
    veu = Share('VEU', 12, 120., 130.)
    print(emb)
    print(veu)

    veu_trade = Trade('VEU', "jan", 10, 115.0, 1.23)
    print(veu_trade)
    emb_divi = Dividend("EMB", 'feb', 0.023, 0.46)
    print(emb_divi)


if __name__ == '__main__':
    main()
