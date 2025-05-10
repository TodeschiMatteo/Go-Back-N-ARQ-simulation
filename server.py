#!/usr/bin/env python

"""
Go-Back-N ARQ Protocol Server Implementation
@authors: Matteo TODESCHI
"""

import sys
import os
import logging
import time
import socket
import json

# Apre file di configurazione
with open('config.json', 'r') as f:
    config = json.load(f)

# Creazione del file di log e della directory per i log se non esiste
log_dir = "log/server"
os.makedirs(log_dir, exist_ok=True)
log_filename = f"{log_dir}/server.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

# Configurazione le variabili globali
BUFFER_SIZE = config["server"]["BUFFER_SIZE"]

# Creazione di un pacchetto ACK
def create_ack(ack_num):
    ack_packet = {"header": {"ack_num": ack_num}}
    return json.dumps(ack_packet).encode()

# Estrazione della sequenza da un pacchetto
def extract_seq_num(packet):
    try:
        decoded = json.loads(packet.decode())

        # Controlla eventuale interruzione del client
        if "abort" in decoded.get("header", {}):
            return "ABORT"
        
        # Controlla se e' l'ultimo pacchetto
        if "end" in decoded.get("header", {}):
            return None
            
        return decoded["header"]["seq_num"]
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Error parsing packet: {e}")
        return -1

# Salva le statistiche nel log
def stats_to_log(stats):
    logging.info("====== Server Statistics ======")
    logging.info(f"Total packets received: {stats['packets_received']}")
    logging.info(f"Packets accepted: {stats['packets_accepted']}")
    logging.info(f"Packets discarded: {stats['packets_discarded']}")
    logging.info("==============================")

def main():
    
    # Inzzializzazione della struttura deti per le statistiche
    stats = {
        "packets_received": 0,
        "packets_accepted": 0,
        "packets_discarded": 0
    }
    
    # Setup del socket
    time.sleep(1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = config["server"].get("IP", "")
    if not ip:
        host = socket.gethostname()
        ip = socket.gethostbyname(host)
    else:
        host = ip
    port = config["server"]["PORT"]
    print(f"Socket started on {host} -> {ip}:{port}")
    time.sleep(1)
    s.bind((host, port))
    
    # Inizio della ricezione
    logging.info("============================================================")
    logging.info(f"Starting Go-Back-N server on {host} -> {ip}:{port}")
    logging.info("Waiting for packets...")
    
    # Inizializzazioni variabili del protocollo
    expected_seq_num = 0
    
    running = True
    while running:
        try:
            data, client_address = s.recvfrom(BUFFER_SIZE)
            stats["packets_received"] += 1
            
            seq_num = extract_seq_num(data)
            
            # Controllo se la trasmissione è terminata
            if seq_num is None:
                logging.info("Received end marker, terminating")
                running = False
                continue
            
            logging.info(f"Received packet with seq_num {seq_num} from {client_address}")
            
            # Processo i pacchetti soltanto se hanno il numero di sequenza previsto
            if seq_num == expected_seq_num:
                logging.info(f"Packet {seq_num} accepted, sending ACK")
                stats["packets_accepted"] += 1
                
                # Invio l'ACK per il pacchetto
                ack_packet = create_ack(seq_num)
                s.sendto(ack_packet, client_address)
                
                # Aggiorno numero di sequenza previsto per la prossima iterazione
                expected_seq_num += 1
            elif seq_num == "ABORT":
                logging.error("Received abort signal from client. Shutting down server.")
                running = False
                break
            else:
                logging.info(f"Out-of-order packet {seq_num} discarded, expected {expected_seq_num}")
                stats["packets_discarded"] += 1
                
                # Invio l'ACK per l'ultimo pacchetto ricevuto correttamente in modo
                # che seguendo le regole del protocollo Go-Back-N mi vengano ritrasmessi
                # i successivi per ovviare all'errore di trasmissione
                if expected_seq_num > 0:
                    ack_packet = create_ack(expected_seq_num - 1)
                    s.sendto(ack_packet, client_address)
        
        except (socket.error, json.JSONDecodeError) as e:
            logging.error(f"Error: {e}")
    
    # Produzione del log con le statistiche
    stats_to_log(stats)
    
    # Chiusura del Socket
    s.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Server terminated by user")
        sys.exit(0)