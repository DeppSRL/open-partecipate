Questo file contiene la descrizione dei tracciati record e dei singoli campi per i CSV scaricabili di OpenPartecipate.

Il pacchetto zip, oltre a questo file di *metadati*, contiene tre files CSV di dati:

- ``partecipate.csv``: anagrafica delle partecipate, con categorizzazione in tipologie e indicatori per l'ultimo anno di rilevazione
- ``quote.csv``: quote di partecipazione pubblica detenute da enti partecipanti
- ``regioni_settori.csv``: settori e regioni di attività delle partecipate

Note
----
I campi sono da intendere come valori *di stringa* o alfanumerici, e obbligatori, ove non specificato altrimenti.
Quando possibile, sono elencati i possibili valori che quel campo può avere.
I campi non obbligatori, possono prendere valori nulli.

partecipate.csv
---------------

codice (intero)
  codice numerico univoco interno della partecipata
  
codfisc_partiva
  codice fiscale della partecipata (può non essere univoco)
  
denominazione
  denominazione estesa della partecipata

anno_inizio (intero, formato YYYY)
  anno di inizio delle attività della partecipata

anno_cessazione (intero, formato YYYY, non obbligatorio);
  anno di cessazione delle attività (se cessate); ha valore nullo se l'attività è ancora in corso

indirizzo (non obbligatorio)
  indirizzo della *sede legale* della partecipata

regione (non obbligatorio)
  regione della *sede legale* della partecipata
  
provincia (non obbligatorio)
  provincia della *sede legale* della partecipata
  
comune (non obbligatorio)
  comune della *sede legale* della partecipata
  
cap (non obbligatorio)
  codice di avviamento postale della *sede legale* della partecipata
  
tel (non obbligatorio)
  numero di telefono della *sede legale* della partecipata;
  possono essere specificati valori multipli, separati dal carattere ";"

fax (non obbligatorio)
  numero di fax della *sede legale* della partecipata;
  possono essere specificati valori multipli, separati dal carattere ";"

email (non obbligatorio)
  email di contatto per la partecipata;
  possono essere specificati valori multipli, separati dal carattere ";"
  
soc_quotata (valore booleano)
  se la società è quotata in borsa;
  assume i valori "Sì" o "No"
  
anno_rilevazione (intero, formato YYYY)
  anno in cui la rilevazione dei dati è stata effettuata e per il quale i dati sono validi
  
tipologia
  categorizzazione di alto livello, per distinguere se si tratta di imprese o amministrazioni pubbliche;
  assume questi valori:
  
  - Amministrazioni Locali
  - Amministrazioni Regionali
  - Imprese pubbliche locali


categoria
  categorizzazione di secondo livello;
  può prendere questi valori:
  
  - Altre società di servizi
  - Autorità ed Enti portuali
  - Aziende pubbliche e istituzioni
  - Camere di Commercio
  - Consorzi e Forme associative
  - Enti dipendenti
  - Fondazioni culturali
  - Società di pubblici servizi  

sottotipo
  categorizzazione di terzo livello della partecipata;
  è quello utilizzato nell'applicazione;
  può prendere questi valori:

  - Agenzie regionali
  - Autorità ed Enti portuali
  - Aziende di edilizia residenziale di livello regionale
  - Aziende speciali e municipalizzate
  - Camere di commercio
  - Consorzi di bonifica
  - Consorzi istituiti e/o partecipati da province e/o comuni
  - Enti di promozione turistica di livello regionale
  - Enti e Istituti regionali
  - Enti per il diritto allo studio universitario
  - Enti pubblici economici di livello sub-regionale
  - Fondazioni sub-regionali - Cultura
  - Società di capitali a partecipazione regionale, per la gestione di pubblici servizi
  - Società di capitali a partecipazione sub-regionale, per la gestione di pubblici servizi
  - Società di capitali a partecipazione regionale con attività diversa dalla gestione di pubblici servizi
  - Società di capitali a partecipazione sub-regionale con attività diversa dalla gestione di pubblici servizi

dimensione (valuta, 2 cifre decimali)
  indicatore di dimensione della partecipata; 
  è il valore totale della spesa al netto del rimborso dei prestiti


partecipazione_pa (valore percentuale, 2 cifre decimali)
  percentuale di azioni detenute dall’insieme degli enti pubblici partecipanti o, 
  per estensione nel caso di soggetti che non siano società (ad esempio gli Enti dipendenti), 
  percentuale di controllo esercitato dall’insieme degli enti pubblici

spese_investimento (valore percentuale, 2 cifre decimali)
  rapporto tra la spesa di investimento e il totale della spesa al netto del rimborso di prestiti, 
  in termini di flussi finanziari di cassa
  
spese_personale (valore percentuale, 2 cifre decimali)
  rapporto tra la spesa di personale e il totale della spesa al netto del rimborso di prestiti, 
  in termini di flussi finanziari di cassa

risultato_finanziario
  indicatore per il risultato finanziario della partecipata;
  può assumere questi valori:
  - Elevato deficit
  - Moderato deficit
  - Sostanziale pareggio
  - Moderato surplus
  - Elevato surplus
  
quota_pubblica (valore percentuale, 2 cifre decimali)
  percentuale di quota pubblica

quote_stimate (valore booleano)
  se le quote di partecipazione provengono da fonti documentato o sono stimate;
  assume i valori "Sì" o "No"

altri_soci_noti (valore percentuale, 2 cifre decimali)
  percentuale di azioni in mano ad altri soci noti
  queste partecipazioni non sono esplicitate nel dettaglio delle quote


altri_soci_noti_pubblici (valore percentuale, 2 cifre decimali)
  percentuale di azioni in mano ad altri soci noti, di natura pubblica
  queste partecipazioni non sono esplicitate nel dettaglio delle quote

altri_soci_noti_privati (valore percentuale, 2 cifre decimali)
  percentuale di azioni in mano ad altri soci noti, di natura privata
  queste partecipazioni non sono esplicitate nel dettaglio delle quote

altri_soci_non_noti (valore percentuale, 2 cifre decimali)
  percentuale di azioni in mano ad altri soci non noti
  queste partecipazioni non sono esplicitate nel dettaglio delle quote

