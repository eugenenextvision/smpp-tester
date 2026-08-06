import time
import sqlite3
import os
import logging
import smpplib.client
import smpplib.gsm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

SMPP_HOST = "5.43.226.176"
SMPP_PORT = 2775
SYSTEM_ID = "Autotest"
PASSWORD = "vmrmwucu"

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'sms_queue.db')

def process_queue(client):
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now_ts = time.time()
        # Выбираем только те SMS, время которых НАСТУПИЛО и статус = pending
        cursor.execute("SELECT id, sender_id, phone_number, message FROM queue WHERE send_at <= ? AND status = 'pending'", (now_ts,))
        tasks = cursor.fetchall()

        for task in tasks:
            task_id, sender_id, phone_number, message = task
            try:
                parts, encoding_flag, msg_type = smpplib.gsm.make_parts(message)
                for part in parts:
                    pdu = client.send_message(
                        source_addr_ton=5,
                        source_addr_npi=0,
                        source_addr=sender_id,
                        dest_addr_ton=1,
                        dest_addr_npi=1,
                        destination_addr=phone_number,
                        short_message=part,
                        data_coding=encoding_flag,
                        esm_class=msg_type,
                        registered_delivery=True
                    )
                    logging.info(f"🚀 [SENT TO ALARIS] SMS -> {phone_number} | Sequence: {pdu.sequence}")
                
                # Помечаем SMS как отправленное ТОЛЬКО ПОСЛЕ успешной отправки в сокет
                cursor.execute("UPDATE queue SET status = 'sent' WHERE id = ?", (task_id,))
                conn.commit()

            except Exception as e:
                logging.error(f"🔴 Ошибка отправки ID {task_id}: {e}")

        conn.close()
    except Exception as e:
        logging.error(f"🔴 Ошибка работы с БД: {e}")

def start_worker():
    while True:
        client = None
        try:
            logging.info(f"Подключение к Alaris {SMPP_HOST}:{SMPP_PORT}...")
            client = smpplib.client.Client(SMPP_HOST, SMPP_PORT)
            client.connect()
            client.bind_transceiver(system_id=SYSTEM_ID, password=PASSWORD)
            logging.info("🟢 BIND SUCCESSFUL! Статус в Alaris: ONLINE")

            last_ping = time.time()

            while True:
                process_queue(client)
                
                # Читаем ответы от сервера (слушаем сокет)
                try:
                    client.poll(1)
                except smpplib.exceptions.PDUError:
                    pass
                except Exception:
                    pass
                
                # Keep-Alive каждые 30 секунд
                if time.time() - last_ping > 30:
                    try:
                        client.enquire_link()
                    except Exception:
                        pass
                    last_ping = time.time()

        except Exception as e:
            logging.error(f"🔴 Разрыв соединения: {e}. Переподключение через 5 сек...")
            if client:
                try:
                    client.disconnect()
                except Exception:
                    pass
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
