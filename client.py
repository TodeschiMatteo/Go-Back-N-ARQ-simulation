#!/usr/bin/env python

"""
Go-Back-N ARQ Protocol Client Implementation
@authors: Matteo TODESCHI

"""
import sys
import os
import logging
import time
import socket
import random
import json

# Apre file di configurazione
with open('config.json', 'r') as f:
    config = json.load(f)

# Creazione del file di log e della directory per i log se non esiste
log_dir = "log/client"
os.makedirs(log_dir, exist_ok=True)
log_filename = f"{log_dir}/client.log"

# Configurazione del logging con libreria di sistema
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

# Configurazione le variabili globali
BUFFER_SIZE = config["client"]["BUFFER_SIZE"]
WINDOW_SIZE = config["client"]["WINDOW_SIZE"]
TOTAL_PACKETS = config["client"]["TOTAL_PACKETS"]
TIMEOUT = config["client"]["TIMEOUT"]
PACKET_LOSS_RATIO = config["client"]["PACKET_LOSS_RATIO"]
MAX_TIMEOUTS = config["client"]["MAX_TIMEOUTS"]

# Creazione di un pacchetto
def create_packet(seq_num):
    data = f"Packet-{seq_num}".encode()
    header = {"seq_num": seq_num}
    packet = {"header": header, "data": data.decode()}
    return json.dumps(packet).encode()

# Invio di un pacchetto
def send_packet(sock, seq_num, server_address):
    packet = create_packet(seq_num)
    
    # Simulazione packet loss randomica con percentuale impostata
    if random.random() < PACKET_LOSS_RATIO:
        logging.info(f"Simulating loss of packet {seq_num}")
        return False
    
    sock.sendto(packet, server_address)
    logging.info(f"Sent packet {seq_num}")
    return True

# Estrazione dell'ACK da un pacchetto
def extract_ack(ack_packet):
    try:
        decoded = json.loads(ack_packet.decode())
        return decoded["header"]["ack_num"]
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Error parsing ACK: {e}")
        return None
    
# Salva le statistiche nel log
def stats_to_log(stats, elapsed_time):
    logging.info("====== Transmission Statistics ======")
    logging.info(f"Total packets sent: {stats['packets_sent']}")
    logging.info(f"Packets lost (simulated): {stats['packets_lost']}")
    logging.info(f"Retransmissions: {stats['retransmissions']}")
    logging.info(f"ACKs received: {stats['acks_received']}")
    logging.info(f"Elapsed time: {elapsed_time:.2f} seconds")
    logging.info("====================================")

def main():
    global WINDOW_SIZE, TOTAL_PACKETS, PACKET_LOSS_RATIO
    
    # Inzzializzazione della struttura deti per le statistiche
    stats = {
        "packets_sent": 0,
        "packets_lost": 0,
        "retransmissions": 0,
        "acks_received": 0
    }
    
    # Setup del socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = config["client"].get("IP", "")
    if not ip:
        host = socket.gethostname()
        ip = socket.gethostbyname(host)
    else:
        host = ip
    port = config["server"]["PORT"]
    print(f"Try connecting on {host} -> {ip}:{port}")
    time.sleep(1)
    server_address = (host, port)
    s.settimeout(TIMEOUT)
    
    # Inizio del traferimento
    logging.info("============================================================")
    logging.info(f"Starting Go-Back-N client with window size {WINDOW_SIZE} on {host} -> {ip}:{port}")
    start_time = time.time()
    
    # Inizializzazioni variabili del protocollo
    base = 0
    next_seq_num = 0

    # Limitazione di timeout consecutivi per evitare loop infiniti
    max_timeouts = MAX_TIMEOUTS
    consecutive_timeouts = 0
    
    while base < TOTAL_PACKETS:
        # Invia pacchetti all'interno della finestra
        while next_seq_num < base + WINDOW_SIZE and next_seq_num < TOTAL_PACKETS:
            if send_packet(s, next_seq_num, server_address):
                stats["packets_sent"] += 1
            else:
                stats["packets_lost"] += 1
            next_seq_num += 1
        
        # Prova a ricevere ACK entro il timeout
        try:
            start_wait = time.time()
            while time.time() - start_wait < TIMEOUT:
                try:
                    s.settimeout(TIMEOUT - (time.time() - start_wait))
                    data, _ = s.recvfrom(BUFFER_SIZE)
                    ack_num = extract_ack(data)
                    
                    if ack_num is not None:
                        if ack_num is not None:
                            if ack_num == base - 1:
                                logging.info(f"Received DUPLICATE ACK {ack_num}")
                            else:
                                logging.info(f"Received ACK {ack_num}")

                        stats["acks_received"] += 1
                        
                        # Tutti i pacchetti sono riconosciuti tramite l'ACK
                        if ack_num >= base:
                            base = ack_num + 1
                            consecutive_timeouts = 0
                        
                        if base >= TOTAL_PACKETS:
                            break
                except socket.timeout:
                    break
            
            if time.time() - start_wait >= TIMEOUT:
                raise socket.timeout
                
        except socket.timeout:
            consecutive_timeouts += 1

            # Controllo dei timeout consecutivi
            if consecutive_timeouts > max_timeouts:
                logging.error(f"Too many consecutive timeouts ({max_timeouts}). Aborting.")
                abort_packet = json.dumps({"header": {"abort": True}}).encode()
                s.sendto(abort_packet, server_address)
                break
            
            if base != (next_seq_num-1 if next_seq_num > base else base):
                logging.warning(f"Timeout #{consecutive_timeouts}: Retransmitting window from {base} to {next_seq_num-1 if next_seq_num > base else base}")
            else:
                logging.info(f"Transmitting a NEW window from packet {base}")
            
            # Ritrasmetti tutti i pacchetti della finestra
            for i in range(base, min(next_seq_num, TOTAL_PACKETS)):
                logging.info(f"Retransmitting packet {i}")
                if send_packet(s, i, server_address):
                    stats["packets_sent"] += 1
                    stats["retransmissions"] += 1
                else:
                    stats["packets_lost"] += 1
                    stats["retransmissions"] += 1
    
    # Invio conferma terminazione del flusso
    end_packet = json.dumps({"header": {"end": True}}).encode()
    s.sendto(end_packet, server_address)
    logging.info("Transmission complete, sent end marker")
    
    # Produzione del log con le statistiche
    elapsed_time = time.time() - start_time
    stats_to_log(stats, elapsed_time)
    
    # Chiusura del Socket
    s.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Client terminated by user")
        sys.exit(0)