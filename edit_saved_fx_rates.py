from tkinter import filedialog, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from FIF import yes_or_no, get_fx_rates, save_fx_rates
from datetime import date

def get_iso4217_currency_codes():
    filename = askopenfilename()
    Tk().withdraw
    # This is to remove the GUI window that was opened.
    if filename is None:
        print('No valid file name was provided')
        return

    codes_list = []
    with open(filename, 'r', encoding='utf-8-sig') as iso4217_currency_codes_file:
        for line in iso4217_currency_codes_file:
            codes_list.append(line[0:3])

    return codes_list


def update_codes_in_fx_rates(fx_rates):
    codes_list = get_iso4217_currency_codes()
    update_made = False
    for code in codes_list:
        if code not in fx_rates:
            fx_rates[code] = None
            update_made = True
    return update_made


def update_currency_rates(fx_rates):
    update_made = False
    currency = input('Enter the currency code for which you would like to add or update a rate: ')
    if currency not in fx_rates:
        print('That is not a valid currency code. This function is closing now.')
        return False

    return update_made


def main():
    fx_rates = get_fx_rates()
    update_made = False

    question = 'Would you like to update the list of currency codes in fx_rates?'
    if (yes_or_no(question)):
        update_made = update_codes_in_fx_rates(fx_rates)

    print(fx_rates)

    question = 'Would you like to add or update fx_rate for any specific currency?'
    if (yes_or_no(question)):
        update_made = update_currency_rates(fx_rates)

    if update_made:
        question = 'Would you like to save the updates to fx_rates?'
        if (yes_or_no(question)):
            save_fx_rates(fx_rates)

    return


if __name__ == '__main__':
    main()
