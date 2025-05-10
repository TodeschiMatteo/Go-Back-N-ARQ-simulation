# Simulazione del protocollo Go-Back-N con socket UDP

## Introduzione

Questo elaborato espone la realizzazione di una simulazione del protocollo Go-Back-N ARQ (Automatic Repeat reQuest) utilizzando socket UDP in Python.

Il protocollo Go-Back-N è un protocollo di livello 2 (collegamento) che garantisce la trasmissione affidabile di pacchetti anche su canali di comunicazione inaffidabili, come ad esempio UDP.

## Architettura

Il progetto è composto da 4 componenti principali:

1. **Client**: Responsabile dell'invio dei pacchetti e della gestione delle ritrasmissioni
2. **Server**: Responsabile della ricezione dei pacchetti e dell'invio degli ACK
3. **File di configurazione**: Contiene i parametri di configurazione per client e server
4. **File di logging**: Tengono traccia dell'operato dei due script e delle loro interazioni con i pacchetti

### Parametri di configurazione

I parametri principali sono configurabili tramite il file `config.json`

Per il server abbiamo:
- `IP`: Ip del server (da lasciare vuoto per usare l'indirizzo locale della macchina)
- `PORT`: Porta di comunicazione (default: 1235)
- `BUFFER SIZE`: Dimenzione del buffer (default: 1024)

Per il client abbiamo in aggiunta anche:
- `WINDOW_SIZE`: Dimensione della finestra di trasmissione (default: 3)
- `TOTAL_PACKETS`: Numero totale di pacchetti da inviare (default: 20)
- `TIMEOUT`: Tempo di attesa prima della ritrasmissione (default: 1.0 secondi)
- `PACKET_LOSS_RATIO`: Probabilità di perdita simulata dei pacchetti (default: 0.2 o 20%)
- `MAX_TIMEOUTS`: Numero massimo di timeout consecutivi prima di interrompere la trasmissione (default: 10)

Da notare che IP e PORT devono essere compatibili nelle due configurazioni per inizializzare una trasmissione corretta


## Implementazione del protocollo Go-Back-N

### Client

Il client implementa le seguenti funzionalità:
- Creazione e invio di pacchetti json con numeri di sequenza
- Gestione della finestra di trasmissione con dimensione configurabile
- Rilevamento del timeout e ritrasmissione di tutti i pacchetti nella finestra
- Simulazione della perdita di pacchetti con probabilità configurabile
- Interruzione dell'invio in caso di errori frequenti con relativa comunicazione al server
- Registrazione di statistiche sulla trasmissione (pacchetti inviati, persi, ritrasmessi, ACK ricevuti)

### Server

Il server implementa le seguenti funzionalità:
- Ricezione di pacchetti json dal client
- Verifica dell'ordine dei pacchetti ricevuti
- Invio di ACK solo per i pacchetti ricevuti nel corretto ordine
- Scarto dei pacchetti ricevuti fuori ordine
- Registrazione di statistiche sulla ricezione (pacchetti ricevuti, accettati, scartati)

## Come eseguire
1. Avviare in una sessione il file server e attendere che si avvii correttamente
2. Avviare in un'altra sessione il client e attendere l'esito

## Flusso di esecuzione

1. Il server viene avviato e si mette in ascolto di pacchetti in arrivo
2. Il client inizia a inviare pacchetti all'interno della finestra di trasmissione
3. Se il server riceve un pacchetto con il numero di sequenza atteso, invia un ACK
4. Se il client riceve un ACK, fa avanzare la base della finestra
5. Se il client non riceve un ACK entro il timeout, ritrasmette tutti i pacchetti nella finestra
6. Se il server riceve un pacchetto fuori ordine, lo scarta e invia un ACK per l'ultimo pacchetto ricevuto correttamente
7. Il processo continua finché tutti i pacchetti non sono stati consegnati correttamente
8. Il client invia un marcatore di fine per indicare la conclusione della trasmissione


## Meccanismi di affidabilità

### Simulazione della perdita di pacchetti

Il client simula la perdita di pacchetti con una probabilità configurabile (`PACKET_LOSS_RATIO`).

Questo meccanismo permette di testare la robustezza del protocollo in condizioni di rete non ideali.

### Gestione dei timeout

Il client implementa un meccanismo di timeout per rilevare la perdita di pacchetti.

Se non viene ricevuto un ACK entro il timeout configurato, il client ritrasmette tutti i pacchetti nella finestra a partire dalla base.

Inoltre se continuano a verificarsi troppi timeout consecutivi, il client interrompe la trasmissione e invia un pacchetto `ABORT` al server in modo da ottenere la corretta terminazione dei due script.

### Gestione dei pacchetti fuori ordine

Il server accetta solo i pacchetti con il numero di sequenza atteso.

Se riceve un pacchetto fuori ordine, lo scarta e invia un ACK per l'ultimo pacchetto ricevuto correttamente. 

Questo meccanismo permette al client di ritrasmettere i pacchetti persi o scartati.

## Statistiche di performance

Il sistema raccoglie diverse statistiche sulla trasmissione:

### Client
- Numero di pacchetti inviati
- Numero di pacchetti persi (simulati)
- Numero di ritrasmissioni
- Numero di ACK ricevuti
- Tempo totale di trasmissione

### Server
- Numero di pacchetti ricevuti 
- Numero di pacchetti accettati
- Numero di pacchetti scartati

Queste statistiche sono registrate nei file di log e forniscono informazioni utili sulla performance del protocollo in diverse condizioni di rete.

## Schema del flusso del protocollo

```
              Client                                 Server
                |                                       |
Send 0, 1, 2    |                                       |
                |  ----------------------------------→  |
                |                                       | Received 0, ACK 0
                |  ←----------------------------------  |
                |                                       | Received 1, ACK 1
                |  ←----------------------------------  |
                |                                       | 2 Lost
                |                                       |
Timeout 2       |                                       |
                |                                       |
Send 2, 3, 4    |                                       |
                |  ----------------------------------→  |
                |                                       | Received 2, ACK 2
                |  ←----------------------------------  |
                |                                       | Received 3, ACK 3
                |  ←----------------------------------  |
                |                                       | Received 4, ACK 4
                |  ←----------------------------------  |
                |                                       |
Send 5, 6, 7    |                                       |
                |  ----------------------------------→  |
                |                                       |
                |            ... continue ...           |
```

## Conclusioni

Grazie a questa simulazione mi è stato possibile apprendere in modo efficace il comportamento del protocollo Go-Back-N ARQ.

In particolare è stato molto utile preoccuparsi di simulare la perdita e il rinvio dei pacchetti per assumere consapevolezza dei vantaggi e dei limiti del protocollo in questione.

### Vantaggi
 - Più efficiente di Stop-and-Wait grazie all'utilizzo della FInestra in modo da non dover aspettare ciascun ACK
 - Il server è molto semplificato evitando avantuali buffer per pacchetti fuori ordine o errati
 - Permette una pronta rilevazione e correzzione delle perdite

### Limiti
 - La ritrasmissione è inefficiente perchè anche un solo pacchetto perso comporta la ritrasmissione di tutta una finestra, considerando poi che il server scarta i pacchetti fuori ordine
 - In caso di reti molto lente la ritrasmissione pesa molto sull'efficienza