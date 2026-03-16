import os
import requests
import shutil
import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")

if not BASE_URL:
    raise ValueError("BASE_URL ist nicht in der .env Datei gesetzt.")

# Using USB connected printer 
PRINTER_IDENTIFIER = '/dev/usb/lp1'

printer = BrotherQLRaster('QL-800')
def sendToPrinter():
    filename = 'qrcode.jpeg'
    print_data = brother_ql.brother_ql_create.convert(printer, [filename], '62', dither=True, red=True)
    send(print_data, PRINTER_IDENTIFIER)

    
token_url = f"{BASE_URL}/token"
token_header = {"Content-Type": "application/x-www-form-urlencoded"}
token_data = {"username": USERNAME, "password": PASSWORD}

token_res = requests.post(token_url, data = token_data, headers = token_header)

qrcode_all_url = f"{BASE_URL}/qrcode/all"
qrcode_all_headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + token_res.json()["access_token"]
    }

qrcodes_res = requests.get(qrcode_all_url, headers = qrcode_all_headers)
for qrcode in qrcodes_res.json():    
    label_url = f"{BASE_URL}/qrcode/create_label?task_id=" + str(qrcode["task_id"])
    label_headers = {
    "Content-Type": "application/json"
    }
    label_res = requests.get(label_url, headers=label_headers, stream=True)
    label_res.raw.decode_content = True
    with open('qrcode.jpeg', 'wb') as f:
        shutil.copyfileobj(label_res.raw, f)
    sendToPrinter()
    url = f"{BASE_URL}/qrcode/complete?qrcode_id=" + str(qrcode["id"])
    headers = {
    "Content-Type": "application/json"
    }
    res = requests.patch(url, headers=headers)
    print(res.text)
