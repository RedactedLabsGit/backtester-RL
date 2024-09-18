from time_series import load_csv
from order_book import OrderBook
from kandel import kandel_simulator


def main():
    ts = load_csv('data/full_ETHUSDC_2023.csv')
    

    window = 1440
    quote = 75000
    base = 0
    vol_mult = 0.4
    n_points = 10
    step_size = 1
    order_book = OrderBook()
    transactions, res, order_book = kandel_simulator(ts = ts, 
                quote = quote,
                base = base, 
                vol_mult=vol_mult,
                n_points= n_points, 
                step_size=step_size,
                order_book= order_book,
                window= window)
    res.to_pandas().to_csv('results/simul_results.csv')

    

if __name__ == '__main__':

    # TO DO ERROR HANDLING
    main()