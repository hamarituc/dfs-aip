DFS-AIP zum Druck aufbereiten
=============================

TL;DR
-----

1. Karten zusammenfassen.

```
./vfr_print.py --cropmark --output print.pdf karte1.pdf karte2.pdf
```

2. Ausdrucken (Duplex lange Kante)
3. Schneiden
4. Lochen
5. Fertig


Hintergrund
-----------

Die VFR- und IFR-Ausgaben des deutschen Luftfahrthandbuchs werden von der
Deutschen Flugsicherung nur noch als PDF-Dateien herausgegeben. Für die
VFR-Ausgabe muss ein Abo abgeschlossen werden. Die Daten können dann unter
https://www.eisenschmidt.aero/aip-vfr abgerufen werden. VFR-Supplements und
VFR-AICs gibt es auch ohne Abo unter https://aip.dfs.de/supplements/vfr/.
Die IFR-Ausgabe ist kostenfrei unter https://aip.dfs.de/basicIFR/ bzw.
https://www.ead.eurocontrol.int abrufbar.

Legt man im Cockpit Wert auf Papierkarten (insb. die Anflugblätter), kommt man
um die Aufbereitung der PDF-Dateien nicht herum. Das AIP-Portal stellt die
Seiten nur einzeln bereit. Es gibt keine einfache Möglichkeit ...

* mehrere Seiten zum Druck auszuwählen,
* nur aktualisierte Seiten zum Druck auszuwählen,
* mehrere ausgewählte Seiten für den Druck auf einem A4-Bogen zu platzieren,
* die ausgewählten Seiten so zu platzieren, dass sie beim Duplexdruck auch die
  passende Rückseite erhalten.

An dieser Stelle sollen die hier bereitgestellten Skripte helfen. Die Skripte
sind in Python implementiert und zur Verwendung über die Kommandozeile unter
Linux implementiert. Code-Vorschläge für eine GUI-Version sind gern gesehen.

Da ich (vermutlich) keine Beispieldaten aus der AIP hier veröffentlichen darf,
ist die Anleitung in manchen Teilen etwas theoretisch. Sorry.


Vorbereitung
------------

Die Skripte benötigen die PDF-Bibliothek `pikepdf` (siehe
https://github.com/pikepdf/pikepdf). Die Bibliothek kann entweder über die
Paketverwaltung des Betriebssystems oder per `pip` in einem separaten
`virtualenv` installiert werden.

```
$ python -m venv /pfad/zum/venv/aip
$ source /pfad/zum/venv/bin/aip/activate
(aip) $ pip install -r requirements.txt
```


Funktionsweise
--------------

Die Skripte `vfr_print.py` und `ifr_print.py` erstellen aus den einzelnen PDFs
aus dem DFS-Portalen ein Gesamt-PDF für den Druck. Es können auch nur einzelnen
Seiten aus einem PDF ausgewählt werden, wenn sich z.B. nur eine Seite eines
größeren Kartenpakets geändert hat. Zur Auswahl der Seiten, siehe den Abschnitt
"Seitenauswahl" unter "Interna".

Es empfiehlt sich immer ganze Kapitel bzw. den kompletten Kartensatz eines
Flugplatzes aus dem AIP-Portal zu aktualisieren. Wird z.B. ein Anflugblatt
aktualisiert, enthält das entsprechende Amendment nur dieses Blatt. Das
rückseitige Rollschema ist nicht enthalten, wird jedoch zur Erstellung des
Druck-PDFs benötigt, damit die Rückseite der Anflugkarte nicht leer bleibt.

Beide Kommandos haben gleichlautende Parameter, die folgendes bewirken.

* `--output` Dateiname des zu erzeugenden PDFs

Mit folgenden Schaltern lassen sich Zusatzmarken einzeichnen. Sie werden nur
auf der Vorderseite eingezeichnet.

* `--cropmark` Schnittmarken einzeichnen
* `--punchmark` Lochmarken einzeichnen
* `--foldmark` Faltmarken einzeichnen

### AIP VFR

Auf folgende Weise werden die Karten der Flugplätze Chemnitz Jahnsdorf, Dresden
und Leipzig Halle für den Druck ausgegeben.

```
& ./vfr_print.py --tc-to-a4 --output print.pdf AD_C_D_Chemnitz_Jahnsdorf.pdf AD_C_D_Dresden.pdf AD_K_L_Leipzig_Halle.pdf
```

Das Skript kann natürlich auch für die Textteile GEN, ENR und AD verwendet
werden. 

*Hinweis:* Ggf. sind manuell Leerseiten einzufügen. Leerseiten werden durch die
  DFS nicht veröffentlicht. Für den Duplexdruck sind sie aber notwendig, damit
  Vorder- und Rückseite jedes Blatts zusammenpassen.

> Zum Beispiel fehlen im Kapitel "GEN 0" die Seiten GEN 0-2, GEN 0-6, GEN 0-8,
> GEN 0-32 und GEN 0-34. Die Zuordnung der Seiten lautet also
>
> | Seite im PDF | Seite in der AIP |
> | ------------:|:---------------- |
> |            1 | GEN 0-1          |
> |            - | GEN 0-2          |
> |            2 | GEN 0-3          |
> |            3 | GEN 0-4          |
> |            4 | GEN 0-5          |
> |            - | GEN 0-6          |
> |            5 | GEN 0-7          |
> |            - | GEN 0-8          |
> |            6 | GEN 0-9          |
> |            7 | GEN 0-10         |
> |          ... | ...              |
> |           28 | GEN 0-31         |
> |            - | GEN 0-32         |
> |           29 | GEN 0-33         |
> |            - | GEN 0-34         |
> |           30 | GEN 0-35         |
>
> Diese Seiten können durch den Ausdruck `{}` im Rahmen der Seitenauswahl
> ergänzt werden. Für die Funktion der Seitenauswahl siehe den entsprechenden
> Abschnitt unter "Interna". Hier ein Beispiel für die obigen Anwendungsfall.
>
> ```
> & ./vfr_print.py --output print.pdf GEN_0.pdf 1,{},2-4,{},5,{},6-28,{},29,{},30
> ```

Das Skript stellt zudem folgende Optionen bereit.

* `--tc-to-a4` Terminal Charts werden auf A4-Faltkarten herunterskaliert. Dies
  ist praktisch wenn man keinen A3-Drucker besitzt oder die A3-Karten zu
  sperrig für das Cockpit oder Kniebrett sind.

### AIP IFR

**TODO:** Das Skript `ifr_print.py? ist noch in Arbeit.


Drucken, schneiden und lochen
-----------------------------

Das erstellte Gesamt-PDF wird auf A4-Papier gedruckt. Es ist Duplexdruck
entlang der langen Papierkante zu aktivieren. Bei den Druckeinstellungen müssen
alle zusätzlichen Druckränder deaktiviert werden, damit keine weitere
Skalierung oder Verschiebung des Seiteninhalts erfolgt. Es empfiehlt sich
Papier mit 50g/m² oder 60g/m² zu verwenden, damit ein vorhandener AIP-Ordner
nicht irgendwann überquillt.

A4-Bögen die zwei A5-Seiten enthalten, müssen in der Mitte geschnitten werden.
Die (ggf. unsaubere) Schnittkante ist zugleich auch immer der Lochrand. Auf
A4-Faltseiten ist rechts ein Rand von 20mm abzuschneiden, damit der Lochrand
bei der Heftung frei bleibt.

Die Heftlöcher haben einen Durchmesser von 8mm. Die Lochmittelpunkte befinden
sich in folgenden Abständen vom oberen Seitenrand.

*  25mm
*  65mm
* 145mm
* 185mm

Der Abstand zwischen den inneren Löchern beträgt somit 80mm oder zwischen den
äußeren und den benachbarten inneren Löchern jeweils 40mm. Zur Lochung
empfiehlt sich z.B. der variable Mehrfachlocher Leitz AKTO (Art.-Nr. 51140084),
der mit vier 8mm-Lochsegmenten (Art.-Nr. 51240000) ausgerüstet werden muss.


Interna
-------

### Seitenauswahl

Jedes PDF welches auf der Kommandozeile angegeben wird, wird mit allen Seiten
in die Ausgabe übernommen. Es besteht jedoch die Möglichkeit nur bestimmte
Bereiche, ausgewählte Seiten oder zusätzliche Leerseiten zu übernehmen.
Bestimmte Seiten können auch mehrfach übernommen werden. Mit dem Skript
`aip_select.py` kann man diese Auswahl testen. Die Seitenauswahl ist aber auch
bei jedem anderen Skript möglich. Die Benutzung wird am besten am Beispiel
deutlich.

Folgender Ausdruck übernimmt die Seiten 1 bis 3 (`1-3`) und die Seite 5 (`,5`)
aus `test.pdf`:

```
./aip_select.py --output print.pdf test.pdf 1-3,5
```

Folgender Ausdruck übernimmt alle Seiten bis inkl. Seite 3 (`-3`) und alle
Seiten ab inkl. Seite 8 (`,8-`):

```
./aip_select.py --output print.pdf test.pdf -3,8-
```

Folgender Ausdruck übernimmt die Seite 1 (`1`), fügte eine Leerseite ein
(`,{}`) und fügt dann Seite 2 an (`,2`).

```
./aip_select.py --output print.pdf test.pdf 1,{},2
```

Folgender Ausdruck übernimmt alle Seiten des Dokuments (`-`) und hängt dann
noch einmal die Seiten 1, 3 und 5 an (`,1,3,5`).

```
./aip_select.py --output print.pdf test.pdf -,1,3,5
```

Das Prinzip ist relativ einfach:

* Seiten werden mit Komma `,` aufgezählt.
* Bereich lassen sich mit Bindestrich `-` angeben.
* Wird der Start eines Bereichs weggelassen, wird ab der ersten Seite begonnen.
* Wird das Ende eines Bereichs weggelassen, wird bis zur letzten Seite
  gegangen.
* Ein einzelner Bindestrich entspricht dem gesamten Dokument.
* Eine Leerseite wird durch geschweifte Klammern `{}` eingefügt.

### Seitenformat und Sortierregeln

Da es sich bei der AIP um eine Loseblattsammlung handelt, kommen verschiedene
Seitenformate zur Anwendung, die eine Einfluss auf die Sortierung für das
Druckdokument haben.

Die Formate der Seiten eines PDFs lassen sich mit dem Skript `aip_box.py`
anzeigen.

```
$ ./aip_box.py AD_C_D_Chemnitz_Jahnsdorf.pdf AD_C_D_Dresden.pdf AD_K_L_Leipzig_Halle.pdf
  #     Media   Crop    Trim    Rotation

test_vfr/AD_C_D_Chemnitz_Jahnsdorf.pdf
  1:    A5  p   A5  p   A5  p     0
  2:    A5  p   A5  p   A5  p     0

test_vfr/AD_C_D_Dresden.pdf
  1:    245x323 A4n p   A4n p   270
  2:    A3  p   A4n l   A4n l     0
  3:    A4  p   A4n p   A4n p   270

test_vfr/AD_K_L_Leipzig_Halle.pdf
  1:    TC  l   TC  l   TC  l     0
  2:    A5  p   A5  p   A5  p     0
  3:    A5  p   A5  p   A5  p     0
  4:    A4  p   A4n p   A4n p    90
```

Die Ausgabe im Beispiel bedeutet folgendes.

* Für Chemnitz sind 2 Seiten DIN A5 vorhanden
  1. Anflugblatt
  2. Rollschema (Rückseite von 1.)
* Für Dresden sind 3 Ausklappseiten DIN A4 vorhanden
  1. Übersicht der Kontrollzone
  2. Anflugblatt mit Flughafengelände (Rückseite von 1.)
  3. Rollschema (eigenständiges Blatt)
* Der Kartensatz für Leipzig besteht aus verschiedenen Formaten
  1. Terminal Chart mit Luftraum D
  2. A5-Seite als Überblick über die Kontrollzone (neues Blatt)
  3. A5-Seite als Anflugblatt mit Flughafengelände (Rückseite von 2.)
  4. A4-Ausklappseite als Rollschema (eigenständiges Blatt)

#### AIP VFR

In der AIP werden folgende Seitenformate verwendet.

* DIN A5 (148x210mm) für den Textteil und die Anflugblätter kleiner Flugplätze
* DIN A4 mit 20mm Beschnitt (277x210mm) für Anflugblätter größerer Flughäfen.
  Die Blätter sind auf A5 gefaltet, sodass sie in geheftetem Zustand nach
  rechts ausgeklappt werden können.
* DIN A4 ohne Rand (279x210mm) für einige Rollschemata. Vermutlich ist das
  Fehler bei der Veröffentlichung. 
* Terminal Charts (380x297mm)

Die Seiten werden nach folgende Regeln zusammensortiert.

* Jeweils zwei A5-Seiten werden auf einen A4-Bogen platziert.
* A4-Ausklappseiten werden auf einer einzelnen A4-Seite platziert.
* Folgen zwei Ausklappseiten aufeinander, wird die Folgeseite auf der Rückseite
  der ersten Seite gedruckt.
* Folgt eine A5-Seite auf eine Ausklappseite, wird die A5-Seite auf die
  Rückseite der Ausklappseite gedruckt.
* Mehrere Terminal Charts *am Anfang* eines PDFs werden jeweils abwechselnd auf
  die Vorder- und die Rückseite eines Bogens gedruckt.
* Terminal Charts *mitten* in einem PDF (z.B. Rollschemata größerer Flughäfen)
  werden jeweils auf eine eigene Seite gedruckt.

Diese Regeln wurden empirisch ermittelt. Ggf. kann das Ergebnis in Einzelfällen
falsche sein. Ggf. sind manuell Leerseiten im Rahmen der Seitenauswahl
einzufügen.

#### AIP IFR

**TODO**

### Fehlersuche

Sollte die Druckausgabe einmal nicht zusammenpassen, sind folgende Angaben für
die Fehlersuche notwendig.

* AIRAC-Termin der Ausgangsdaten
* Ausgabe von `aip_box.py` für die Eingabedaten
* Ggf. die Eingabedaten als PDF
* Ggf. das Ausgabedokument als PDF
* Beschreibung wie das Ergebnis aussehen sollte
* Beschreibung inwiefern die Ausgabe vom gewünschten Ergebnis abweicht


Limitierungen
-------------

Die PDF-Dateien werden von der DFS kryptografisch signiert. Die hier
bereitgestellten Skripte verifizieren diese Signaturen *nicht*. Wer die
Integrität der verwendeten PDF-Dateien sicherstellen will, muss dies zuvor
manuell auf separatem Weg erledigen.
