import math
import pandas as pd
import numpy as np
from datetime import timedelta
from datetime import datetime
from pypfopt import EfficientFrontier
from pypfopt import risk_models
from pypfopt import expected_returns

time_window_days = 120
time_window_days_minus1 = time_window_days - 1
rebalancing_period = 7

df = pd.read_excel(r'/Users/gmmtakane/Desktop/Thesis/Prices.xlsx')

"""Get the dataframe and set indexes and columns"""
df['date'] = [datetime.strptime(d, '%d-%m-%Y') for d in df['date']]
dates = df['date']
df = df.set_index(df['date'])
del df['date']
cryptos = list(df.columns)

"""Initialize the variables for the loops"""
start_date = df.index[0]
start_date_plus1= start_date + timedelta(days=1)
start_portfolio = start_date + timedelta(days=time_window_days_minus1)
end_date=df.index[-1]

"""Calculate the logarithmic returns matrix"""
returns = [0] * (len(cryptos)) #first row of zeros
returns = pd.DataFrame([returns],columns=cryptos)

while start_date_plus1 <= end_date:
    daily_returns = list()

    for i in cryptos:
        t_minus1=df.loc[start_date_plus1 - timedelta(days=1)]
        t_minus1=t_minus1.loc[i]
        t=df.loc[start_date_plus1]
        t=t.loc[i]
        log_ret = math.log(t/t_minus1)
        daily_returns.append(log_ret)

    df_length = len(returns)
    returns.loc[df_length] = daily_returns
    start_date_plus1 = start_date_plus1 + timedelta(days=1)
returns = returns.set_index(dates)
returns=returns.replace([np.inf, -np.inf, np.nan],0)

"""Calculate weights and weighted returns"""
start_date_plus1 = start_date + timedelta(days=1)
start_date_i = start_date
start_portfolio_i = start_portfolio
first_return_day = start_portfolio + timedelta(days=1)
weights_index = 0

weighted_returns = [0] * (len(cryptos))
weighted_returns = pd.DataFrame([weighted_returns],columns=cryptos)

#Set to zero the weighted returns of the dates before the start of the portfolio
while start_date_plus1 <= start_portfolio:
    min_vol = [0] * (len(cryptos))
    df_length = len(weighted_returns)
    weighted_returns.loc[df_length] = min_vol
    start_date_plus1 = start_date_plus1 + timedelta(days=1)

#Set the first weights
rebalancing_day = start_portfolio

local_df = df[start_date_i: start_portfolio_i]
local_df = local_df.replace(0, np.nan).dropna(axis=1)
columns = list(local_df.columns)
drop = list(set(cryptos) - set(columns))

local_df = returns[start_date_i: start_portfolio_i]
local_df = local_df.iloc[1:]  # remove first row
local_df = local_df.drop(drop, axis=1)
columns = list(local_df.columns)

mu = expected_returns.mean_historical_return(local_df,returns_data=True,frequency=365)
rf = 0.00 #risk free rate - 0.02 (in this case = 0)
mu_excess = mu - rf

Sigma = risk_models.sample_cov(local_df,returns_data=True,frequency=365)

Sigma_np = Sigma.to_numpy()

x = Sigma_np.diagonal()
x = x**(1/2)

inv = 1/x

divisor = inv.sum()

weights=np.divide(inv,divisor)
weights=weights.T

weight_matrix = pd.DataFrame(weights)
weight_matrix = weight_matrix.T
weight_matrix['date'] = rebalancing_day
weight_matrix = weight_matrix.set_index('date')
weight_matrix.columns=columns

start_portfolio_i = start_portfolio_i + timedelta(days=1)
start_date_i = start_date_i + timedelta(days=1)

while start_portfolio_i <= end_date:
    min_vol = list()
    rebalancing_day_check=start_portfolio_i-start_portfolio
    rebalancing_day_check=rebalancing_day_check.days

    #rebalancing and returns calculation
    if rebalancing_day_check % rebalancing_period == 0 :

        for i in cryptos:
            if i not in columns: #All the cryptos not in the weight names set to 0
                min_vol.append(0)

            else: #Returns calculation
                r = returns.loc[start_portfolio_i]
                r = r.loc[i]
                weight_minus1 = weight_matrix.loc[rebalancing_day]
                weight_minus1 = weight_minus1.loc[i]
                c = r * weight_minus1
                min_vol.append(c)

        local_df = df[start_date_i: start_portfolio_i]
        local_df = local_df.replace(0, np.nan).dropna(axis=1)
        columns = list(local_df.columns)
        drop = list(set(cryptos) - set(columns))

        local_df = returns[start_date_i: start_portfolio_i]
        local_df = local_df.drop(drop, axis=1)
        columns = list(local_df.columns)

        rebalancing_day = rebalancing_day + timedelta(days=rebalancing_period)

        mu = expected_returns.mean_historical_return(local_df,returns_data=True,frequency=365)
        mu_excess = mu - rf

        Sigma = risk_models.sample_cov(local_df, returns_data=True, frequency=365)

        Sigma_np = Sigma.to_numpy()

        x = Sigma_np.diagonal()
        x = x ** (1 / 2)

        inv = 1 / x

        divisor = inv.sum()

        weights = np.divide(inv, divisor)
        weights = weights.T

        weights = pd.DataFrame(weights)
        weights = weights.T
        weights['date'] = rebalancing_day
        weights = weights.set_index('date')
        weights.columns = columns

        weight_matrix = [weight_matrix, weights]
        weight_matrix = pd.concat(weight_matrix, ignore_index=False)

        df_length = len(weighted_returns)
        weighted_returns.loc[df_length] = min_vol

    # Returns calculation
    else:
        for i in cryptos:
            if i not in columns:
                min_vol.append(0)
            else:
                r = returns.loc[start_portfolio_i]
                r = r.loc[i]
                weight_minus1 = weight_matrix.loc[rebalancing_day]
                weight_minus1 = weight_minus1.loc[i]
                c = r * weight_minus1
                min_vol.append(c)

        df_length = len(weighted_returns)
        weighted_returns.loc[df_length] = min_vol

    start_portfolio_i = start_portfolio_i + timedelta(days=1)
    start_date_i = start_date_i + timedelta(days=1)
weighted_returns = weighted_returns.set_index(dates)
weighted_returns['portfolio return'] = weighted_returns.sum(axis=1)

"""Calculation of the portfolio value"""
initial_value = 1
start_portfolio_i = start_portfolio + timedelta(days=1)

portfolio_value = [0] * (time_window_days_minus1)
portfolio_value.append(initial_value)
portfolio_return_index = time_window_days_minus1


while start_portfolio_i <= end_date:

    ret = weighted_returns.loc[start_portfolio_i]
    ret = ret.loc['portfolio return']

    if ret == 0:
        portfolio_value_previous = portfolio_value[portfolio_return_index]
        current_value = portfolio_value_previous
        portfolio_value.append(current_value)

        start_portfolio_i = start_portfolio_i + timedelta(days=1)
        portfolio_return_index = portfolio_return_index + 1
    else:
        portfolio_value_previous = portfolio_value[portfolio_return_index]
        current_value = portfolio_value_previous * math.exp(ret)
        portfolio_value.append(current_value)

        start_portfolio_i = start_portfolio_i + timedelta(days=1)
        portfolio_return_index = portfolio_return_index + 1

weighted_returns['portfolio_value'] = portfolio_value

#Save the dataframes to Excel file
weighted_returns.to_excel(r'/Users/gmmtakane/Desktop/Thesis/weighted_returns inv vol' + '.xlsx', index = True)
weight_matrix.to_excel(r'/Users/gmmtakane/Desktop/Thesis/weights inv vol' + '.xlsx')
returns.to_excel(r'/Users/gmmtakane/Desktop/Thesis/log returns inv vol' + '.xlsx')

