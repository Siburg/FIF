"""
A program to calculate Foreign Investment Fund (FIF) income in
accordance with tax rules in New Zealand. It calculates FIF income
using the Fair Dividend Rate (FDR) method and the Comparative Value
(CV) method. The minimum from those two methods is used as final
result for FIF income.

Note that some tax payers may use other methods as well or instead.
Such other methods are not covered by this program.

by Jelle Sjoerdsma
September 2018
version 0.2

No license (yet), but program is intended for public domain and may
be considered open source

Note: current version ignores, and will not work properly, with
transactions such as share splits or share reorganisations.
"""

from collections import namedtuple
import csv
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext
# import json
from operator import attrgetter
import pickle
import sys
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
import dateutil.parser


FAIR_DIVIDEND_RATE = '0.05'   # statutory Fair Dividend Rate of 5%
tax_year = 2018  # hard coded for testing
item_format = namedtuple('item_output_format', 'header, width, precision')
outfmt = {'code': item_format('share code', 16, 16),
                 'full_name': item_format('name / description', 27, 27),
                 'price': item_format('price', 10, 999),
                 'holding': item_format('shares', 13, 999),
                 # Next 2 lines are a bit of kludge to combine
                 # " currency rate" in the header. We also want a
                 # space after printing the previous value, so that
                 # is why we are  right-aligning the 3-letter
                 # currency in a field with a width of 4.
                 'value': item_format('value', 16, 2), 'currency': item_format(' cur', 4, 4),
                 'FX rate': item_format('rency rate', 10, 4),
                 'fees': item_format('fees', 12, 2),
                 'date': item_format(' date ( & time)', 15, 15),
                 'dividend': item_format('gross dividend', 22, 999), 'total width': 112}
fx_rates = {}
"""
    All foreign exchange rates, here and in any other function, must be
    compatible with those used by the IRD, if not directly obtained
    from them. This means foreign values are divided by the fx_rates
    to arrive at NZD values.

"""
# Ending date of 31 March for tax periods is hard coded throughout.
# (Search for   31   if that needs changing.)


class Share:
    """
    Holds information on shares and shareholdings.

    Input arguments:
    code: a code, abbreviation or symbol to identify the share issuer.
    full_name: the name or description of the share issuer and/or class.
    currency: currency of the share prices.
    opening_holding : number of shares held at start of the tax period.
    opening_price: price per share at start of the tax period (in its
        native currency). This shoudl be the same as closing price at
        the end of the previous tax period.

    Other attributes that are available:
    holding: current number of shares held, as calculated from other
        inputs. At the end of the tax period this should be its closing
        holding. Note that this can include fractional shares.
    closing_price: price per share at end of the tax period (in its
        native currency). Note that prices can have more than 2
        decimals.
    opening_value: to be calculated, and remembered, in NZD.
    gross_income_from_dividends: to be calculated, and remembered, in
        NZD.
    cost_of_trades: to be calculated, and remembered, in NZD.
    closing_value: to be calculated, and remembered, in NZD.
    quick_sale_adjustment: to be calculated,  if needed, and
        remembered. If it has a positive value it will be in NZD.

    All numerical values are stored as Decimals. It is strongly
    recommended to pass numerical values for them as strings (or
    already in the form of Decimals), so they can be accurately
    converted to Decimals.

    THINK IF WE NEED A DATE, OR AT LEAST A YEAR INDICATOR for the
    shareholding

    Consider splitting the class later into a Share class and a
    Holding class, or have a list of shareholdings over time inside the
    class.
    """

    def __init__(self, code, full_name='', currency='USD', opening_holding='0',
                 opening_price='0.00'):
        """
        Constructor function with defaults set to zero for numerical
        values. Default for currency is USD. Change that if you wish
        another default currency, e.g. AUD.

        input arguments: as per descriptions for the class.

        return: None
        """
        self.code = code
        self.full_name = full_name
        self.currency = currency
        self.opening_holding = Decimal(opening_holding)
        self.opening_price = Decimal(opening_price)

        # Variables below are not immediately needed when creating the
        # object, but will be used later. They are set up here in
        # preparation and for clarity.
        self.holding = self.opening_holding
        # holding is set to opening_holding (after conversion to
        # Decimal) at initialisation.
        # STILL NEED TO THINK IF THIS RIGHT APPROACH
        self.closing_price = Decimal('0.00')
        self.opening_value = Decimal('0.00')
        self.gross_income_from_dividends = Decimal('0.00')
        self.cost_of_trades = Decimal('0.00')
        self.closing_value = Decimal('0.00')
        self.quick_sale_adjustment = None  # most shares won't need it
        return

    def re_initialise_with_prior_year_closing_values(self):
        """
        Function that can be used at the start of a tax year to reset
        shares with closing values read in from a prior tax year. The
        opening values are set to those prior closing values, and
        closing values are reinitialised.
        Be very careful with this. There is no check if it has run
        previously, and using the function twice could lead to loss
        of information. The program may not need this at all.

        input arguments: none.

        return: None.
        """
        self.opening_holding = Decimal(self.holding)
        self.opening_price = Decimal(self.closing_price)
        self.opening_value = Decimal(self.closing_value)
        self.holding = Decimal(self.holding)    # it could be a string
        self.closing_price = Decimal('0.00')
        self.gross_income_from_dividends = Decimal('0.00')
        self.cost_of_trades = Decimal('0.00')
        self.closing_value = Decimal('0.00')
        self.quick_sale_adjustment = None  # most shares won't need it
        return

    def increase_holding(self, increase):
        """
        Adds Decimal value of increase to holding. This means a
        positive value will increase holding, and a negative value
        will decrease it.

        input arguments:
        increase: number of shares to increase/(decrease) holding with.
            This should be passed as a string (or as Decimal already)
            but will also accept an integer value.

        return: holding (i.e. number of shares) after the increase,
            in Decimal.

        """
        self.holding += Decimal(increase)
        return self.holding

    def __repr__(self):
        return '{} shareholding is {} shares'.format(
            self.code, self.holding)


class Trade:
    """
    Holds information on share trades.
    Could conceivably be replaced with a dict, or a namedtuple, or
    another type of object.

    Input arguments:
    code: the code, abbreviation or symbol to identify the share issuer.
        This can match the code of a share that is part of opening
        holding, or can be for a new share purchased during the tax
        period.
    date_time: the transaction date and time of the trade (during the
        tax period). This should  be in the form of a datetime object.
        The time will be 00:00:00 if there is no information for it.
    number_of_shares: the number of shares acquired in the trade. This
        will be positive for a share acquisition and negative for a
        share disposal. It can include fractional shares.
    share_price: average price of shares traded in the transaction (in
        its native currency). This price may have more than 2 decimals.
    trade_costs: the aggregate costs, fees or charges incurred for
        executing the trade (in addition to the price of the shares
        themselves, e.g. brokerage fees; this is a total cost, not a
        cost per share). These must be in the same currency as the
        share price (for now; otherwise we must allow a separately
        identified currency for the costs component of a trade).

    Other attributes that are available:
    charge: the total costs of an acquisition including trade_costs;
        or the net proceeds from a divestment after deducting trade
        costs (which will almost always be a negative value, unless
        trade costs exceed the gross share disposal proceeds). It is
        in the same currency as the share price (for now). It is not
        rounded and may have more than 2 decimals.
    quick_sale_portion: to be calculated,  if needed. For a share
        disposal it will represent the number of shares (which may be
        all of the trade) that are a Quick Sale. For an acquisition
        it will represent the number of shares that will later be
        part of one or more quick sales. The value will be positive in
        both cases.

    All numerical values are stored as Decimals. It is strongly
    recommended to pass numerical values for them as strings (or
    already in the form of Decimals), so they can be accurately
    converted to Decimals.
    """

    def __init__(self, code, date_time, number_of_shares, share_price, trade_costs='0.00'):
        """
        Constructor function. trade_costs have a default value of
        Decimal(0). charge is calculated from the other inputs.

        input arguments: as per descriptions for the class.

        return: None
        """
        self.code = code
        self.date_time = date_time
        self.number_of_shares = Decimal(number_of_shares)
        self.share_price = Decimal(share_price)
        self.trade_costs = Decimal(trade_costs)
        self.charge = self.number_of_shares * self.share_price + self.trade_costs
        self.quick_sale_portion = None
        return

    def __repr__(self):
        return 'trade for {:,f} shares of {} on {} at {:,.2f} with costs of {:,.2f}'.format(
            self.number_of_shares, self.code, self.date_time, self.share_price,
            self.trade_costs)


class Dividend:
    """
    Holds information on dividens.
    Could conceivably be replaced with a dict, or a namedtuple, or
    another type of object.

    Input arguments:
    code: a code, abbreviation or symbol to identify the share.
    date_paid: the payment date for the dividend (not the declaration
        date or other type of date). This should be in the form of a
        date object (time of the day is irrelevant for dividends).
    per_share: the dividend per share, in its native currency, as
        declared by the issuer. This can have more than 2 decimals.
    gross_paid: the total gross sum paid, before any withholding or
        other taxes, in its native currency, on all eligible shares for
        the dividend.

    Other attributes that are available:
    eligible_shares: the number of shares for which the dividend was
        paid; calculated as gross_paid / per_share. Note that this
        can be different from the number of shares held on the payment
        date, because not all of those may have been eligible (yet) for
        the dividend. This can include fractional shares.

    All numerical values are stored as Decimals. It is strongly
    recommended to pass numerical values for them as strings (or
    already in the form of Decimals), so they can be accurately
    converted to Decimals.

    The class does not yet hold information on withholding or other
    taxes on dividends. This might be added, but is probably too
    tricky because dates for tax paid may not match up with dates
    for dividends paid.
    """

    def __init__(self, code, date_paid, per_share, gross_paid):
        """
        Constructor function. eligible_shares is calculated from the
        other inputs.

        input arguments: as per descriptions for the class.

        return: None
        """
        self.code = code
        self.date_paid = date_paid
        self.per_share = Decimal(per_share)
        self.gross_paid = Decimal(gross_paid)
        # Note that self.gross_paid should be gross before tax, or the
        # calculation below will need to be modified for tax effects.
        self.eligible_shares = (self.gross_paid / self.per_share).quantize(
                Decimal('1'), ROUND_HALF_UP)
        # Assume dividends are only paid on full shares.
        return

    def __repr__(self):
        return 'dividend of {:,.2f} on {} for {} at {} per share'.format(
               self.gross_paid, self.date_paid, self.code, self.per_share)


class IntegerError(Exception):
    """Used to raise error in input processing function."""
    pass


class TooEarlyError(Exception):
    """Used to raise error in input processing function."""
    pass


class TooLateError(Exception):
    """Used to raise error in input processing function."""
    pass


def yes_or_no(question):
    """
    Obtains a yes or no response to the question passed as argument.

    input arguments:
    question: a string holding a question for a yes or no reply. The
        phrase " (Yes/No) " will be added to this question by the
        function.

    return: bool True if response is a form of yes or False if no.

    Allowed responses are "yes", "y", "no" or "n" in any upper, lower
    or mixed case. Any other response leads to repeated input prompts.
    """
    prompt = question + " (Yes/No) "
    while True:
        answer = input(prompt).lower()
        if answer == 'yes' or answer == 'y':
            return True
        if answer == 'no' or answer == 'n':
            return False
        print('That is not a valid response; please try again.')
    # return dummy; can never reach here


def get_date(prompt="Enter date: "):
    """
    Obtains a valid date from user input.

    input arguments:
    prompt: a prompt for the user input, in the form of a string. A
        default prompt is set in the argument list.

    return:
    date_result: a date, in the form of a date object
    """
    question = 'Is that what you intended to enter?'
    again = '\nThat is not a valid entry. Please try again.'

    while True:
        try:
            user_input = input(prompt)
            date_result = dateutil.parser.parse(user_input, dayfirst=True).date()
            print('Your input was read as: {}'.format(date_result.strftime('%d %b %Y')))
            if yes_or_no(question):
                break   # out of the loop; we are finished

            print('Sorry about that; you can try again.')

        except ValueError:
            print(again)

    return date_result


def get_tax_year():
    """
    Obtains the tax year, i.e. the year in which the tax period ends.

    input arguments: none.

    return: the tax year, expressed as an integer

    The tax year is now obtained from manual user input, following a
    prompt and reply. The function could potentially be restructured
    to read the tax year from a file with other date(s). It could even
    be integrated with the get_opening_positions function if that were
    to include a reading of a date to which those positions apply.

    This function is the first one called by the main function. It
    allows the user to enter "quit", instead of a year. If the user
    does that the program will immediately do a hard exit.
    """
    global tax_year
    prompt = 'Enter the year in which the income tax period ends: '
    again = '\nPlease try again (or enter "quit" without quotation marks to exit): '

    while True:
        try:
            user_input = input(prompt)
            if user_input == 'quit':
                print('Program is now exiting')
                sys.exit()
                # This is a hard exit. No need to do anything more.

            if not user_input.isdigit():
                raise IntegerError

            tax_year = int(user_input)
            if tax_year < 2008:
                raise TooEarlyError
            if tax_year > 2100:
                raise TooLateError

            break   # out of the loop, with a valid value, when here.

        except ValueError:
            prompt = 'That is not a valid entry.' + again
        except IntegerError:
            prompt = 'Entry needs to be a whole number.' + again
        except TooEarlyError:
            prompt = 'Calculations do not apply for tax years ending earlier than 31 Mar 2008' \
                + again
        except TooLateError:
            prompt = 'That seems an implausably late year.' + again

    return tax_year


def previous_closing_date():
    return date(tax_year - 1, 3, 31)


def closing_date():
    return date(tax_year, 3, 31)


def get_new_fx_rate(currency, fx_date, fx_rates):
    """
    Obtains a foreign exchange rate for the currency and day specified
    in the argument list. The obtained rate is then added to the
    dictionary with fx_rates.

    input arguments:
    currency: the currency for which we need the exchange rate.
    fx_date: the date for which we need the exchange rate. This must be
        passed in the form of a date object.
    fx_rates: a nested dictionary with foreign exchange rates by
        currency and by date (as a date object).

    return: the desired foreign exchange rate, as a string.

    other data changes (to mutable objects in arguments):
    fx_rates is updated with the new fx_rate.

    This function also allows the user to enter "quit", instead of an
    exchange rate. If the user does that the program will immediately
    do a hard exit.
    """

    if fx_date.month == 3 and fx_date.day == 31:
        # Assume we are dealing with tax period closing date. It is
        # still possible to enter a rolling average rate for March
        # if desired. This could lead to the same rolling average rate
        # being entered twice -- for 15 March and for 31 March -- but
        # so be it.
        rate_date = fx_date
        prompt = 'Enter ' + currency + ' currency rate for 31/03/' + \
            str(fx_date.year) + ' : '
    else:
        # Assume we want, and will save, an IRD mid-month rate. This
        # could be a rolling average rate.
        rate_date = date(fx_date.year, fx_date.month, 15)
        # This is redundant if this function will only be called from
        # FX_rate() but is harmless to leave in.
        prompt = 'Enter ' + currency + ' currency rate for 15/' + \
            str(fx_date.month) + '/' + str(fx_date.year) + ' : '

    again = '\nPlease try again (or enter "quit" without quotation marks to exit): '

    while True:
        try:
            fx_rate = input(prompt)
            if fx_rate == 'quit':
                print('Program is now exiting')
                sys.exit()
                # This is a hard exit. No need to do anything more.

            check_value_error = float(fx_rate)
            # This statement only serves to raise a ValueError if it
            # fails. Also consider adding a check to limit entries to
            # 4 decimals

            break   # out of the loop, with a valid value, when here.

        except ValueError:
            prompt = 'That is not a valid entry.' + again

    fx_rates[currency][rate_date] = fx_rate

    return fx_rate


def FX_rate(currency, fx_date):
    """

    :param currency:
    :param date:
    :param conversion_method:
    :return:
    """
    if fx_date.month == 3 and fx_date.day == 31:
        # Assume we are dealing with a tax period closing date.
        rate_date = fx_date
    else:
        # Assume we want, and will use, an IRD mid-month rate. This
        # could be a rolling average rate.
        rate_date = date(fx_date.year, fx_date.month, 15)

    if currency in fx_rates and rate_date in fx_rates[currency]:
        fx_rate = fx_rates[currency][rate_date]
    else:
        fx_rate = get_new_fx_rate(currency, rate_date, fx_rates)

    return Decimal(fx_rate)


def get_new_share_currency_and_full_name(trade):
    """

    :param trade:
    :return:
    """

    prompt = ('{0} is for a share that is not yet in the system.\n' +
              'Enter the currency code in which that share trades (e.g. USD): ').format(
        repr(trade))
    currency = input(prompt)

    while currency not in fx_rates:
        print('The system does not have any information for currency code ' + currency)
        currency = input('Please enter a valid code (from ISO4217) for an existing currency')

    full_name = input('Enter the full share name or description for ' +
                      trade.code + ' : ')
    # Consider adding a while loop to ensure we get a string value.
    # Also consider if we allow a blank return.
    # Also consider a sentinel value such as "quit" allowing the user
    # exit the program altogether.
    return full_name, currency


def get_fx_rates(fx_rates, filename='saved_fx_rates.pickle'):
    """

    :rtype: object
    :param fx_rates:
    :return:
    """
    with open(filename, 'rb') as fx_rates_save_file:
        fx_rates = pickle.load(fx_rates_save_file)
    return fx_rates


def get_opening_positions():
    """
    Creates the list of shares with opening positions that will be used
    as starting point for all subsequent processing.

    input arguments: none

    return:
    opening_positions: list of Share instances with information for each
        share at the opening of the tax period.

    For shares that were already held at the end of the previous tax
    period, the information on opening positions must be the same as
    that of the closing positions in the previous year. For example,
    the price at opening must be the same as the closing price at the
    end of the prior period. This means the closing price on 31 March;
    not a potential market opening price on 1 April. Foreign exchange
    rates must also be those for 31 March of the previous tax period;
    not those for 1 April.

    The opening_shares list may also include information on shares with
    a zero opening position. This could be useful to have starting
    information with the code, full_name, and currency of shares that
    are subsequently acquired during the year.

    The function is now designed to only read such information from a
    csv file. It may be extended with additional input methods.
    """
    opening_positions = []
    filename = '/home/jelle/Documents/2017 Mar/Jelle/2017_closing_share_info.csv'
    # print('Select file with opening positions, i.e. closing share info from the previous year')
    # filename = askopenfilename()
    Tk().withdraw
    # This is to remove the GUI window that was opened.
    if filename is None:
        print('The program does not have an input file to work with. It is now exiting!')
        sys.exit()
        # This is a hard exit. No need to do anything more.

    with open(filename, newline='') as shares_file:
        reader = csv.DictReader(shares_file)
        for row in reader:
            if 'full_name' in row:
                full_name = row['full_name']
            else:
                full_name = ''

            if 'currency' in row:
                currency = row['currency']
            else:
                currency = 'USD'

            opening_share = Share(row['code'], full_name, currency,
                    row['holding'], row['closing_price'])
            opening_positions.append(opening_share)

    return opening_positions


def process_opening_positions(opening_shares):
    """
    Calculates NZD value of each share held at opening, sets that value
    for the share, and calculates total NZD value across shares. Also
    calculates FRD basic income (without quick sale adjustments).
    First for each share individually, and then the combined total.
    Prints inputs and results in a tabular format.

    input arguments:
    opening_shares: list of shares, as obtained from
        get_opening_positions (i.e. without any updates from trades)

    return: (tuple with)
    total_opening_value: in NZD
    FDR_basic_income: total from calculations (and roundings) per share

    other data changes (to mutable objects in arguments):
    opening_value for each Share in opening_shares is set.
    """
    total_opening_value = Decimal('0.00')
    FDR_basic_income = Decimal('0.00')

    header_format_string = '{v1:{w1}}' + '{v2:{w2}}' + '{v3:>{w3}}' + '{v4:>{w4}}' + \
        '{v5:>{w5}}' + '{v6:{w6}}' + '{v7:{w7}}' + '{v8:>{w8}}'
    share_format_string = '{v1:{w1}.{p1}}' + '{v2:{w2}.{p2}}' + '{v3:>{w3},}' + \
        '{v4:>{w4},}' + '{v5:>{w5},.{p5}f}' + '{v6:>{w6}}' + '{v7:>{w7},.{p7}f}' + \
        '{v8:>{w8},.{p8}f}'
    # Note that share price may have more than 2 decimals.
    print('\nOpening positions, based on previous closing positions for 31 Mar {}'.format(
        tax_year - 1))
    print(header_format_string.format(
        v1 = outfmt['code'].header, w1 = outfmt['code'].width,
        v2=outfmt['full_name'].header, w2=outfmt['full_name'].width,
        v3=outfmt['price'].header, w3=outfmt['price'].width,
        v4=outfmt['holding'].header, w4=outfmt['holding'].width,
        v5='foreign value', w5=outfmt['value'].width,
        v6=outfmt['currency'].header, w6=outfmt['currency'].width,
        v7=outfmt['FX rate'].header, w7=outfmt['FX rate'].width,
        v8='NZD value', w8=outfmt['value'].width))
    print(outfmt['total width'] * '-')

    for share in opening_shares:
        foreign_value = (share.opening_holding * share.opening_price).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Note that we are first rounding off the value in foreign
        # currency, before additional rounding below. This can only
        # be an issue for shares with fractional holdings.

        fx_rate = FX_rate(share.currency, previous_closing_date())
        NZD_value = (foreign_value / fx_rate).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
        # Make this a separate rounding as well.

        # Next statement stores the result in Share object
        share.opening_value = NZD_value
        total_opening_value += NZD_value

        FDR_basic_income += (NZD_value * Decimal(FAIR_DIVIDEND_RATE)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP)
        # It appears that FIF needs to be calculated for each security.
        # That's why final rounding is done per share, after
        # multiplying each share with the fair_dividend_rate.

        print(share_format_string.format(
            v1 = share.code, w1 = outfmt['code'].width, p1 = outfmt['code'].precision,
            v2 = share.full_name, w2=outfmt['full_name'].width, p2=outfmt['full_name'].precision,
            v3 = share.opening_price, w3=outfmt['price'].width,
            v4 = share.opening_holding, w4=outfmt['holding'].width,
            v5 = foreign_value, w5=outfmt['value'].width, p5=outfmt['value'].precision,
            v6 = share.currency, w6=outfmt['currency'].width,
            v7 = fx_rate, w7=outfmt['FX rate'].width, p7=outfmt['FX rate'].precision,
            v8 = NZD_value, w8=outfmt['value'].width, p8=outfmt['value'].precision))

    print('{:>{w}}'.format(outfmt['value'].width * '-', w=outfmt['total width']))
    print('{v1:{w1}}{v2:>{w2},.{p2}f}\n'.format(
        v1 = 'total opening value', w1 = outfmt['total width'] - outfmt['value'].width,
        v2 = total_opening_value, w2 = outfmt['value'].width, p2 = outfmt['value'].precision))

    return total_opening_value, FDR_basic_income


def get_trades():
    """
    Creates the list of share trades that took place, if any.

    input arguments: none

    return:
    trades: list of Trade instances with information for each
        trade (i.e. acquisition or disposal of shares) made during the
        tax period. The list may be empty.

    The function is now designed to only read such information from a
    csv file. It may be extended with additional input methods.
    """
    trades = []
    filename = '/home/jelle/Documents/2018 Mar/Jelle/2018_trades.csv'

    # print('Select csv file with information on trades')
    # filename = askopenfilename()
    # Tk().withdraw
    with open(filename, newline='') as trades_file:
        reader = csv.DictReader(trades_file)
        for row in reader:
            # use row fields as defined in Interactive Brokers csv output
            if row['Header'] != 'Data':
                continue
                # skip rows with sub-totals and totals

            trade_date_time = dateutil.parser.parse(row['Date/Time'], yearfirst=True)

            if previous_closing_date() < trade_date_time.date() <= closing_date():
                # Strictly speaking this test should be unnecssary, but
                # we just want to make sure we only deal with trades
                # falling inside the tax year.
                trade_costs = -Decimal(row['Comm/Fee'])
                # Interactive Brokers has Comm/Fee as negative value,
                # so we need to convert it here from the string that is
                # being read.

                trade = Trade(row['Symbol'], trade_date_time, row['Quantity'],
                              row['T. Price'], trade_costs)
                trades.append(trade)

    return trades


def process_trades(shares, trades):
    """

    :param trades:
    :return:
    """
    total_cost_of_trades = Decimal('0.00')
    any_quick_sale_adjustment = False
    trades.sort(key=attrgetter('date_time'))
    # Sorting the trades by date and time is necessary to work out the
    # need for a quick sale adjustment, and to properly calculate such
    # an adjustment later if needed.
    # The sort is done in place, and trades is a mutable object, so the
    # sorting should be retained for later use of the trades list
    # outside this function as well.

    # First, ensure there are share instances for every trade
    for trade in trades:
        # Check if we do not have a matching share code.
        # consider changing the if to a while, in order to ensure
        # we can never process unmatching trades. That may require
        # some revamping of the code in such a while loop.
        if not any(share.code == trade.code for share in shares):
            full_name, currency = get_new_share_currency_and_full_name(trade)
            new_share = Share(trade.code, full_name, currency)
            shares.append(new_share)

    # After this we should have a share instance to match every trade.
    # For cosmetic output reasons, and probably greater efficiency,
    # we now process all trades aggregated by share.

    header_format_string = '{v1:{w1}}' + '{v2:{w2}}' + '{v3:>{w3}}' + '{v4:>{w4}}'+ \
        '{v5:>{w5}}' + '{v6:>{w6}}' + '{v7:>{w7}}' + '{v8:>{w8}}' + '{v9:>{w9}}'
    trade_format_string = '{v1:{w1}.{p1}}' + '{v2:{w2}.{p2}}' + '{v3:>{w3},.{p3}f}' + \
        '{v4:>{w4},.{p4}f}' + '{v5:>{w5},}' + '{v6:>{w6},.{p6}f}' + '{v7:>{w7}}' + \
        '{v8:>{w8},.{p8}f}' + '{v9:>{w9},.{p9}f}'
    print('\nTrades: share acquisitions (positive) and disposals (negative)')
    print(header_format_string.format(
        v1 = outfmt['code'].header, w1 = outfmt['code'].width,
        v2=outfmt['date'].header, w2=outfmt['date'].width,
        v3=outfmt['fees'].header, w3=outfmt['fees'].width,
        v4=outfmt['price'].header, w4=outfmt['price'].width,
        v5=outfmt['holding'].header, w5=outfmt['holding'].width,
        v6='foreign value', w6=outfmt['value'].width,
        v7=outfmt['currency'].header, w7=outfmt['currency'].width,
        v8=outfmt['FX rate'].header, w8=outfmt['FX rate'].width,
        v9='NZD value', w9=outfmt['value'].width))
    print(outfmt['total width'] * '-')

    for share in shares:
        share_cost_of_trades = Decimal('0.00')
        shares_acquired = False
        for trade in filter(lambda trade: trade.code == share.code, trades):

            share.increase_holding(trade.number_of_shares)

            fx_rate = FX_rate(share.currency, trade.date_time.date())
            NZD_value = (trade.charge / fx_rate).quantize(
                Decimal('0.01'), ROUND_HALF_UP)

            # This is why there is an outer loop. If a separate
            # total by share is not needed then the inner loop
            # would be enough.
            share_cost_of_trades += NZD_value

            if trade.number_of_shares > Decimal('0'):
                shares_acquired = True
            elif shares_acquired and trade.number_of_shares < Decimal('0'):
                share.quick_sale_adjustment = True
            # Here we are enjoying Python's duck typing, changing
            # value from None to True, in preparation for later
            # assigning a Decimal value to quick_sale_adjustment.
            # The test for number_of_shares < 0 may be overkill,
            # but is there just in case we encounter a bizarre
            # situation where a trade record would be for 0 shares.

            if trade.share_price.as_tuple().exponent >= -2:
                price_precision = 2
            else:
                price_precision = 4
            # This works for share_price in Decimal format. If it has
            # more than 2 digits after the point than limit the print
            # precision to 4 digits.

            print(trade_format_string.format(
                v1=share.code, w1=outfmt['code'].width, p1=outfmt['code'].precision,
                v2=trade.date_time.strftime('%d %b %X'), w2=outfmt['date'].width,
                    p2=outfmt['date'].precision,
                v3=trade.trade_costs, w3=outfmt['fees'].width, p3=outfmt['fees'].precision,
                v4=trade.share_price, w4=outfmt['price'].width, p4=price_precision,
                v5=trade.number_of_shares, w5=outfmt['holding'].width,
                v6=trade.charge, w6=outfmt['value'].width, p6=outfmt['value'].precision,
                v7=share.currency, w7=outfmt['currency'].width,
                v8=fx_rate, w8=outfmt['FX rate'].width, p8=outfmt['FX rate'].precision,
                v9=NZD_value, w9=outfmt['value'].width, p9=outfmt['value'].precision))

        share.cost_of_trades = share_cost_of_trades
        # update the quick sale adjustment to something else than None
        # E.g. use -1 as value to indicate it needs to be calculated
        total_cost_of_trades += share_cost_of_trades
        if share.quick_sale_adjustment:
            any_quick_sale_adjustment = True

    print('{:>{w}}'.format(outfmt['value'].width * '-', w=outfmt['total width']))
    print('{v1:{w1}}{v2:>{w2},.{p2}f}\n'.format(
        v1 = 'total net cost of trades / (proceeds from disposals)',
            w1 = outfmt['total width'] - outfmt['value'].width,
        v2 = total_cost_of_trades, w2 = outfmt['value'].width, p2 = outfmt['value'].precision))
    # cost_of_trades in share instances have been
    # updated as well. Because shares is a mutable list, this does not
    # need to be part of the return.
    return total_cost_of_trades, any_quick_sale_adjustment


def get_dividends():
    """
    Creates the list with information on dividends received during the
    tax period.

    input arguments: none

    return:
    dividends: list of Dividend instances with information for each
        dividend received during the tax period. The list may be empty.
    """
    dividends = []
    filename = '/home/jelle/Documents/2018 Mar/Jelle/2018_dividends.csv'
    # filename = askopenfilename()
    # Tk().withdraw
    with open(filename, newline='') as dividends_file:
        reader = csv.DictReader(dividends_file)
        for row in reader:
            # use row fields as defined in Interactive Brokers csv output
            date_paid = dateutil.parser.parse(row['Date'], yearfirst=True).date()
            if previous_closing_date() < date_paid <= closing_date():
                # Strictly speaking this test should be unnecssary, but
                # we just want to make sure we only deal with dividends
                # falling inside the tax year.

                gross_paid = row['Amount']
                description = row['Description']
                # Next 2 statements assume that share code is first item
                # in description, followed by something between
                # brackets. There may not be a space before the bracket.
                # If there is a space before the bracket we need to
                # strip it from the code.
                first_split = description.split('(')
                code = first_split[0].strip()
                # Following assumes that the value of dividend per
                # share is the only floating point item in the
                # text after the first bracket of the description, and
                # before any next bracket, with a space separating the
                # items.
                second_split = first_split[1].split()
                for item in second_split:
                    try:
                        per_share = float(item)
                        # If we do NOT get a ValueError we have found
                        # what we are looking for. However, we actually
                        # want the string value, in order to convert
                        # it to Decimal in the Dividend constructor.
                        per_share = item
                        break
                        # When we find it
                    except ValueError:
                        continue
                        # Try the next item

                dividend = Dividend(code, date_paid, per_share, gross_paid)
                dividends.append(dividend)

    return dividends


def process_dividends(shares, dividends):
    """

    :param dividends:
    :return:
    """
    total_income_from_dividends = Decimal('0.00')

    header_format_string = '{v1:{w1}}' + '{v2:{w2}}' + '{v3:>{w3}}' + '{v4:>{w4}}' + \
        '{v5:>{w5}}' + '{v6:{w6}}' + '{v7:{w7}}' + '{v8:>{w8}}'
    dividend_format_string = '{v1:{w1}.{p1}}' + '{v2:{w2}}' + '{v3:>{w3},}' + \
        '{v4:>{w4},}' + '{v5:>{w5},.{p5}f}' + '{v6:>{w6}}' + '{v7:>{w7},.{p7}f}' + \
        '{v8:>{w8},.{p8}f}'
    print('\nDividends')
    print(header_format_string.format(
        v1 = outfmt['code'].header, w1 = outfmt['code'].width,
        v2='payment date', w2=outfmt['date'].width,
        v3=outfmt['dividend'].header, w3=outfmt['dividend'].width,
        v4=outfmt['holding'].header, w4=outfmt['holding'].width,
        v5='foreign value', w5=outfmt['value'].width,
        v6=outfmt['currency'].header, w6=outfmt['currency'].width,
        v7=outfmt['FX rate'].header, w7=outfmt['FX rate'].width,
        v8='NZD value', w8=outfmt['value'].width))
    print(outfmt['total width'] * '-')

    for share in shares:
        share_income_from_dividends = Decimal('0.00')
        for dividend in filter(lambda dividend: dividend.code == share.code, dividends):
            fx_rate = FX_rate(share.currency, dividend.date_paid)
            NZD_value = (dividend.gross_paid / fx_rate).quantize(
                Decimal('0.01'), ROUND_HALF_UP)

            # This is why there is an outer loop. If a separate
            # total by share is not needed then the inner loop
            # would be enough.
            share_income_from_dividends += NZD_value
            print(dividend_format_string.format(
                v1=share.code, w1=outfmt['code'].width, p1=outfmt['code'].precision,
                v2=dividend.date_paid.strftime('%d %b'), w2=outfmt['date'].width,
                v3=dividend.per_share, w3=outfmt['dividend'].width,
                v4=dividend.eligible_shares, w4=outfmt['holding'].width,
                v5=dividend.gross_paid, w5=outfmt['value'].width, p5=outfmt['value'].precision,
                v6=share.currency, w6=outfmt['currency'].width,
                v7=fx_rate, w7=outfmt['FX rate'].width, p7=outfmt['FX rate'].precision,
                v8=NZD_value, w8=outfmt['value'].width, p8=outfmt['value'].precision))

        share.gross_income_from_dividends = share_income_from_dividends
        total_income_from_dividends += share_income_from_dividends

    print('{:>{w}}'.format(outfmt['value'].width * '-', w=outfmt['total width']))
    print('{v1:{w1}}{v2:>{w2},.{p2}f}\n'.format(
        v1 = 'total gross income (before tax deductions) from dividends',
            w1 = outfmt['total width'] - outfmt['value'].width,
        v2 = total_income_from_dividends, w2 = outfmt['value'].width, p2 = outfmt['value'].precision))
    # gross_income_from_dividends in share instances have been
    # updated as well. Because shares is a mutable list, this does not
    # need to be part of the return.
    return total_income_from_dividends


def get_closing_prices(shares):
    """
    Creates the list with closing prices for shares.

    input arguments:
    shares: the list of shares with their holdings at the end of the
        tax period, i.e. their closing positions. (This list is only
        needed to check that we get a closing price for every share
        with a non-zero holding at the end of the tax period. If we do
        not make such a check then we don't need any input argument.)

    return:
    closing prices: list of named tuples with closing_price_info.
        Each such tuple contains:
        code: this must match the code in an existing  Share instance.
        price: the closing price, at the end of the tax period, for
            the share with that code.
    The list may be empty.

    closing_price_info is required for every share with a non-zero
    closing position, i.e. a holding other than zero at the end of the
    tax period. It may also be provided for shares with a zero holding
    at the end of the tax period, but is not required for those shares.

    The function is now designed to only read information from a
    csv file. It may be extended with additional input methods.
    """
    closing_prices = []
    closing_price_info = namedtuple('closing_price_info', 'code, price')
    filename = '/home/jelle/Documents/2018 Mar/Jelle/2018_closing_prices.csv'

    # filename = askopenfilename()
    # Tk().withdraw
    with open(filename, newline='') as closing_prices_file:
        reader = csv.DictReader(closing_prices_file)
        for row in reader:
            row_info = closing_price_info(code=row['code'], price=row['price'])
            closing_prices.append(row_info)

    # Consider adding functionality to check that we have a closing
    # price for every share with a closing holding, and to ensure we
    # get it if not.

    return closing_prices


def process_closing_prices(shares, closing_prices):
    """

    :param shares:
    :return:

    """
    total_closing_value = Decimal('0.00')

    header_format_string = '{v1:{w1}}' + '{v2:{w2}}' + '{v3:>{w3}}' + '{v4:>{w4}}' + \
        '{v5:>{w5}}' + '{v6:{w6}}' + '{v7:{w7}}' + '{v8:>{w8}}'
    share_format_string = '{v1:{w1}.{p1}}' + '{v2:{w2}.{p2}}' + '{v3:>{w3},}' + \
        '{v4:>{w4},}' + '{v5:>{w5},.{p5}f}' + '{v6:>{w6}}' + '{v7:>{w7},.{p7}f}' + \
        '{v8:>{w8},.{p8}f}'
    # Note that share price may have more than 2 decimals. That is no
    # problem for storing and processing, but think about how to
    # show that in print (or not).
    print('\nClosing positions for 31 Mar {}'.format(tax_year))
    print(header_format_string.format(
        v1=outfmt['code'].header, w1=outfmt['code'].width,
        v2=outfmt['full_name'].header, w2=outfmt['full_name'].width,
        v3=outfmt['price'].header, w3=outfmt['price'].width,
        v4='shares held', w4=outfmt['holding'].width,
        v5='foreign value', w5=outfmt['value'].width,
        v6=outfmt['currency'].header, w6=outfmt['currency'].width,
        v7=outfmt['FX rate'].header, w7=outfmt['FX rate'].width,
        v8='NZD value', w8=outfmt['value'].width))
    print(outfmt['total width'] * '-')

    for closing_price_info in closing_prices:
        # Assume that we did indeed obtain a closing price for every
        # share with a closing holding > 0. This functionality can be
        # forced in get_closing_prices.
        # Don't use filter function here because there is only one
        # share per closing price so we can break out of the inner loop
        # as soon as we find it.
        for share in shares:
            # assume the lists are not sorted by share code
            if share.code == closing_price_info.code:
                share.closing_price = Decimal(closing_price_info.price)

                foreign_value = (share.holding * share.closing_price).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)
                # Note that we are first rounding off the value in foreign
                # currency, before additional rounding below. This can only
                # be an issue for shares with fractional holdings.

                fx_rate = FX_rate(share.currency, closing_date())
                NZD_value = (foreign_value / fx_rate).quantize(
                    Decimal('0.01'), ROUND_HALF_UP)
                # Make this a separate rounding as well.

                # Next statement stores the result in Share object
                share.closing_value = NZD_value
                total_closing_value += NZD_value

                print(share_format_string.format(
                    v1=share.code, w1=outfmt['code'].width, p1=outfmt['code'].precision,
                    v2=share.full_name, w2=outfmt['full_name'].width,
                    p2=outfmt['full_name'].precision,
                    v3=share.closing_price, w3=outfmt['price'].width,
                    v4=share.holding, w4=outfmt['holding'].width,
                    v5=foreign_value, w5=outfmt['value'].width, p5=outfmt['value'].precision,
                    v6=share.currency, w6=outfmt['currency'].width,
                    v7=fx_rate, w7=outfmt['FX rate'].width,
                        p7=outfmt['FX rate'].precision,
                    v8=NZD_value, w8=outfmt['value'].width, p8=outfmt['value'].precision))

                break   # the inner loop after matching share is found

    # Also print shares that do not have a closing price or value.
    # This could risk double printing if a zero price is included in
    # the closing_prices list, but is otherwise harmless.
    for share in shares:
        if share.closing_price == Decimal(0) or share.closing_value == Decimal(0):
            print(share_format_string.format(
                v1=share.code, w1=outfmt['code'].width, p1=outfmt['code'].precision,
                v2=share.full_name, w2=outfmt['full_name'].width,
                    p2=outfmt['full_name'].precision,
                v3=share.closing_price, w3=outfmt['price'].width,
                v4=share.holding, w4=outfmt['holding'].width,
                v5=0.0, w5=outfmt['value'].width, p5=outfmt['value'].precision,
                v6=share.currency, w6=outfmt['currency'].width,
                v7=0.0, w7=outfmt['FX rate'].width,
                    p7=outfmt['FX rate'].precision,
                v8=0.0, w8=outfmt['value'].width, p8=outfmt['value'].precision))

    print('{:>{w}}'.format(outfmt['value'].width * '-', w=outfmt['total width']))
    print('{v1:{w1}}{v2:>{w2},.{p2}f}\n'.format(
        v1 = 'total closing value', w1 = outfmt['total width'] - outfmt['value'].width,
        v2 = total_closing_value, w2 = outfmt['value'].width, p2 = outfmt['value'].precision))

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

    filename = asksaveasfilename()
    Tk().withdraw
    share_fields = shares[0].__dict__.keys()
    with open(filename, 'w', newline='') as shares_save_file:
        writer = csv.DictWriter(shares_save_file, fieldnames=share_fields)
        writer.writeheader()
        for share in shares:
            writer.writerow(share.__dict__)

    # for share in shares:
    #     json_item = json.dumps(share, default = lambda x: x.__dict__)
    #     print(json_item)
    return


def save_fx_rates(fx_rates, filename='saved_fx_rates.pickle'):
    """

    :rtype: object
    :param fx_rates:
    :return:
    """
    with open(filename, 'wb') as fx_rates_save_file:
        pickle.dump(fx_rates, fx_rates_save_file)
    return


def calc_comparative_value_income(opening_value, cost_of_trades,
                                  gross_income_from_dividends, closing_value):
    """
    Calculates and prints the comparative value income.

    input arguments (which have all been returned by earlier functions):
    opening_value
    cost_of_trades
    gross_income_from_dividends
    closing_value

    return
    CV_income: the calculated comparative value income

    Note that this probably needs to be adjusted for tax effects, e.g.
    by using net income from dividends.
    """
    CV_income = closing_value + gross_income_from_dividends - (opening_value + cost_of_trades)

    print('\nComparative Value income calculation')
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'total closing value', w1 = 55, v2 = closing_value, w2 = 20))
    # Need to amend below to show net income from dividends
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'total gross income from dividends', w1 = 55,
            v2 = gross_income_from_dividends, w2 = 20))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'net proceeds from disposals/(costs of acquisitions)', w1 = 55,
            v2 = -cost_of_trades, w2 = 20))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'total opening value', w1 = 55,
            v2 = -opening_value, w2 = 20))
    print('{v1:{w1}}{v2:>{w2}}'.format(
            v1 = '', w1 = 55, v2 = 16 * '-', w2 = 20))
    print('{v1:{w1}}{v2:>{w2},.2f}\n'.format(
            v1 = 'Comparative Value income', w1 = 55, v2 = CV_income, w2 = 20))

    return CV_income


def calc_QSA(share, trades, dividends):
    """

    :return:
    """
    share_trades = []
    for trade in filter(lambda trade: trade.code == share.code, trades):
        share_trades.append(trade)
    share_trades.sort(reverse=False, key = attrgetter('date_time'))

    closing_holding = share.holding
    # Because we already traversed all trades when processing them
    # the first time.
    holding = share.opening_holding
    peak_holding = Decimal('0')
    acquired_shares = Decimal('0')
    acquisition_costs = Decimal('0.00')
    quick_sale_shares = Decimal('0')
    quick_sale_proceeds = Decimal('0.00')
    for trade in share_trades:
        if trade.share_price == Decimal('0'):
            continue
            # This is intended to weed out quasi-trades, if entered,
            # that represent transactions such as share splits.

        holding += trade.number_of_shares
        if holding > peak_holding:
            peak_holding = holding

        fx_rate = FX_rate(share.currency, trade.date_time.date())

        if trade.number_of_shares > Decimal('0'):
            acquired_shares += trade.number_of_shares
            acquisition_costs += (trade.charge / fx_rate).quantize(Decimal('0.01'), ROUND_HALF_UP)
        else:
            shares_sold = -trade.number_of_shares
            # Changing it to a positive value in this context.
            quick_sale_portion = min(shares_sold, acquired_shares - quick_sale_shares)
            # At this point, quick_sale_shares has the previous balance
            # of (the portions of) shares sold as a quick sale.
            trade.quick_sale_portion = quick_sale_portion
            # After this, trade.quick_sale_portion for each share
            # disposal has a Decimal value (which could be zero). It
            # will no longer be None.
            quick_sale_shares += quick_sale_portion
            quick_sale_proceeds += ((quick_sale_portion / shares_sold) *
                    -trade.charge / fx_rate).quantize(Decimal('0.01'), ROUND_HALF_UP)
            # This will also be a positive value, assuming that the
            # trade charge will always be negative.

    if holding != closing_holding:
        # It normally should be equal after we have run through all
        # trades again.
        print('Trades included a transaction with a share price of zero, probably for ' +
              'a transaction such as a share split.')
        print('The program cannot calculate the quick sale adjustment for this situation.')
        return Decimal('0.00')
        # Exiting early
        # We could also return a very large number to mess up all
        # calculations, but that could be annoying.

    share_trades.sort(reverse=True, key = attrgetter('date_time'))
    # We are now going to traverse the share trades again, but this
    # time in reverse order by date so that we can find the portion of
    # each individual acquisition that contributed to a later quick
    # sale, and then calculate the dividend income on the quick sale
    # holding balances.
    share_dividends = []
    for dividend in filter(lambda dividend: dividend.code == share.code, dividends):
        share_dividends.append(dividend)
    # This is a first filter on dividends. It may save time for the
    # second filter we will use later.
    share_dividends.sort(reverse=True, key = attrgetter('date_paid'))
    # This is not necessary for the calculation, but it allows any
    # print out to be in the same reverse order by date as trades.

    end_date = closing_date()
    quick_sale_balance = Decimal('0')
    for trade in share_trades:
        start_date = trade.date_time.date()
        for dividend in filter(lambda dividend:
                start_date <= dividend.date_paid < end_date, share_dividends):
            print(dividend)

        if trade.number_of_shares < Decimal('0'):
            quick_sale_balance += trade.quick_sale_portion
        else:
            quick_sale_portion = min(trade.number_of_shares, quick_sale_balance)
            trade.quick_sale_portion = quick_sale_portion
            # After this, trade.quick_sale_portion for each share
            # acquisition also has a Decimal value (which could be
            # zero). It will no longer be None.
            quick_sale_balance -= quick_sale_portion
        print(trade.date_time, trade.number_of_shares, trade.quick_sale_portion, quick_sale_balance)
        end_date = start_date

    peak_differential = min(peak_holding - share.opening_holding, peak_holding - closing_holding)
    average_cost_of_acquisition = acquisition_costs / acquired_shares
    peak_holding_adjustment = (Decimal(FAIR_DIVIDEND_RATE) * peak_differential *
            average_cost_of_acquisition).quantize(Decimal('0.01'), ROUND_HALF_UP)
    quick_sale_costs = (quick_sale_shares * average_cost_of_acquisition).quantize(
            Decimal('0.01'), ROUND_HALF_UP)
    quick_sale_gain = quick_sale_proceeds - quick_sale_costs

    width1 = 18
    width2 = 45

    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'shares acquired: ', w1 = width2,
            v2 = acquired_shares, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'total acquisition costs: ', w1 = width2,
            v2 = acquisition_costs, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},.4f}'.format(
            v1 = 'average acquisition cost per share: ', w1 = width2,
            v2 = average_cost_of_acquisition, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'shares sold subject to QSA: ', w1 = width2,
            v2 = quick_sale_shares, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'proceeds from shares sold subject to QSA: ', w1 = width2,
            v2 = quick_sale_proceeds, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'costs of those (based on average per share): ', w1 = width2,
            v2 = quick_sale_costs, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'capital gain/(loss) from quick sales: ', w1 = width2,
            v2 = quick_sale_gain, w2 = 10))
    if quick_sale_gain < 0:
        print('quick sale gain cannot be negative')
        quick_sale_gain = Decimal('0.00')
    print('{v1:{w1}}{v2:>{w2},.2f}'.format(
            v1 = 'Quick sale gain: ', w1 = width2,
            v2 = quick_sale_gain, w2 = 10))


    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'opening holding: ', w1 = width1,
            v2 = share.opening_holding, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'closing holding: ', w1 = width1,
            v2 = closing_holding, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'peak holding: ', w1 = width1,
            v2 = peak_holding, w2 = 10))
    print('{v1:{w1}}{v2:>{w2},}'.format(
            v1 = 'peak differential (minimum): ', w1 = width2,
            v2 = peak_differential, w2 = 10))
    print('{v1:{w1}}{v2:{w2}.0%}{v3:{w3}}{v4:>{w4},.2f}'.format(
            v1 = 'Peak holding adjustment (at ', w1 = 28,
            v2 = Decimal(FAIR_DIVIDEND_RATE), w2 = 2,
            v3 = '): ', w3 = width2 - (28 + 2),
            v4 = peak_holding_adjustment, w4 = 10))

    quick_sale_adjustment = min(peak_holding_adjustment, quick_sale_gain)
    share.quick_sale_adjustment = quick_sale_adjustment
    return quick_sale_adjustment


def determine_FDR_income(FDR_basic_income, any_quick_sale_adjustment, shares, trades, dividends):
    print('\nFair Dividend Rate income calculation')
    print('{v1:{w1}.0%}{v2:{w2}}{v3:>{w3},.2f}'.format(
            v1 = Decimal(FAIR_DIVIDEND_RATE), w1 = 2,
            v2 = ' of total opening value', w2 = 53,
            v3 = FDR_basic_income, w3 = 20))

    if any_quick_sale_adjustment:
        quick_sale_adjustments = Decimal('0.00')
        for share in shares:
            if share.quick_sale_adjustment:
                print('\nQuick Sale Adjustment for ' + share.code)
                share_adjustment = calc_QSA(share, trades, dividends)
                print('{v1:{w1}}{v2:>{w2}}'.format(
                    v1='Quick Sale Adjustment', w1=55, v2=share_adjustment, w2=20))
                quick_sale_adjustments += share_adjustment

        FDR_income = FDR_basic_income + quick_sale_adjustments
    else:
        print('{v1:{w1}}{v2:>{w2}}'.format(
            v1='Quick Sale Adjustments', w1=55, v2='Not Applicable', w2=20))
        FDR_income = FDR_basic_income

    print('{v1:{w1}}{v2:>{w2}}'.format(
            v1 = '', w1 = 55, v2 = 16 * '-', w2 = 20))
    print('{v1:{w1}}{v2:>{w2},.2f}\n'.format(
            v1 = 'Fair Dividend Rate income', w1 = 55, v2 = FDR_income, w2 = 20))
    return FDR_income


def print_FIF_income(CV_income, FDR_income):
    """

    :param CV_income:
    :return:
    """
    if FDR_income <= CV_income:
        print('\nUse Fair Dividend Rate income as basis for FIF income')
        FIF_income = FDR_income
    else:
        print('\nUse Comparative Value income as basis for FIF income')
        if CV_income < 0:
            print('However, FIF income cannot be negative.')
            FIF_income = 0
        else:
            FIF_income = CV_income

    print('{v1:{w1}}{v2:>{w2},.2f}\n'.format(
            v1 = 'FIF income is:', w1 = 55, v2 = FIF_income, w2 = 20))
    return


def main():
    global fx_rates
    global tax_year
    # tax_year = get_tax_year()
    fx_rates = get_fx_rates(fx_rates)

    shares = get_opening_positions()
    opening_value, FDR_basic_income = process_opening_positions(shares)

    # Need to process trades first, to get info on shares purchased
    # during the year, which might receive dividends later.
    trades = get_trades()
    cost_of_trades, any_quick_sale_adjustment = process_trades(shares, trades)

    dividends = get_dividends()
    gross_income_from_dividends = process_dividends(shares, dividends)

    closing_prices = get_closing_prices(shares)
    closing_value = process_closing_prices(shares, closing_prices)
# uncomment next when ready to actually save
#     save_closing_positions(shares)

    CV_income = calc_comparative_value_income(opening_value, cost_of_trades,
            gross_income_from_dividends, closing_value)

    FDR_income = determine_FDR_income(FDR_basic_income, any_quick_sale_adjustment,
           shares, trades, dividends)

    print_FIF_income(CV_income, FDR_income)
    save_fx_rates(fx_rates)
    return


if __name__ == '__main__':
    main()
