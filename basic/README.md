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

 * https://aip.dfs.de/BasicVFR
 * https://aip.dfs.de/BasicIFR

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

**TODO**
