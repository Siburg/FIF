from tkinter import filedialog, Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pickle
from FIF import yes_or_no, get_fx_rates, save_fx_rates

def get_iso4217_currency_codes():
    filename = askopenfilename()
    Tk().withdraw
    # This is to remove the GUI window that was opened.
    if filename is None:
        print('No valid file name was provided')
        return

    codes_list = []
    with open(filename, 'r', encoding='utf-8') as iso4217_currency_codes_file:
        for line in iso4217_currency_codes_file:
            codes_list.append(line[0:3])

    return codes_list


def update_codes_in_fx_rates(fx_rates):
    codes_list = get_iso4217_currency_codes()
    for code in codes_list:
        if code not in fx_rates:
            fx_rates[code] = None
    return  # fx_rates is mutable; no need to return it explicitly.


def main():
    fx_rates = get_fx_rates()
    update_made = False

    question = 'Would you like to update the list of currency codes in fx_rates?'
    if (yes_or_no(question)):
        update_codes_in_fx_rates(fx_rates)
        update_made = True

    print(fx_rates)

    if update_made:
        question = 'Would you like to save the updates to fx_rates?'
        if (yes_or_no(question)):
            save_fx_rates(fx_rates)

    return


if __name__ == '__main__':
    main()
