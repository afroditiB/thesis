# -*- coding: utf-8 -*-
"""final

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1UYpShJz7ejNrFYo3WjQJHyePU-IJX71-
"""



!python -m pip uninstall matplotlib
!pip install matplotlib==3.1.3

!pip install -U darts
!pip install -U optuna
!pip install -U matplotlib

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline

import torch
import random
import numpy as np
from darts import TimeSeries
import pandas as pd
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from pytorch_lightning.callbacks import Callback, EarlyStopping
from sklearn.preprocessing import MaxAbsScaler, StandardScaler, MinMaxScaler

from sklearn.metrics import mean_absolute_percentage_error as mape
from sklearn.metrics import mean_squared_error as mse
from darts.metrics import mape as mape_darts
from darts.metrics import mase as mase_darts
from darts.metrics import mae as mae_darts
from darts.metrics import rmse as rmse_darts
from darts.metrics import smape as smape_darts
from darts.metrics import mse as mse_darts




from darts.datasets import ElectricityDataset
from darts.models import TCNModel, LinearRegressionModel, LightGBMModel, NBEATSModel
from darts.dataprocessing.transformers import Scaler
from darts.metrics import smape, rmse, mape, mae, mase
from darts.utils.likelihood_models import GaussianLikelihood
import datetime
from datetime import timedelta

import logging
from functools import reduce

from sklearn import preprocessing
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.metrics import r2_score

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from pytorch_lightning.profiler import Profiler, AdvancedProfiler
from torchmetrics import MeanAbsolutePercentageError

import lightgbm as lgb
from sklearn.datasets import load_boston
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error,mean_absolute_error
from sklearn.model_selection import train_test_split
from pandas import DataFrame
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt

def select_range(df,start_date,end_date):
  """
  Parameters: df : pd.Dataframe : the dataframe that we want to check for missing datetime values
              start_date : str : the desired start date of our df
              end_date : str : the desired end_date of our df

  Returns : ts : the cut df from start_date to end_date
"""
  ts=df.copy()
  start = pd.Timestamp(start_date)
  end = pd.Timestamp(end_date)
  ts=ts.loc[start:end]
  return ts

def read_csv_and_set_index(file,col=None,format=None,date_parse=None, separator = None):
  """
   Parameters: file : str: the name of the csv file that we want to save as df
               col : str : the name of the column we want to set as index
            
   Returns : df : pd.DataFrame : the df from the csv file, with col as index
"""
  if (date_parse is not None):
    dateparse = lambda x: datetime.datetime.strptime(x, '%Y%m%d%H%M%S')
    parse = [col]
  else :
    parse = False
    dateparse = None

  df = pd.read_csv(file,parse_dates=parse, date_parser=dateparse,sep=separator)
  if (col is not None):
    df = df.set_index(col)
  df.index=pd.to_datetime(df.index)
  return df

def convert_to_timeseries(df,col=None, resolution=None):

  """"
    Parameters: df : pd.DataFrame : the df we want to convert to TimeSeries
                resolution : str : the resolution in which we want to resample
                col : [str] : the column which we want to convert to TimeSeries, if not None, inside brackets
            
   Returns : series : TimeSeries: the converted timeseries from df or df's columns ( if col is not None)
  
"""
  if(resolution is not None):
    df=df.resample(resolution).mean()

  if (col is not None):
    data = df[col]
  else :
    data = df

  series = data.squeeze()
  series = series.astype(np.float32)
  series = TimeSeries.from_series(series)
  return series

def split_and_scale(series,test_start_date,scaler_model=None):

  """"
    Parameters: series : TimeSeries : The timeseries we want to split into train, val test and, optionally, scale.
                val_length : int : the length of the Timeseries we want to keep as a validation set
                scaler_model : sklearn.preprocessing. : the model of scaler to be fitted in our data.
            
   Returns : train : darts.TimeSeries: the timeseries we will use as a training set, meaning the input series timeseries, but cut at the val_start_date
             val   : TimeSeries: the timeseries we will use as a validation set, meaning the input series timeseries, but startint from the val_start_date
            series_transformed : TimeSeries : The timeseries with the scaled_model fitted and transformed
"""

  if (scaler_model is not None):
    scaler = Scaler(scaler=scaler_model)
    scaler_x =scaler.fit(series)
    series_transformed = scaler_x.transform(series)       

  else : 
    scaler_x = None
    series_transformed = series
  
  train = series_transformed.drop_after(pd.Timestamp(test_start_date))
  val = series_transformed.drop_before(pd.Timestamp(pd.Timestamp(
        test_start_date) - datetime.timedelta(hours=1)))
  
  return train,val, series_transformed, scaler_x

def append(x, y):
    return x.append(y)

def backtester_final(model,
               series_transformed,
               test_start_date,
               forecast_horizon,
               stride=None,
               series=None,
               transformer_ts=None,
               retrain=False,
               future_covariates=None,
               past_covariates=None,
               path_to_save_backtest=None):
    """ Does the same job with advanced forecast but much more quickly using the darts
    bult-in historical_forecasts method. Use this for evaluation. The other only
    provides pure inference. Provide a unified timeseries test set point based
    on test_start_date. series_transformed does not need to be adjacent to
    training series. if transformer_ts=None then no inverse transform is applied
    to the model predictions.
    Parameters
    ----------
    Returns
    ----------
    """
    # produce the fewest forecasts possible.
    if stride is None:
        stride = forecast_horizon
    test_start_date = pd.Timestamp(test_start_date)
    from functools import reduce

    # produce list of forecasts
    #print("backtesting starting at", test_start_date, "series:", series_transformed)
    backtest_series_transformed = model.historical_forecasts(series_transformed,
                                                             future_covariates=future_covariates,
                                                             past_covariates=past_covariates,
                                                             start=test_start_date,
                                                             forecast_horizon=forecast_horizon,
                                                             stride=stride,
                                                             retrain=retrain,
                                                             last_points_only=False,
                                                             verbose=False)
    


    # flatten lists of forecasts due to last_points_only=False
    if isinstance(backtest_series_transformed, list):
        backtest_series_transformed = reduce(
            append, backtest_series_transformed)

    # inverse scaling
    if transformer_ts is not None:
        backtest_series = transformer_ts.inverse_transform(
            backtest_series_transformed)
        series = transformer_ts.inverse_transform(
            series_transformed)
    else:
        series = series_transformed
        backtest_series = backtest_series_transformed
        print("\nWarning: Scaler not provided. Ensure model provides normal scale predictions")
        logging.info(
            "\n Warning: Scaler not provided. Ensure model provides normal scale predictions")

    # plot all test
    fig1 = plt.figure(figsize=(15, 8))
    ax1 = fig1.add_subplot(111)
    backtest_series.plot(label='forecast')
    series \
        .drop_before(pd.Timestamp(pd.Timestamp(test_start_date) - datetime.timedelta(days=7))) \
        .drop_after(backtest_series.time_index[-1]) \
        .plot(label='actual')
    ax1.legend()
    ax1.set_title(
        f'Backtest, starting {test_start_date}, {forecast_horizon}-steps horizon')
    # plt.show()

    # plot one week (better visibility)
    forecast_start_date = pd.Timestamp(
        test_start_date + datetime.timedelta(days=7))

    fig2 = plt.figure(figsize=(15, 8))
    ax2 = fig2.add_subplot(111)
    backtest_series \
        .drop_before(pd.Timestamp(forecast_start_date)) \
        .drop_after(forecast_start_date + datetime.timedelta(days=7)) \
        .plot(label='Forecast')
    series \
        .drop_before(pd.Timestamp(forecast_start_date)) \
        .drop_after(forecast_start_date + datetime.timedelta(days=7)) \
        .plot(label='Actual')
    ax2.legend()
    ax2.set_title(
        f'Weekly forecast, Start date: {forecast_start_date}, Forecast horizon (timesteps): {forecast_horizon}, Forecast extended with backtesting...')

    # Metrix
    test_series =  series.drop_before(pd.Timestamp(pd.Timestamp(
        test_start_date) - datetime.timedelta(hours=1)))
    
    metrics = {
        
        "smape": smape_darts(
            test_series,
            backtest_series),
        "mase": mase_darts(
            test_series,
            backtest_series,
            insample=series.drop_after(pd.Timestamp(test_start_date)),m=1),
        "mae": mae_darts(
            test_series,
            backtest_series),
        "rmse": rmse_darts(
            test_series,
            backtest_series),
        "mse" :mse_darts(
            test_series,
            backtest_series),
        "mape": mape_darts(
            test_series,
            backtest_series),
       }

    

    for key, value in metrics.items():
        print(key, ': ', value)



    return {"metrics": metrics, "eval_plot": plt, "backtest_series": backtest_series}

def eval_model(test_set, preds):
    
    metrics = {
        
        "mse" : mean_squared_error(test_set, preds),
        "rmse" :mean_squared_error(test_set, preds)**(0.5),
        "mape" :mean_absolute_percentage_error(test_set, preds),
        "mae" : mean_absolute_error(test_set, preds)
    }
    
    
    plt.figure(figsize=(15, 5))

    for key, value in metrics.items():
        print(key, ': ', value)

def drop_zeros(series, null_dates = None):

  temp = series.pd_dataframe()
  if (null_dates is None):
    null_dates = temp[temp['active_w6'] == 0].index
  temp = temp.drop(index =null_dates)
  series = temp.squeeze()
  series = series.astype(np.float32)
  return series , null_dates

def feature_target_split(df,col_name, lookback_window=24*3, forecast_horizon=1):# lookback_window: 168 = 7 days(* 24 hours)
    """
    This function gets a column of a dataframe and splits it to input and target
    
    **lookback_window**
    In a for-loop of 'lookback_window' max iterations, starting from 0 
    At N-th iteration (iter): 
        1. create a shifted version of 'Load' column by N rows (vertically) and 
        2. stores it in a column* (feature_'N')
    Same pseudo-code for 'forecast_horizon' loop
    
    *At first iterations of both loops, the new columns (feature/target) are going to be firstly created
    but for each iteration, the same columns are going to be used
    
    We store each new column created in a dictionary which, at the end, convert it to dataframe
    The reason behind this choice is that if it was initially a dataframe, for large amount of loops,
    fast insertion of new columns would cause a performance issue (slower) even though the end result
    would propably not be altered
    
    Parameters: 
        df: pandas.dataframe containing column to parse
        lookback_window: lookback_window - # feature columns - # inputs in model
        forecast_horizon: forecast_horizon - # target columns - # outputs in model
        col_name - str - the name of the column containing t-- -- - -to be filled
    ----------
    Returns
        'subset'_X: pandas.dataframe containing features of df after preprocess for model
        'subset'_Y: pandas.dataframe containing targets of df after preprocess for model
    -------
    """

    # Reset "Unnamed: 0" based on concated df 
    df['Unnamed: 0'] = range(1, len(df) + 1)

    df_copy = df.copy()    

    df_new = {}
        
    for inc in range(0,int(lookback_window)):
        df_new['feature_' + str(inc)] = df_copy[col_name].shift(-inc)

    # shift 'load' column permanently for as many shifts happened at 'lookback_window' loops  
    df_copy[col_name] = df_copy[col_name].shift(-int(lookback_window))
                    
    for inc in range(0,int(forecast_horizon)):
        df_new['target_' + str(inc)] = df_copy[col_name].shift(-inc)    
    
    df_new = pd.DataFrame(df_new, index=df_copy.index)
    df_new = df_new.dropna().reset_index(drop=True)    
                            
    return df_new.iloc[:,:lookback_window] , df_new.iloc[:,-forecast_horizon:]

"""#reading CSVs"""

power =read_csv_and_set_index('power_dt.csv','index')
current =read_csv_and_set_index('current_dt.csv','index')
voltage =read_csv_and_set_index('voltage_dt.csv','index')
weather = read_csv_and_set_index('weather.csv',col='time [UTC](yyyymmddHHMM)',date_parse = True, separator =';')

"""#Selecting range and converting dfs to Timeseries"""

start ='2021-08-06 17:00:00'
end = '2022-07-03 17:00:00'
power = select_range(power,start,end)
current=select_range(current,start,end)
voltage = select_range(voltage,start,end)
weather = select_range(weather,start,end)

power = power.interpolate()
current = current.interpolate()
voltage  = voltage.interpolate()

#power.at[power['active_w6']>-2,'active_w6']=0

series = convert_to_timeseries(current,['w6_phase1'],'60min')
series = abs(series)

"""#Spliting our series at train / val sets and start trying forecasting models

"""

train, val, series_transformed, scaler = split_and_scale(series, '2022-06-03 17:00:00')

"""# Trying Light GBM Model with backtesting ( historical forecasts)

"""

lgbm_model = LightGBMModel(lags = 5*24)
lgbm_model.fit(train)

backtest_dict = backtester_final(lgbm_model,series_transformed,'2022-06-03 17:00:00',1, series=series,transformer_ts=scaler )

"""#plotting the results

Selecting range and converting dfs to Timeseries
"""

test_series = series.drop_before(pd.Timestamp(pd.Timestamp(pd.Timestamp(
        '2022-06-03 17:00:00') - datetime.timedelta(hours=1))))

backtest_series = backtest_dict.get("backtest_series")

backtest_metrics = backtest_dict.get("metrics")

plt.plot(backtest_series.pd_dataframe()['2022-06-22 00:00:00':'2022-06-25 00:00:00'], label = 'forecast')
plt.plot(series.pd_dataframe()['2022-06-22 00:00:00':'2022-06-25 00:00:00'], label='pv power')

plt.xticks(rotation = 45)
plt.legend()
plt.show()

"""#Adding past and/or future covariates"""

weather_rad=convert_to_timeseries(weather,'global radiation [W/m^2]','60min')
weather_humidity = convert_to_timeseries(weather,'relative humidity [%]','60min')
weather_temp = convert_to_timeseries(weather,'air temperature [°C]','60min')
weather_cloud = convert_to_timeseries(weather,'cloudcover [%]','60min')
weather_wind = convert_to_timeseries(weather,'wind speed[m/s]','60min')

hour_covariate = convert_to_timeseries(power,['hour_of_day'],'60min')
month_covariate = convert_to_timeseries(power,['month'],'60min')

past_covariates =hour_covariate.stack(weather_temp).stack(weather_cloud).stack(month_covariate)

"""#plotting global radiation with pv's active power 

"""

plt.plot(weather_rad.pd_dataframe()['2022-06-22 00:00:00':'2022-06-25 00:00:00'], label = 'weather')
plt.plot(series.pd_dataframe()['2022-06-22 00:00:00':'2022-06-25 00:00:00'], label='pv power')

plt.xticks(rotation = 45)
plt.legend()
plt.show()

"""#forecasting with covariates

"""

train_cov,  val_cov, series_cov ,sc_cov= split_and_scale(past_covariates,'2022-06-03 17:00:00',MinMaxScaler())

lgbm_model_power = LightGBMModel(lags = 24, lags_past_covariates = 1)
lgbm_model_power.fit(train, past_covariates = train_cov)
backtester_final(lgbm_model_power,series_transformed,'2022-06-03 17:00:00',1, series=series,transformer_ts=scaler, past_covariates=series_cov)

"""#Plotting the results"""

backtest_series = backtest_dict.get("backtest_series")

test_series[-60:].plot(label='actual')
backtest_series[-60:].plot(label='forecast')
weather_rad[-60:].pd_dataframe().plot(label='weather')

plt.plot(backtest_series.pd_dataframe()['2022-06-19 00:00:00':'2022-06-25 22:00:00'], label = 'forecast')
plt.plot(series.pd_dataframe()['2022-06-19 00:00:00':'2022-06-25 22:00:00'], label='pv power')

plt.xticks(rotation = 45)
plt.legend()
plt.show()

"""#Manual Backtesting dataframe creation"""

test_df = series.pd_dataframe()

X , Y = feature_target_split(test_df,test_df.columns[0],lookback_window=5*24)

x_train, x_test, y_train, y_test = train_test_split(X, Y, test_size=0.09062303335431088735053492762744, random_state=42)

# defining parameters 
params = {
    'task': 'train', 
    'boosting': 'gbdt',
    'objective': 'regression',
    'num_leaves': 10,
    'learnnig_rage': 0.05,
    'metric': {'l2','l1'},
    'verbose': -1
}

lgb_train = lgb.Dataset(x_train, y_train)
lgb_eval = lgb.Dataset(x_test, y_test, reference=lgb_train)

model = lgb.train(params,train_set=lgb_train,
                 valid_sets=lgb_eval,
                 early_stopping_rounds=30)

y_pred = model.predict(x_test)

eval_model(y_test,y_pred)
