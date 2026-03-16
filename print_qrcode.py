import os
import time
import logging
import requests
import shutil
import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
USERNAME = os.getenv("USERNAME", "")
PASSWORD = os.getenv("PASSWORD", "")
PRINTER_IDENTIFIER = os.getenv("PRINTER_IDENTIFIER", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))

if not BASE_URL:
    raise ValueError("BASE_URL ist nicht in der .env Datei gesetzt.")
if not USERNAME:
    raise ValueError("USERNAME ist nicht in der .env Datei gesetzt.")
if not PASSWORD:
    raise ValueError("PASSWORD ist nicht in der .env Datei gesetzt.")
if not PRINTER_IDENTIFIER:
    raise ValueError("PRINTER_IDENTIFIER ist nicht in der .env Datei gesetzt.")

printer = BrotherQLRaster("QL-800")


def get_token() -> str:
    token_res = requests.post(
        f"{BASE_URL}/token",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    token_res.raise_for_status()
    return token_res.json()["access_token"]


def send_to_printer(filename: str = "qrcode.jpeg") -> None:
    print_data = brother_ql.brother_ql_create.convert(
        printer, [filename], "62", dither=True, red=True
    )
    send(print_data, PRINTER_IDENTIFIER)


def check_and_print(token: str) -> str:
    """Prüft auf neue QR-Codes, druckt sie und markiert sie als erledigt.
    Gibt bei HTTP 401 'unauthorized' zurück, damit der Aufrufer den Token erneuert."""
    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    qrcodes_res = requests.get(
        f"{BASE_URL}/qrcode/all", headers=auth_headers, timeout=10
    )

    if qrcodes_res.status_code == 401:
        return "unauthorized"

    qrcodes_res.raise_for_status()
    qrcodes = qrcodes_res.json()

    if not qrcodes:
        log.debug("Keine neuen QR-Codes gefunden.")
        return "ok"

    for qrcode in qrcodes:
        task_id = qrcode["task_id"]
        qrcode_id = qrcode["id"]
        log.info("Drucke QR-Code für task_id=%s …", task_id)

        label_res = requests.get(
            f"{BASE_URL}/qrcode/create_label?task_id={task_id}",
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=15,
        )
        label_res.raise_for_status()
        label_res.raw.decode_content = True

        with open("qrcode.jpeg", "wb") as f:
            shutil.copyfileobj(label_res.raw, f)

        send_to_printer()

        complete_res = requests.patch(
            f"{BASE_URL}/qrcode/complete?qrcode_id={qrcode_id}",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        complete_res.raise_for_status()
        log.info("QR-Code %s als erledigt markiert: %s", qrcode_id, complete_res.text)

    return "ok"


def main() -> None:
    log.info("Starte Label-Printer-Dienst (Intervall: %ds) …", POLL_INTERVAL)
    token = get_token()
    log.info("Token erhalten.")

    while True:
        try:
            result = check_and_print(token)
            if result == "unauthorized":
                log.warning("Token abgelaufen – hole neuen Token …")
                token = get_token()
                check_and_print(token)
        except requests.RequestException as exc:
            log.error("Netzwerkfehler: %s", exc)
        except Exception as exc:
            log.error("Unerwarteter Fehler: %s", exc)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
