# RELEASES

## v1.0.4 — 2026-03-11

Distribution update: Linux standalone executables added.

Added `dist/sysclock_gui` (Linux standalone, Dark version, PyInstaller) e `dist/sysclock_gui_clear` (Linux standalone, Clear version, PyInstaller). Aggiornato README.md (IT + EN) con sezione dedicata agli eseguibili standalone Linux e istruzioni di avvio. Aggiornate le tabelle Quick Launch Reference con le voci `dist/sysclock_gui` e `dist/sysclock_gui_clear`. Aggiornato il badge versione corrente a v1.0.4.

### Repository Metadata

- Tag: `v1.0.4`
- GitHub release: SYSCLOCK v1.0.4
- Main assets: `dist/sysclock_gui`, `dist/sysclock_gui_clear`

### Linux Build Commands

```bash
pyinstaller -F -w --name sysclock_gui sysclock_gui.py
pyinstaller -F -w --name sysclock_gui_clear sysclock_gui_clear.py
```

---

## v1.0.3 — 2026-03-10

Documentation update focused on screenshot placement and readability.

Aggiornato il badge versione corrente a v1.0.3. Espansa la sezione screenshot per includere entrambe le immagini `images/1.png` e `images/2.png`. Aggiunti riferimenti contestuali agli screenshot vicino alle sezioni del pannello operativo FT8/FT4 (italiano e inglese).

### Repository Metadata

- Tag: `v1.0.3`
- GitHub release: SYSCLOCK v1.0.3

---

## v1.0.2 — 2026-03-10

Release dedicated to the Windows standalone executable package.

Aggiunto e validato il target di build standalone per `SysClockControl.exe` (Windows 11). Aggiornata la documentazione per fornire un percorso di esecuzione senza Python per gli utenti Windows. Confermato il requisito di avvio come amministratore per tutte le operazioni sull'orologio di sistema.

### Repository Metadata

- Tag: `v1.0.2`
- GitHub release: SYSCLOCK v1.0.2
- Main asset: `SysClockControl.exe`

### Windows Build Command

```cmd
python -m PyInstaller -F -w --name SysClockControl sysclock_gui.py
```

---

## v1.0.1 — 2026-03-09

Patch release focused on repository presentation and documentation clarity.

Aggiunta una sezione screenshot in cima al README.md. Collegato l'asset immagine (`images/1.png`) per un'anteprima immediata dell'interfaccia. Miglioramenti minori al contesto della documentazione nella sezione iniziale del progetto.

### Repository Metadata

- Tag: `v1.0.1`
- GitHub release: SYSCLOCK v1.0.1

### Quick Run

```bash
sudo python3 sysclock_gui.py
```

---

## v1.0.0 — 2026-03-08

First public release of SYSCLOCK.

Applicazione desktop GUI scritta in Python 3 con tkinter. Inclusi: controlli step forward/backward dell'orologio di sistema, pannello di impostazione data e ora esatta, controlli enable/disable NTP, selezione e applicazione del fuso orario, grafico storico offset e log operazioni, scorciatoie da tastiera per il controllo rapido.

### Repository Metadata

- License: GNU GPL v3.0 (`LICENSE`)
- Tag: `v1.0.0`
- GitHub release: SYSCLOCK v1.0.0
- Topics: `python`, `tkinter`, `desktop-gui`, `system-clock`, `time-sync`, `ntp`, `timezone`, `clock-management`, `amateur-radio`, `ham-radio`, `ft8`, `ft4`, `wsjtx`, `jtdx`, `mshv`

### Quick Run

```bash
sudo python3 sysclock_gui.py
```
