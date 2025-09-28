DFS-AIP zum Druck aufbereiten
=============================

TL;DR
-----

**TODO**

Hintergrund
-----------

Die VFR- und IFR-Ausgaben des deutschen Luftfahrthandbuchs werden von der
Deutschen Flugsicherung nur online herausgegeben. Seit Anfang 2023 ist die
VFR-Ausgabe kostenfrei verfügbar (IFR bereits länger). Die Daten können unter

 * https://aip.dfs.de/BasicVFR/
 * https://aip.dfs.de/BasicIFR/

abgerufen werden. Die Daten werden als Einzelseiten bereitgestellt -- für die
AIP-IFR als PDF-Dateien, für die AIP-VFR leider nur als Rasterbilder. Legt man
im Cockpit Wert auf Papierkarten (insb. die Anflugblätter), kommt man um die
Aufbereitung der Bilddateien nicht herum. Es gibt keine einfache Möglichkeit
...

* mehrere Seiten zum Druck auszuwählen,
* nur aktualisierte Seiten zum Druck auszuwählen,
* mehrere ausgewählte Seiten für den Druck auf einem A4-Bogen zu platzieren,
* die ausgewählten Seiten so zu platzieren, dass sie beim Duplexdruck auch die
  passende Rückseite erhalten.

An dieser Stelle sollen die hier bereitgestellten Skripte helfen. Die Skripte
sind in Python implementiert und zur Verwendung über die Kommandozeile unter
Linux implementiert. Code-Vorschläge für eine GUI-Version sind gern gesehen.

Es gibt keinen direkten Weg zielgerichtet Einzelseiten herunterzuladen. Der
Zugriff erfolgt zweistufig. Zuerst wird das gesamte Inhaltsverzeichnis
heruntergeladen. Anschließend lassen sich Einzelseiten anhand der Referenzen
im Inhaltsverzeichnis nachladen.

Mangels einer maschinenlesbaren API, erfolgt der Download durch Auswertung der
Webseiten. Dieses Verfahren ist sehr instabil bzgl. zukünftiger Änderungen des
Web-Portals. Es kann also passieren, dass dieses Werkzeug vom einen auf den
anderen Tag den Dienst versagt. Beim Zugriff auf die AIP ist Verantwortung
geboten. Der automatisierte Abruf von AIP-Seiten, sollten auf die notwendigen
Seiten beschränkt werden, um Lastbeschränkungen zu vermeiden. Im Gegenzeug
werden einmal erhaltene Daten zwischengespeichert und führen so im Gegensatz
zum Zugriff per Web-Browser nicht zu einem erneuten Download.


Vorbereitung
------------

Das Skript benötigt einige Python-Pakete, die in `requirements.txt` aufgeführt
sind. Die Bibliotheken können entweder über die Paketverwaltung des
Betriebssystems oder per `pip` in einem separaten `virtualenv` installiert
werden.

```
$ python -m venv /pfad/zum/venv/aip
$ source /pfad/zum/venv/bin/aip/activate
(aip) $ pip install -r requirements.txt
```


Funktionsweise
--------------

Das Programm verfügt über eine Reihe von Unterkommandos, die verschiedene
Funktionen erfüllen. Folgende Funktionen sind implementiert.

| Kommando      | Funktion                           |
| ------------- | ---------------------------------- |
| `toc fetch`   | Inhaltsverzeichnis herunterladen   |
| `toc list`    | Inhaltsverzeichnisse anzeigen      |
| `page fetch`  | Seiten herunterladen               |
| `page tree`   | Seitenbaum anzeigen                |
| `page list`   | Seiten anzeigen                    |
| `page diff`   | Geänderte Seiten anzeigen          |
| `pdf summary` | Einfache Zusammenfassung erstellen |

Zu jedem Kommando ist mit dem Parameter `-h` eine Beschreibung aller Parameter
verfügbar.

### Inhaltsverzeichnis herunterladen

Zunächst muss das Inhaltsverzeichnis der aktuellen AIP-Ausgabe heruntergeladen
werden.

```
$ ./aip.py toc fetch --vfr
GEN Allgemeine Information
  GEN 0
  GEN 1
  GEN 2
  GEN 3
  GEN 4
ENR Streckeninformation
  ENR 0
  ENR 1
...
```

Auf folgende Weise lässt sich anzeigen, für welche AIP-Ausgaben ein
Inhaltsverzeichnis vorliegt.

```
$ ./aip.py toc list
VFR  2023-04-06  /home/ppl/.cache/dfs-aip/VFR-2023-04-06.json
IFR  2023-03-23  /home/ppl/.cache/dfs-aip/IFR-2023-03-23.json
VFR  2023-03-09  /home/ppl/.cache/dfs-aip/VFR-2023-03-09.json
```

Die Ausgabe lässt sich auch nach Flugregeln filtern.

```
$ ./aip.py toc list --vfr
VFR  2023-04-06  /home/ppl/.cache/dfs-aip/VFR-2023-04-06.json
VFR  2023-03-09  /home/ppl/.cache/dfs-aip/VFR-2023-03-09.json
```

### Seiten anzeigen

Die Seiten lassen sich wie folgt auflisten.

```
$ ./aip.py page list --vfr -f "ENR 3 1-ENR 3 10" "AD EDCJ"
ENR 3 1:        Gebiete mit Flugbeschränkungen und Gefahrengebiete
ENR 3 2
ENR 3 2A
ENR 3 3
ENR 3 4
ENR 3 4A
ENR 3 4B
ENR 3 4C
ENR 3 4D
ENR 3 5:        Einzelheiten des Verwaltungsverfahrens für die Erteilung allgemeiner Genehmigungen des Durchfluges durch das Gebiet mit Flugbeschränkungen ED-R 146 (Berlin)
ENR 3 6
ENR 3 7
ENR 3 8
ENR 3 9
ENR 3 10:       Gebiete mit besonderen Aktivitäten
AD EDCJ 1:      Chemnitz Jahnsdorf
AD EDCJ 2:      Chemnitz Jahnsdorf
```

Der Parameter `-f`/`--filter` ermöglicht es, nur bestimmte Seiten in die
Ausgabe zu übernehmen. Es lassen sich ganze Kapitel, einzelne Seiten oder
Bereiche angeben. Die Seitenangaben orientieren sich an den Bezeichnern und
Abschnittsnummern der Gliederungsstruktur. Die einzelnen Gliederungsebenen
werden durch Leerzeichen getrennt. Deshalb müssen die Angaben auf der Shell in
`"` geklammert werden. Ein besten wird die Formulierung der Filterausdrücke
durch Beispiele deutlich:

 * `GEN` gibt das gesamte Kapitel "GEN" aus.
 * `ENR 1` gibt den zweiten Abschnitt (Zählung beginnt ab 0) des Kapitel "ENR"
   aus
 * `AD EDCJ` gibt die Anflugblätter für Chemnitz/Jahnsdorf (EDCJ) aus.
 * `GEN 0 1-GEN 0 10` gibt die Seiten 1 bis 10 aus dem Abschnitt "GEN 0" aus.
 * `ENR 1-ENR 2` gibt die Abschnitte "ENR 1" und "ENR 2" aus.
 * `GEN 0 33-GEN 0` gibt die Seiten ab "GEN 0-30" bis zum Ende des Kapitels
   "GEN 0" aus.

Bei mehreren Filtern wir die Gesamtmenge ausgegeben. Ohne Filter werden alle
Seiten ausgegeben.

Mit dem Parameter `--pairs` werden zu den jeweiligen Seiten auch die
entsprechenden Vorder- und Rückseiten ausgegeben. Ggf. werden Leerseiten
eingefügt.

```
$ ./aip.py page list --vfr -f "GEN 0-GEN 0 9" --pairs
V  GEN 0 1:     Inhaltsverzeichnis
R  ---
V  GEN 0 3:     Vorwort
R  GEN 0 4
V  GEN 0 5
R  ---
V  GEN 0 7:     Berichtigungsverzeichnis
R  ---
V  GEN 0 9:     Prüfliste
R  GEN 0 10
```

Mit dem Parameter `-a`/`--airac` werden die Seiten des angegebenen AIRAC-Datums
ausgegeben werden. Das Inhaltsverzeichnis muss zuvor heruntergeladen worden
sein. Ohne Angabe wird die aktuellste Ausgabe angenommen.

```
$ ./aip.py page list --vfr -a 2023-03-09 -f "GEN 0 33-GEN 0"
GEN 0 33:       Ausgewählte Berichtigungen zur Luftfahrtkarte ICAO 1 : 500 000
GEN 0 34
GEN 0 35
GEN 0 36
GEN 0 37
GEN 0 38
```

Mit dem Parameter `-b`/`--base-airac` wird ein Vergleich zwischen zwei
AIRAC-Ausgaben vorgenommen. Es werden dann nur Seiten ausgegeben, die sich seit
dieser Version geändert haben.

```
$ ./aip.py page list --vfr -b 2023-03-09 -a 2023-04-06 -f ENR
ENR 1 73
ENR 1 80
ENR 1 84
ENR 1 89
ENR 1 91
ENR 2 4
```

Die hier beschriebenen Parameter gelten auch für eine Reihe weiterer Kommandos.
Das Kommando `page list` dient i.d.R. nur dazu die Wirkung der Filter bzw. den
Abgleich zwischen verschiedenen Ausgaben zu prüfen.

### Liste an Nachträgen erstellen

Mit dem Kommando `page diff` kann man Änderungen zwischen Ausgaben anzeigen.
Dabei wird im Gegensatz zu `page list` auch angezeigt, welche Alteseiten zu
entfernen sind.

```
$ ./aip.py page diff --vfr -b 2023-03-09 -a 2023-04-06
** geändert     GEN 0 7
...
** geändert     GEN 0 33
-- gelöscht     GEN 0 34
-- gelöscht     GEN 0 35
-- gelöscht     GEN 0 36
-- gelöscht     GEN 0 37
-- gelöscht     GEN 0 38
** geändert     ENR 1 73
...
++ hinzugefügt  AD EDDM 4
** geändert     AD EDDM 5
++ hinzugefügt  AD EDDM 6
-- gelöscht     AD EDDM 7
-- gelöscht     AD EDDM 8
...
```

### PDF-Zusammenstellung erzeugen

Das Kommando `pdf summary` nimmt die selben Parameter wie `page list` entgegen.
Die Seiten werden jedoch nicht angezeigt, sondern in einem PDF-Dokument
zusammengefasst.

Auf folgende Weise werden alle Seiten ausgegeben, die sich zwischen den
genannten Ausgaben geändert haben. Es werden ebenfalls die zugehörigen Vorder-
bzw. Rückseiten bzw. Leerseiten übernommen, auch wenn sie sich nicht geändert
haben.

```
$ ./aip.py pdf --output amdt-2023-04.pdf summary --vfr -b 2023-03-09 -a 2023-04-06 --pairs
```


Danksagung
----------

Für Weiterentwicklung, Fehlerbeseitigung und Anregungen danke ich (in
zeitlicher Reihenfolge der Erstbeiträge):

 * Franz Pletz <fpletz@fnordicwalking.de>
