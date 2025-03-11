from SmartApi import SmartConnect
from logzero import logging
import pyotp
from time import sleep
import datetime
from datetime import date,timedelta
import pandas as pd
import requests
import os
import math

class AngelBroking:
    def __init__(self, api_key:str, qr_totp:str, client_id:str, pin:int):
        logging.basicConfig(filename="angel_error.log", filemode="a", format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO) 
        self.api_key=api_key
        self.client_id=client_id
        self.pin=pin
        self.qr_totp=qr_totp
        self.tradeable_file_name=""
        self.tradeable_url="https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
        self.totp=self.totp_code(self.qr_totp)
        self.smart=SmartConnect(self.api_key)
        self.generate_session()
        self.angelone_tradeable_instr()
        

    def time_formating(self,time:str):  #time formating str time to time data type with date and time='09:15:16'
        z=str(date.today())
        y=z+' '+time
        return datetime.datetime.strptime(y,'%Y-%m-%d %H:%M:%S')
    

    def totp_code(self,qr_totp:str):
        try:  
            totp = pyotp.TOTP(qr_totp).now()
            #data type of totp is str
            if type(totp)==int:
                logging.error("totp is string and value error ")
        except Exception as e:
            logging.error(f"totp generative fail   {e}")
        return totp
    

    def generate_session(self):
        initial_time=datetime.datetime.now()+timedelta(seconds=121) #this line simply add 61 sec to persent time and i am using datetime.datetime because some time library is overlaping
        while True: 
            try:
                data=self.smart.generateSession(self.client_id, self.pin, self.totp)
                if data['status']==True:
                    print(data['data']['name'], ', you connected successfully')
                    break
                if datetime.datetime.now()>initial_time:
                    logging.critical("connection failled angelone after 121 second ")
                    break
            except Exception as e:
                logging.critical(f"connection failled angelone  {e}")
    

    def end_Session(self):
        #after initiation of this function you can't push order through API you can pull data but can't order
        self.smart.terminateSession(self.client_id)
        

    def angelone_tradeable_instr(self):
        # Download tradeable instrument and will help us to find symbol token from script
        try:
            response = requests.get(self.tradeable_url)
            if response.status_code == 200:
                data = response.json()  # Convert response to JSON
                # Convert JSON to DataFrame
                df = pd.DataFrame(data)
                # Save as CSV in the same directory
                file_name = "AngelOne_Tradable_Instruments.csv"
                self.tradeable_file_name=file_name
                df.to_csv(file_name, index=False)
                print(f"CSV file saved successfully: {file_name}")
        except Exception as e:
            logging.error(f'problem in fetching tradeable instrument file from angelone  {e}')
    
    def lot_size(self, symbol:str):
        #symbol fromat of every exchange and differ script is different so check before entering symbol
        try:
            file_name = self.tradeable_file_name  # Replace with your actual file name
            read1=0
            for file in os.listdir("."):  
                if file == file_name:
                    read1=1
                    df = pd.read_csv(file_name, low_memory=False)
                    lot_size = df.loc[df["symbol"] == symbol, "lotsize"].values[0]
                    symbol_value=int(lot_size)
                    return symbol_value
            if read1==0:
                logging.error(f"problem in finding file or something is wrong in code lot size ")
        except Exception as e:
            logging.error(f"problem in finding file or something is wrong  lot size  {e}")
    

    def get_fut_scripts(self,name_script:str):
        #name_script sholud pass like  "sbin", "infy" not like SBIN-EQ, INFY-EQ
        # if searching nifty, banknifty, sensex
        name_script=name_script.upper()
        try:
            df = pd.read_csv(self.tradeable_file_name, low_memory=False)
        except Exception as e:
            logging.error(f'problem in instrument file  {e}') 
        
        try:
            filtered_df = df[(df['symbol'].str.contains(name_script)) & (df['instrumenttype'] == 'FUTSTK') & (df['exch_seg'] == 'NFO')]
            filtered_df = filtered_df.copy()
            filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
            filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
            if len(filtered_df)==0:
                filtered_df = df[(df['symbol'].str.contains(name_script)) & (df['instrumenttype'] == 'FUTCOM') & (df['exch_seg'] == 'MCX')]
                filtered_df = filtered_df.copy()
                filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
                filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
                if len(filtered_df)==0:
                    filtered_df = df[(df['symbol'].str.contains(name_script)) & (df['instrumenttype'] == 'FUTCUR') & (df['exch_seg'] == 'CDS')]
                    filtered_df = filtered_df.copy()
                    filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
                    filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
                    if len(filtered_df)==0:
                        filtered_df = df[(df['symbol'].str.contains(name_script)) & (df['instrumenttype'] == 'FUTIDX') & (df['exch_seg'] == 'NFO')]
                        filtered_df = filtered_df[filtered_df['name'] == name_script]
                        filtered_df = filtered_df.copy()
                        filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
                        filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
                        if len(filtered_df)==0:
                            filtered_df = df[(df['symbol'].str.contains(name_script)) & (df['instrumenttype'] == 'FUTIDX') & (df['exch_seg'] == 'BFO')]
                            filtered_df = filtered_df[filtered_df['name'] == name_script]
                            filtered_df = filtered_df.copy()
                            filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
                            filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
            return filtered_df['symbol'].to_list()
        except Exception as e:
            logging.error(f'problem in finding future of script  {e}')


    def convert_symbol_to_token(self,symbol:str):
        try:
            file_name = self.tradeable_file_name  # Replace with your actual file name
            read1=0
            for file in os.listdir("."):  
                if file == file_name:
                    read1=1
                    df = pd.read_csv(file_name, low_memory=False)
                    symbol_value = df.loc[df["symbol"] == symbol, "token"].values[0]
                    symbol_value=int(symbol_value)
                    return symbol_value
            if read1==0:
                logging.error(f"problem in finding file or something is wrong in code")
        except Exception as e:
            logging.error(f"problem in finding file or something is wrong  {e}")
    

    def pnl(self):
        try:
            pos1=self.smart.position() 
            return pos1['data'][0]['pnl']
        except Exception as e:
            logging.critical(f'problem in pnl data   {e}')

        
    def ltp_of_script(self,exchange:str, symbol:str): 
        symbol_tok=self.convert_symbol_to_token(symbol=symbol)
        try:
            return self.smart.ltpData(symboltoken=symbol_tok,tradingsymbol=symbol,exchange=exchange)['data']['ltp']
        except Exception as e:
            logging.error(f'problem in fetching ltp data  {e}')

    
    def no_of_order(self):
        ak=self.smart.orderBook()
        return len(pd.DataFrame(ak))
        
    
    def short_term_histroical_data(self,symbol:str, interval:str, exchange:str):
        sym_tok=self.convert_symbol_to_token(symbol=symbol)
        interval_constant={'ONE_MINUTE':30, 'THREE_MINUTE':60,'FIVE_MINUTE':100,'TEN_MINUTE':100,'FIFTEEN_MINUTE':200,'THIRTY_MINUTE':200, 'ONE_HOUR':400,'ONE_DAY':2000 }
        days_buffer=interval_constant[interval]
        try:
            to_date = datetime.datetime.today()
            from_date = to_date - datetime.timedelta(days_buffer-2)

            from_int=from_date.strftime("%Y-%m-%d %H:%M")
            limi_int=to_date.strftime("%Y-%m-%d %H:%M")
            historicParam={"exchange": exchange,"symboltoken": sym_tok,"interval": interval,"fromdate": from_int, "todate": limi_int}
            can_data=self.smart.getCandleData(historicParam)
            can_data = pd.DataFrame(can_data['data'], columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
            return can_data
        except Exception as e:
            logging.error(f'problem in short term histroical data  {e}')


    def get_long_length_hist_datar(self,symbol:str,exchange:str,interval:str,from_date:str,download_till_date:str) :
        try:
            sym_tok=self.convert_symbol_to_token(symbol=symbol)
            interval_constant={'ONE_MINUTE':30, 'THREE_MINUTE':60,'FIVE_MINUTE':100,'TEN_MINUTE':100,'FIFTEEN_MINUTE':200,'THIRTY_MINUTE':200, 'ONE_HOUR':400,'ONE_DAY':2000 }
            delta_value=interval_constant[interval]
            # to_date = from_date + datetime.timedelta(days=delta_value)
            download_till_date = download_till_date
            to_date = None
            from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d")
            from_date = from_date.date()
            download_till_date = datetime.datetime.strptime(download_till_date, "%Y-%m-%d")
            download_till_date = download_till_date.date()
            culumative_data = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            while True:
                to_date = from_date + datetime.timedelta(days=delta_value)
                if from_date < download_till_date < to_date:
                    to_date = download_till_date

                from_int=from_date.strftime("%Y-%m-%d %H:%M")
                limi_int=to_date.strftime("%Y-%m-%d %H:%M")
                historicParam={"exchange": exchange,"symboltoken": sym_tok,"interval": interval,"fromdate": from_int, "todate": limi_int}
                can_data=self.smart.getCandleData(historicParam)
                can_data = pd.DataFrame(can_data['data'], columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
                culumative_data = (pd.concat([culumative_data, can_data], ignore_index=True).sort_values(by='Date', ascending=True).reset_index(drop=True))

                print(symbol, from_date, to_date, len(culumative_data))
                from_date = to_date + datetime.timedelta(days=1)
                if to_date >= download_till_date:
                    break
            culumative_data.to_csv('nifty.csv')
            return culumative_data
        except Exception as e:
            logging.error(f'problem in historical data fetching  {e}')
        

    
    def intraday_order(self,symbol:str, exchange:str, order_type:str, transaction_type:str, qunatity:int,price:None ,trigger_price:None,order_tag:None):
        symbol_tok=self.convert_symbol_to_token(symbol=symbol)

        if order_type=="LIMIT":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "INTRADAY","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="MARKET":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "INTRADAY","duration": "DAY","price": 0,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="STOPLOSS_LIMIT":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "INTRADAY","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        
        if order_type=="STOPLOSS_MARKET":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "INTRADAY","duration": "DAY","price": '0',"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        try:
            orderid_intraday = self.smart.placeOrder(orderparams)
            return orderid_intraday
        except Exception as e:
            logging.critical(f'problem in parameter or code of placing order  {e}')

    
    def future_option_order(self,symbol:str, exchange:str, order_type:str, transaction_type:str, qunatity:int,price:None ,trigger_price:None,order_tag:None):
        symbol_tok=self.convert_symbol_to_token(symbol=symbol)

        if order_type=="LIMIT":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "CARRYFORWARD","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="MARKET":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "CARRYFORWARD","duration": "DAY","price": 0,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="STOPLOSS_LIMIT":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "CARRYFORWARD","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        
        if order_type=="STOPLOSS_MARKET":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "CARRYFORWARD","duration": "DAY","price": '0',"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        try:
            orderid_intraday = self.smart.placeOrder(orderparams)
            return orderid_intraday
        except Exception as e:
            logging.critical(f'problem in parameter or code of placing order  {e}')

    
    def stock_delivery_order(self,symbol:str, exchange:str, order_type:str, transaction_type:str, qunatity:int,price:None ,trigger_price:None,order_tag:None):
        symbol_tok=self.convert_symbol_to_token(symbol=symbol)
        #for stock delivery
        if order_type=="LIMIT":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "DELIVERY","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="MARKET":
            orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "DELIVERY","duration": "DAY","price": 0,"quantity": qunatity,"triggerprice":'0',"ordertag":order_tag}
        
        if order_type=="STOPLOSS_LIMIT":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "DELIVERY","duration": "DAY","price": price,"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        
        if order_type=="STOPLOSS_MARKET":
            orderparams = {"variety": "STOPLOSS","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": transaction_type,"exchange": exchange,"ordertype": order_type,"producttype": "DELIVERY","duration": "DAY","price": '0',"quantity": qunatity,"triggerprice":trigger_price,"ordertag":order_tag}
        try:
            orderid_intraday = self.smart.placeOrder(orderparams)
            return orderid_intraday
        except Exception as e:
            logging.critical(f'problem in parameter or code of placing order  {e}')

    
    def find_order_id(self,tag:str):
        try:
            order_data=self.smart.orderBook()
            lenth_order=len(pd.DataFrame(order_data))
            ta=0
            for item in range (lenth_order):
                if order_data['data'][item]['ordertag']==tag:
                    order_id=order_data['data'][item]['orderid']
                    ta=1
                    return order_id  
            if ta==0:
                print('wrong tag or tag is not filled or http connection fail ')
        except Exception as e:
            logging.error(f'problem in finding order id through tag  {e}')
    
        
    def order_cancel(self,order_id:int):
        #check variety of order it like "STOPLOSS" or "NORMAL"  or etc
        order_data=self.smart.orderBook()
        lenth_order=len(pd.DataFrame(order_data))
        for item in range (lenth_order):
            if order_data['data'][item]['orderid']==str(order_id):
                variety=order_data['data'][item]['variety']
                try:
                    self.smart.cancelOrder(order_id=order_id,variety=variety)
                except Exception as e:
                    logging.critical(f'not able to cancel order please cancel manually and check code {e}')
                break


    def modify_order(self,order_id:int,price:int,trigger_price:int):
        order_data=self.smart.orderBook()
        lenth_order=len(pd.DataFrame(order_data))
        for item in range (lenth_order):
            if order_data['data'][item]['orderid']==str(order_id):
                variety=order_data['data'][item]['variety']
                order_type=order_data['data'][item]['ordertype']
                product_type=order_data['data'][item]['producttype']
                trading_sym=order_data['data'][item]['tradingsymbol']
                exchange=order_data['data'][item]['exchange']
                sym_tok=order_data['data'][item]['symboltoken']
                quantity=order_data['data'][item]['quantity']
                try:
                    para1={"variety":variety,"orderid":order_id,"ordertype":order_type,"producttype":product_type,"duration":"DAY","price":price,"quantity":quantity,"tradingsymbol":trading_sym,"symboltoken":sym_tok,"exchange":exchange,'triggerprice':trigger_price}
                    self.smart.modifyOrder(para1)
                except Exception as e:
                    logging.error(f'problem in modifying of order {e}')
                break


    def get_order_status(self,order_id):
        try:
            order_data=self.smart.orderBook()
            lenth_order=len(pd.DataFrame(order_data))
            ta=0
            for item in range (lenth_order):
                if order_data['data'][item]['orderid']==str(order_id):
                    order_status=order_data['data'][item]['status']
                    ta=1
                    return order_status
            if ta==0:
                print('wrong oder status is not filled or http connection fail ')
        except Exception as e:
            logging.error(f'problem in finding order status through tag  {e}')

        
    def option_symbol_finding(self,ltp_script:int,step_vallue:int,ce_or_pe:str,name:str,no_of_expiry_ahead:int,select_atm_itm_otm:str,inside_outside:int):
        file_name=self.tradeable_file_name
        strike = round(ltp_script/step_vallue)*step_vallue
        if select_atm_itm_otm=='ITM' and ce_or_pe=='CE':
            strike=strike-(step_vallue*inside_outside)
        if select_atm_itm_otm=='ITM' and ce_or_pe=='PE':
            strike=strike+(step_vallue*inside_outside)
        if select_atm_itm_otm=='OTM' and ce_or_pe=='CE':
            strike=strike+(step_vallue*inside_outside)
        if select_atm_itm_otm=='OTM' and ce_or_pe=='PE':
            strike=strike-(step_vallue*inside_outside)   
        first_filter=str(strike)+ce_or_pe
        read1=0
        try:
            for file in os.listdir("."):  
                if file == file_name:
                    read1=1
                    df = pd.read_csv(file_name, low_memory=False)
                    filtered_df = df[df['symbol'].astype(str).str.contains(first_filter, na=False)]
                    filtered_df = filtered_df[(filtered_df['name'] == name)]
                    filtered_df = filtered_df.copy()
                    filtered_df.loc[:, "Expiry2"] = pd.to_datetime(filtered_df["expiry"], format="%d%b%Y", errors="coerce")
                    filtered_df = filtered_df.sort_values(by="Expiry2", ascending=True)
                    first_symbol = filtered_df.iloc[no_of_expiry_ahead]['symbol']  
                    return first_symbol
            if read1==0:
                logging.error(f"problem in findinG ATM symbol")
        except Exception as e:
            logging.error(f"problem in finding atm symbol  {e}")
    

    def market_over_close_all_order(self):
        try:
            order_data=self.smart.orderBook()
            lenth_order=len(pd.DataFrame(order_data))
            ta=0
            #complete,#rejected
            for item in range (lenth_order):
                if order_data['data'][item]['status']=='open' or order_data['data'][item]['status']=='trigger pending':
                    order_id=order_data['data'][item]['orderid']
                    variety=order_data['data'][item]['variety']
                    self.smart.cancelOrder(order_id=order_id,variety=variety)
        except Exception as e:
            logging.error(f"market over closee all trade cancel part  {e}")
        try:
            trade_data=self.smart.tradeBook()
            lenth_trade=len(pd.DataFrame(trade_data))
            for item in range (lenth_trade):
                symbol_tok=self.convert_symbol_to_token(symbol=trade_data['data'][item]['tradingsymbol'])
                symbol=trade_data['data'][item]['tradingsymbol']
                exchange=trade_data['data'][item]['exchange']
                if trade_data['data'][item]['transactiontype']=='BUY':
                    #ltp1=self.smart.ltpData(symboltoken=symbol_tok,tradingsymbol=symbol,exchange=exchange)['data']['ltp']
                    product_typ=trade_data['data'][item]['producttype']
                    q1=trade_data['data'][item]['fillsize']
                    orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": 'SELL',"exchange": exchange,"ordertype": "MARKET","producttype": product_typ,"duration": "DAY","price": 0,"squareoff": "0","stoploss": "0","quantity": q1}
                    exit_id = self.smart.placeOrder(orderparams)
                if trade_data['data'][item]['transactiontype']=='SELL':
                    #ltp1=self.smart.ltpData(symboltoken=symbol_tok,tradingsymbol=symbol,exchange=exchange)['data']['ltp']
                    product_typ=trade_data['data'][item]['producttype']
                    q1=trade_data['data'][item]['fillsize']
                    orderparams = {"variety": "NORMAL","tradingsymbol": symbol,"symboltoken": symbol_tok,"transactiontype": 'BUY',"exchange": exchange,"ordertype": "MARKET","producttype": product_typ,"duration": "DAY","price": 0,"squareoff": "0","stoploss": "0","quantity": q1}
                    exit_id = self.smart.placeOrder(orderparams) 
        except Exception as e:
            logging.error(f'tradebook empty order squaring off {e}')


ab1=AngelBroking("FOicAB6B","CEZT6ZWWQSXWGA6LICZRZHTTHQ","D90026",1503)
ab1.market_over_close_all_order()
#print(ab1.smart.tradeBook())
#ak=ab1.get_order_status(order_id=250227000870442)
#ak=ab1.option_symbol_finding(ltp_script=48743,step_vallue=100,ce_or_pe='CE',name='BANKNIFTY',no_of_expiry_ahead=0,select_atm_itm_otm='OTM',inside_outside=4)
#ab1.market_over_close_all_order()
#print(ab1.no_of_order())
#id1=ab1.stock_delivery_order(exchange='NSE',symbol='PNB-EQ', order_type='STOPLOSS_MARKET',transaction_type='BUY',qunatity=1,price=0,trigger_price=93.4,order_tag='class99')
sleep(1)
#print(id1)
#ac=ab1.modify_order(order_id=250227000841619,price=0,trigger_price=93.8)
#print(ac)
#id2=ab1.find_order_id(tag='class99')
#print(id2)
#ab1.get_long_length_hist_datar(exchange='NSE',symbol='Nifty 50',interval='FIVE_MINUTE',from_date='2023-01-01',download_till_date='2025-02-25')
#print(ab1.convert_symbol_to_token(name='pnb'))
#print(ab1.lot_size(symbol='NIFTY27FEB2522600CE'))
#print(ab1.get_fut_scripts(name_script='finnifty'))
#df=ab1.short_term_histroical_data(symbol='Nifty 50',exchange='NSE', interval='FIVE_MINUTE')

#ab1.intraday_order(name='pnb',exchange='NSE',order_type='STOPLOSS_LIMIT',transaction_type='BUY',qunatity=1,trigger_price=93.5,price=94)
'''while True:
    try:
        d1=ab1.short_term_histroical_data(symbol='PNB-EQ',interval='ONE_MINUTE',exchange='NSE')
        print(d1.tail(2))
        sleep(1)
    
    except :
        pass'''


'''
name='PNB'
trading_sym=ab1.convert_name_to_symbol(name)
symbol_tok=ab1.convert_symbol_to_token(name)
print(trading_sym)
print(symbol_tok)
orderparams = {"variety": "STOPLOSS","tradingsymbol": trading_sym,"symboltoken": symbol_tok,"transactiontype": "BUY","exchange": "NSE","ordertype": "STOPLOSS_LIMIT","producttype": "INTRADAY","duration": "DAY","price": 94,"squareoff": "0","stoploss": 93.5,"quantity": 1}
print('higy   look')
ord=ab1.smart.placeOrder(orderparams)
print('lastt  ', ord)'''