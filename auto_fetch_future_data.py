from iFinDPy import *
from datetime import datetime
import pandas as pd
import time as _time
import json
from threading import Thread,Lock,Semaphore
import requests

sem = Semaphore(5)  # 此变量用于控制最大并发数
dllock = Lock()  #此变量用来控制实时行情推送中落数据到本地的锁

# 登录函数
def thslogin(username, password):
    # 输入用户的帐号和密码
    thsLogin = THS_iFinDLogin(username,password)
    # print(thsLogin)
    if thsLogin != 0:
        print('同花顺数据接口登录失败')
    else:
        print('同花顺数据接口登录成功')

def download_future_data(ETFName:str,strikePrice:int,maturityMonth:int,csvOutput:bool):
    """
    ETFName = '科创50'/'科创板50'/'创业板ETF'\n
    strikePrice = 行权价，阿拉伯数字\n
    maturityMonth = 1-12之间的阿拉伯数字\n
    csvOutput = True/False, 是否输出一个csv文件 \n
    返回值 = pandas df中保存期权、期货、ETF的日线数据
    """
    datestart = '2024-10-08'
    datedend = '2024-10-23'

    # 拼接出简称字符串
    callOptionName = ETFName+"购"+str(maturityMonth)+"月"+str(strikePrice)
    putOptionName = ETFName+"沽"+str(maturityMonth)+"月"+str(strikePrice)

    # 查询对应ETF的同花顺代码
    if ETFName == '科创50' or ETFName == '科创板50':
        ETFCode = '588000.SH'
    elif ETFName == '创业板ETF':
        ETFCode = '159915.SZ'
    else:
        print('ETFName输入错误，请输入科创50/科创板50/创业板ETF,三者其一')
        return

    # 查询期权合约简称的同花顺代码
    callOptionCode = THS_toTHSCODE(callOptionName,'mode:secname;sectype:021,021001,021002,021003,021004,021005;;tradestatus:2;isexact:1').data['thscode'].iloc[0]
    putOptionCode = THS_toTHSCODE(putOptionName,'mode:secname;sectype:021,021001,021002,021003,021004,021005;;tradestatus:2;isexact:1').data['thscode'].iloc[0]

    # 查询并获取期权合约的基本信息
    callOptionInfo = THS_BD(callOptionCode,'ths_strike_price_option;ths_listed_date_option;ths_maturity_date_option;ths_option_short_name_option;ths_option_code_option;ths_underlying_code_option','2025-06-21;;;;;').data
    putOptionInfo = THS_BD(putOptionCode,'ths_strike_price_option;ths_listed_date_option;ths_maturity_date_option;ths_option_short_name_option;ths_option_code_option;ths_underlying_code_option','2025-06-21;;;;;').data
    
    # 获取期权合约的基本信息
    listedDate = callOptionInfo['ths_listed_date_option'].iloc[0]
    maturityDate = callOptionInfo['ths_maturity_date_option'].iloc[0]
    strikePrice2 = callOptionInfo['ths_strike_price_option'].iloc[0]
    callOptionStdName = callOptionInfo['ths_option_code_option'].iloc[0]
  
    df1 = THS_HQ(callOptionCode,'close;openInterest;positionChange','',listedDate,maturityDate).data
    df2 = THS_HQ(putOptionCode,'close;openInterest;positionChange','',listedDate,maturityDate).data
    df3 = THS_HQ(ETFCode,'close','',listedDate,maturityDate).data

    # cols_to_prefix_df1 = [col for col in df1.columns if col != 'time']
    # df1[cols_to_prefix_df1] = df1[cols_to_prefix_df1].add_prefix("C_")
    # cols_to_prefix_df2 = [col for col in df2.columns if col != 'time']
    # df2[cols_to_prefix_df2] = df2[cols_to_prefix_df2].add_prefix("P_")
    # cols_to_prefix_df3 = [col for col in df3.columns if col != 'time']
    # df3[cols_to_prefix_df3] = df3[cols_to_prefix_df3].add_prefix("ETF_")

    df1['time'] = pd.to_datetime(df1['time'])
    df2['time'] = pd.to_datetime(df2['time'])
    df3['time'] = pd.to_datetime(df3['time'])

    # 第一次合并
    merged_df_temp = pd.merge(df1, df2, on='time', how='outer')

    # 第二次合并
    final_merged_df = pd.merge(merged_df_temp, df3, on='time', how='outer')
    final_merged_df['strike_price'] = strikePrice2
    final_merged_df['C-P+K-S'] = (
    final_merged_df['close_x'] -
    final_merged_df['close_y'] +
    final_merged_df['strike_price'] -
    final_merged_df['close']
)
    # final_merged_df.rename(columns={"thscode_x": "thscode_call"})
    # final_merged_df.rename(columns={"close_x": "close_call"})
    # final_merged_df.rename(columns={"openInterest_x": "openInterest_call"})
    # final_merged_df.rename(columns={"positionChange_x": "positionChange_call"})
    
    # final_merged_df.rename(columns={"thscode_y": "thscode_put"})
    # final_merged_df.rename(columns={"close_y": "close_put"})
    # final_merged_df.rename(columns={"openInterest_y": "openInterest_put"})
    # final_merged_df.rename(columns={"positionChange_y": "positionChange_put"})
    
    # final_merged_df.rename(columns={"thscode": "thscode_ETF"})
    # final_merged_df.rename(columns={"close": "close_ETF"})

    # print("\n最终合并后的 DataFrame (列名已带前缀):\n", final_merged_df)

    # 依据选择将最终合并后的结果保存
    if csvOutput == True:
        final_merged_df.to_csv(f"./{callOptionStdName}.csv", index=False, encoding='utf-8-sig')
        return final_merged_df
    else:
        return final_merged_df

def main():
    # 登录函数
    username = "glzqgf076"
    password = "SkTbcgR7"
    thslogin(username,password)

    ETFName = '科创50' # 科创50/科创板50/创业板ETF, str
    strikePrice = 900 # 行权价，int类型
    maturityMonth = 6 # 到期月份，int类型， 1-12之间的阿拉伯数字
    df = download_future_data(ETFName,strikePrice,maturityMonth,csvOutput=False)
    print(df)

if __name__ == '__main__':
    main()

