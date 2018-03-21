from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen, HTTPError
import csv
import redis 
import os
app = Flask(__name__)

BSE_URL = "https://www.bseindia.com/download/BhavCopy/Equity/"
REDIS_HOST = os.environ.get('REDIS_HOST', '')
REDIS_USER = os.environ.get('REDIS_USER', '')
REDIS_PORT = os.environ.get('REDIS_PORT', '')
REDIS_PASS = os.environ.get('REDIS_PASS', '')


def generateBhavFileURL(date):
    return BSE_URL + "EQ" + date + "_CSV.ZIP"

def fetchCSVFromBSE():
    now = datetime.now()
    try:
        date = now.strftime("%d%m%y")
        url = generateBhavFileURL(date)
        resp = urlopen(url)
    except HTTPError:
        date = (datetime.now() - timedelta(1)).strftime("%d%m%y")
        url = generateBhavFileURL(date)
        resp = urlopen(url)
    zipfile = ZipFile(BytesIO(resp.read()))
    zipfile.extractall()

    return "EQ"+date+".CSV"

def updateRedisWithCSV(file):
    print("Processing Started")
    bhav_data = []
    with open(file, 'r') as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            print("Processing: " + row['SC_NAME'])
            ds = {
                "code": row['SC_CODE'],
                "name": row['SC_NAME'],
                "open": row['OPEN'],
                "high": row['HIGH'],
                "low": row['LOW'],
                "close": row['CLOSE']
            }

            name_query = {
                "code": row['SC_CODE'],
                "open": row['OPEN'],
                "high": row['HIGH'],
                "low": row['LOW'],
                "close": row['CLOSE']
            }


            redis_client.set('query:name:'+row['SC_NAME'].strip(), name_query)
            bhav_data.append(ds)
            print("Processing: " + row['SC_NAME'])


    redis_client.set('data:bhav', bhav_data)

    top_10 = sorted(bhav_data, key=lambda k: k['close'])[:10]
    redis_client.set('data:bhav_top_10', top_10)
    print("Processing Completed")

@app.route('/')
def method_name():
   return 'Hello World!'

@app.route('/update_bhav')
def fetchAndUpdateBhav():    
    try:
        csv_file = fetchCSVFromBSE()
        updateRedisWithCSV(csv_file)
        result = "Success"
    except Exception as e:
        result = "Failed: " + str(e)
    
    return jsonify(
        status= result
    )

if __name__ == '__main__':
    redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS)
    port = int(os.environ.get('PORT', 8000))
    app.run(host="0.0.0.0", port=8000)

