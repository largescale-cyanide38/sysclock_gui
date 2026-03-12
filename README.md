# SYSCLOCK — System Time Control

Ham Radio Tool
© 2026 Alessandro Orlando — GNU General Public License v3.0

Versione corrente / Current version: v1.0.4 (2026-03-11)

---

## Screenshot

### Dark Version

![SYSCLOCK GUI overview](images/1.png)

### Clear Version

![SYSCLOCK GUI operational panels](images/2.png)

---

## Italiano

### Descrizione

SYSCLOCK — System Time Control è un'applicazione desktop con interfaccia grafica (GUI) scritta interamente in Python 3 usando la libreria standard tkinter, senza dipendenze esterne.

È pensata specificamente per i radioamatori che operano con i modi digitali (FT8, FT4, JT65, JT9 e simili), dove la precisione dell'orologio di sistema è critica. Consente di correggere rapidamente la sincronizzazione del clock direttamente dal valore DT riportato da WSJT-X, JTDX o MSHV, e di gestire NTP, fuso orario e ora esatta in un'unica interfaccia.

---

### Perché i radioamatori ne hanno bisogno

I modi digitali deboli come FT8 e FT4 si basano su slot temporali fissi di 15 secondi sincronizzati con UTC. Se l'orologio del computer devia anche solo di 1–2 secondi, le decodifiche falliscono e la trasmissione diventa impossibile. Il parametro DT (Delta Time) mostrato da WSJT-X, JTDX e MSHV indica esattamente questo scarto.

SYSCLOCK permette di correggere il clock del PC in un click inserendo il valore DT, operare senza connessione internet (operazioni portatili, contest, SOTA, POTA), disabilitare NTP in modo completo per evitare che il demone reintroduca derive, impostare l'ora manualmente da un riferimento GPS o orologio atomico, e monitorare visivamente la deriva accumulata nel tempo tramite il grafico storico.

| Situazione | Come usare SYSCLOCK |
|---|---|
| DT mostrato in WSJT-X è ±0.5s o più | Inserire il valore DT nel pannello FT8 e premere **APPLY DT** |
| Operazione portatile senza internet | Disabilitare NTP, impostare l'ora con **SET EXACT TIME** da GPS |
| Deriva progressiva durante un contest | Monitorare il grafico storico e applicare correzioni DT al volo |
| NTP non disponibile o inaffidabile | Disabilitare NTP e usare **RESTORE CLOCK FROM SNAPSHOT** |
| Cambio fuso orario in trasferta | Aggiornare il SO con il pannello **TIMEZONE** in un click |

> Compatibile con WSJT-X · JTDX · MSHV

---

### Descrizione tecnica

| Voce | Dettaglio |
|---|---|
| Linguaggio | Python 3.8+ |
| GUI toolkit | tkinter (stdlib) + ttk |
| Dipendenze esterne | Nessuna |
| Sistemi operativi | Linux, macOS, Windows |
| Privilegi richiesti | root / amministratore per le operazioni di sistema |
| Architettura | Single-file, multi-thread con coda thread-safe (queue.Queue) |
| Licenza | GNU GPL v3.0 |

#### Funzioni attualmente in uso

| Funzione | Descrizione |
|---|---|
| `_linux_set_clock(dt)` | Imposta `CLOCK_REALTIME` via `clock_settime()` (libc, ns) + reset PLL con `adjtimex(2)` |
| `set_system_time(dt)` | Wrapper multi-OS: libc su Linux, `date` su macOS, `SetLocalTime` WinAPI su Windows |
| `ntp_enable()` | Unmask + riabilita tutti i demoni NTP noti tramite `timedatectl` e `systemctl` |
| `ntp_disable()` | Ferma, disabilita e maschera tutti i demoni NTP (incluso socket) + reset kernel PLL |
| `ntp_status()` | Verifica se NTP è attivo (`timedatectl` + `systemctl is-active` per ogni demone noto) |
| `get_timezones()` | Recupera l'elenco dei fusi orari (timedatectl / zoneinfo / tzutil) |
| `set_timezone(tz)` | Imposta il fuso orario di sistema (`timedatectl` / `systemsetup` / `tzutil`) |
| `RingBuffer` | Buffer circolare thread-safe per lo storico degli offset (120 campioni, ~2 min) |
| `SysClockApp` | Classe principale (tkinter.Tk), architettura producer/consumer con queue |
| `_do_step(ms)` | Calcola target da riferimento monotono e invia syscall al thread worker |
| `_tick()` | Loop principale (500ms): drena coda, aggiorna display, offset, history, chart |
| `_restore_clock()` | Ripristina l'ora OS dallo snapshot monotono — nessuna rete, nessun subprocess |

#### Costanti Linux

| Costante | Valore | Uso |
|---|---|---|
| `_NTP_UNITS` | 7 unit | Demoni e socket gestiti da `ntp_disable` / `ntp_enable` |
| `_CLOCK_REALTIME` | 0 | Clock ID per `clock_settime` |
| `_STA_UNSYNC` | 0x0040 | Segnala al kernel che il clock non è sincronizzato, blocca il PLL |
| `_ADJ_OFFSET/FREQUENCY/STATUS` | 0x0001/0x0002/0x0010 | Azzera offset, frequenza e stato PLL via `adjtimex` |

#### Comandi di sistema per OS

| OS | Operazione | Metodo |
|---|---|---|
| Linux | Imposta ora | `clock_settime(CLOCK_REALTIME)` via libc ctypes (nanosec) |
| Linux | Blocca deriva | `adjtimex(2)` reset PLL — struct Timex 208 byte |
| Linux | NTP disable | `timedatectl set-ntp false` + `systemctl stop/disable/mask` + reset PLL |
| Linux | NTP enable | `systemctl unmask` + `timedatectl set-ntp true` |
| Linux | Timezone | `timedatectl set-timezone` |
| macOS | Imposta ora | `date <MMDDHHmmYYYY.SS>` (sudo) |
| macOS | NTP | `systemsetup -setusingnetworktime on/off` |
| macOS | Timezone | `systemsetup -settimezone` |
| Windows | Imposta ora | `SetLocalTime()` WinAPI via ctypes (millisec) |
| Windows | NTP | `net start/stop w32time`, `w32tm /resync`, `sc config` |
| Windows | Timezone | `tzutil /s` |

---

### Funzionalità

L'applicazione include un orologio live aggiornato ogni 500ms calcolato da riferimento monotono (immune a derive OS), la correzione FT8/FT4 DT con barra di tolleranza visiva (verde < 0.5s, arancione < 1s, rosso ≥ 1s), e pulsanti quick DT per correzioni rapide di ±0.1s, ±0.5s, ±1s, ±2s. È disponibile l'impostazione manuale dell'ora esatta nel formato `YYYY-MM-DD / HH:MM:SS` con tasto **NOW** per la precompilazione automatica.

La gestione NTP comprende enable, disable con mascheratura demoni e indicatore di stato in tempo reale. La funzione restore clock from snapshot ripristina l'ora dal snapshot salvato al momento del disable NTP tramite contatore monotono, senza rete. Il pannello timezone offre un menu a tendina con tutti i fusi orari disponibili. Il grafico storico offset mostra la sparkline degli ultimi 2 minuti thread-safe, con log operazioni timestampato a colori. L'applicazione è compatibile con Linux, macOS e Windows, ciascuno con le proprie API native.

---

### Istruzioni d'uso

#### Installazione

##### Linux

```bash
python3 --version
python3 -c "import tkinter; print('tkinter OK')"
# se tkinter manca:
sudo apt install python3-tk        # Debian/Ubuntu
sudo dnf install python3-tkinter   # Fedora
sudo pacman -S tk                  # Arch

sudo python3 sysclock_gui.py
sudo python3 sysclock_gui_clear.py
```

##### macOS

```bash
brew install python3
python3 -c "import tkinter; print('tkinter OK')"
brew install python-tk   # se manca

sudo python3 sysclock_gui.py
sudo python3 sysclock_gui_clear.py
```

##### Windows

Installare Python 3.8+ da [python.org](https://www.python.org/downloads/windows/) con "Add Python to PATH" selezionato. Avviare da Prompt come Amministratore:

```cmd
cd C:\percorso\cartella
python sysclock_gui.py
python sysclock_gui_clear.py
```

##### Linux — Eseguibili standalone

Sono disponibili due versioni precompilate per Linux che non richiedono l'installazione di Python. I file eseguibili si trovano nella cartella `dist`:

```
dist/sysclock_gui        ← versione Dark
dist/sysclock_gui_clear  ← versione Clear
```

Per prima cosa rendili eseguibili, poi avviali con i privilegi di root:

```bash
chmod +x dist/sysclock_gui dist/sysclock_gui_clear
sudo dist/sysclock_gui
# oppure
sudo dist/sysclock_gui_clear
```

Per rigenerare gli eseguibili (maintainer release):

```bash
pip install pyinstaller
pyinstaller -F -w --name sysclock_gui sysclock_gui.py
pyinstaller -F -w --name sysclock_gui_clear sysclock_gui_clear.py
```

> Importante: avviare sempre con `sudo`, in quanto le operazioni di sistema richiedono privilegi di root.

##### Windows 11 — Eseguibile standalone

È disponibile una versione precompilata compatibile con Windows 11, che non richiede l'installazione di Python. Il file eseguibile si trova nella cartella `dist`:

```
dist\SysClockControl.exe
dist\SysClockControl_clear.exe
```

Per rigenerare l'eseguibile (maintainer release):

```cmd
python -m PyInstaller -F -w --name SysClockControl sysclock_gui.py
python -m PyInstaller -F -w --name SysClockControl_clear sysclock_gui_clear.py
```

> Importante: avviare `SysClockControl.exe` con click destro → Esegui come amministratore, in quanto le operazioni di sistema richiedono privilegi elevati.

#### Riepilogo avvio

| Sistema | Comando |
|---|---|
| Linux | `sudo python3 sysclock_gui.py` |
| Linux (standalone dark) | `sudo dist/sysclock_gui` |
| Linux (standalone clear) | `sudo dist/sysclock_gui_clear` |
| macOS | `sudo python3 sysclock_gui.py` |
| Windows | Prompt come Amministratore → `python sysclock_gui.py` |
| Windows 11 (standalone) | `dist\SysClockControl.exe` — click destro → Esegui come amministratore |

---

#### Pannello FT8 / FT4 — DT Correction

Leggere il valore DT da WSJT-X, JTDX o MSHV (es. `+0.8` o `-1.2`). Inserirlo nel campo DT value (s) e premere **APPLY DT** — la correzione viene applicata con segno invertito. Usare i pulsanti quick (±0.1s … ±2s) per correzioni istantanee. La barra di tolleranza indica: verde |DT| < 0.5s, arancione < 1s, rosso ≥ 1s.

![Pannello operativo SYSCLOCK](images/2.png)

#### Pannello SET EXACT TIME

Inserire la data nel formato `YYYY-MM-DD` e l'ora nel formato `HH:MM:SS`. Il tasto **NOW** precompila con l'ora corrente del sistema. **SET** applica al sistema.

#### Pannello NTP

L'indicatore colorato mostra verde quando NTP è attivo, rosso quando è inattivo. **ENABLE NTP** esegue unmask e riabilita la sincronizzazione automatica. **DISABLE NTP** disabilita completamente: ferma, disabilita e maschera tutti i demoni noti (incluso `systemd-timesyncd.socket`) con reset PLL kernel Linux. **RESTORE CLOCK FROM SNAPSHOT** ripristina l'ora OS dal snapshot salvato al momento del disable NTP, usando il contatore monotono senza rete.

#### Pannello TIMEZONE

Selezionare il fuso orario e premere **APPLY**.

#### Grafico OFFSET HISTORY

Trend dell'offset cumulativo aggiornato ogni 500ms. Min/max mostrati sotto il grafico. La linea tratteggiata indica lo zero.

---

### Note e avvertenze

Su Linux viene usato `clock_settime` via libc (nanosecondo) con `adjtimex` reset PLL dopo ogni correzione. Il comando disable NTP maschera anche `systemd-timesyncd.socket` per impedire il riavvio automatico via socket activation. Su macOS il reset del PLL del kernel non è applicabile. Su Windows viene usato `SetLocalTime()` via WinAPI (millisecondo) e l'applicazione richiede il Prompt come Amministratore. L'offset counter è locale all'applicazione e si azzera alla chiusura. Le funzioni Linux (`clock_settime`, `adjtimex`) non vengono mai chiamate su macOS o Windows.

---

### Licenza

```
SYSCLOCK — System Time Control
Copyright (C) 2026  Alessandro Orlando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

---

## English

### Description

SYSCLOCK — System Time Control is a desktop GUI application written entirely in Python 3 using the standard tkinter library, with no external dependencies.

Designed specifically for amateur radio operators working with weak-signal digital modes (FT8, FT4, JT65, JT9 and similar), where system clock accuracy is critical. It allows quick clock correction directly from the DT value reported by WSJT-X, JTDX or MSHV, and manages NTP, timezone and exact time in a single interface.

---

### Why Ham Radio Operators Need It

Weak-signal modes like FT8 and FT4 rely on fixed 15-second time slots synchronized to UTC. A clock drift of just 1–2 seconds causes decoding failures and makes transmission impossible. The DT (Delta Time) value shown by WSJT-X, JTDX and MSHV indicates exactly this offset.

SYSCLOCK allows you to correct the PC clock in one click by entering the DT value, operate without internet (portable ops, contests, SOTA, POTA), fully disable NTP to prevent the sync daemon from reintroducing drift, set time manually from a GPS or atomic clock reference, and visually monitor accumulated drift via the history chart.

| Situation | How to use SYSCLOCK |
|---|---|
| DT in WSJT-X is ±0.5s or more | Enter DT value in the FT8 panel and press **APPLY DT** |
| Portable operation without internet | Disable NTP, set exact time from GPS with **SET EXACT TIME** |
| Progressive drift during a contest | Monitor history chart and apply DT corrections on the fly |
| NTP unavailable or unreliable | Disable NTP and use **RESTORE CLOCK FROM SNAPSHOT** |
| Timezone change while travelling | Update the OS with the **TIMEZONE** panel in one click |

> Compatible with WSJT-X · JTDX · MSHV

---

### Technical Description

| Item | Detail |
|---|---|
| Language | Python 3.8+ |
| GUI toolkit | tkinter (stdlib) + ttk |
| External dependencies | None |
| Operating systems | Linux, macOS, Windows |
| Required privileges | root / administrator for system operations |
| Architecture | Single-file, multi-thread with thread-safe queue (queue.Queue) |
| License | GNU GPL v3.0 |

#### Functions currently in use

| Function | Description |
|---|---|
| `_linux_set_clock(dt)` | Sets `CLOCK_REALTIME` via `clock_settime()` (libc, ns) + PLL reset via `adjtimex(2)` |
| `set_system_time(dt)` | Multi-OS wrapper: libc on Linux, `date` on macOS, `SetLocalTime` WinAPI on Windows |
| `ntp_enable()` | Unmasks and re-enables all known NTP daemons via `timedatectl` and `systemctl` |
| `ntp_disable()` | Stops, disables and masks all NTP daemons (including activation socket) + kernel PLL reset |
| `ntp_status()` | Checks if NTP is active (`timedatectl` + `systemctl is-active` for each known daemon) |
| `get_timezones()` | Retrieves available timezone list (timedatectl / zoneinfo / tzutil) |
| `set_timezone(tz)` | Sets system timezone (`timedatectl` / `systemsetup` / `tzutil`) |
| `RingBuffer` | Thread-safe circular buffer for offset history (120 samples, ~2 min) |
| `SysClockApp` | Main application class (tkinter.Tk), producer/consumer architecture |
| `_do_step(ms)` | Computes target from monotonic reference, sends syscall to worker thread |
| `_tick()` | Main loop (500ms): drains queue, updates display, offset, history, chart |
| `_restore_clock()` | Restores OS time from monotonic snapshot — no network, no subprocess |

#### System commands per OS

| OS | Operation | Method |
|---|---|---|
| Linux | Set time | `clock_settime(CLOCK_REALTIME)` via libc ctypes (nanosec) |
| Linux | Stop drift | `adjtimex(2)` PLL reset — complete Timex struct 208 bytes |
| Linux | NTP disable | `timedatectl set-ntp false` + `systemctl stop/disable/mask` + PLL reset |
| Linux | NTP enable | `systemctl unmask` + `timedatectl set-ntp true` |
| Linux | Timezone | `timedatectl set-timezone` |
| macOS | Set time | `date <MMDDHHmmYYYY.SS>` (sudo) |
| macOS | NTP | `systemsetup -setusingnetworktime on/off` |
| macOS | Timezone | `systemsetup -settimezone` |
| Windows | Set time | `SetLocalTime()` WinAPI via ctypes (millisec) |
| Windows | NTP | `net start/stop w32time`, `w32tm /resync`, `sc config` |
| Windows | Timezone | `tzutil /s` |

---

### Features

The application includes a live clock updated every 500ms computed from a monotonic reference (immune to OS drift), FT8/FT4 DT correction with a visual tolerance bar (green < 0.5s, orange < 1s, red ≥ 1s), and quick DT buttons for instant corrections of ±0.1s, ±0.5s, ±1s, ±2s. Manual exact time entry is available in `YYYY-MM-DD / HH:MM:SS` format with a **NOW** button for automatic pre-fill.

NTP management covers enable, disable with daemon masking, and a real-time status indicator. The restore clock from snapshot function restores the OS clock from the snapshot saved at disable NTP time using the monotonic counter, with no network required. The timezone panel provides a dropdown of all available timezones applied immediately. The offset history chart shows a thread-safe sparkline of the last 2 minutes with a timestamped, color-coded operations log. The application is compatible with Linux, macOS and Windows, each using its own native APIs.

---

### Usage Instructions

#### Installation

##### Linux

```bash
python3 -c "import tkinter; print('OK')"
sudo apt install python3-tk      # Debian/Ubuntu
sudo dnf install python3-tkinter # Fedora
sudo pacman -S tk                # Arch

sudo python3 sysclock_gui.py
sudo python3 sysclock_gui_clear.py
```

##### macOS

```bash
brew install python3
brew install python-tk   # if tkinter missing
sudo python3 sysclock_gui.py
sudo python3 sysclock_gui_clear.py
```

##### Windows

Install Python 3.8+ from [python.org](https://www.python.org/downloads/windows/) with "Add Python to PATH". Launch from an Administrator Command Prompt:

```cmd
cd C:\path\to\folder
python sysclock_gui.py
python sysclock_gui_clear.py
```

##### Linux — Standalone Executables

Two pre-built versions for Linux are available, requiring no Python installation. The executables are located in the `dist` folder:

```
dist/sysclock_gui        ← Dark version
dist/sysclock_gui_clear  ← Clear version
```

Make them executable first, then launch with root privileges:

```bash
chmod +x dist/sysclock_gui dist/sysclock_gui_clear
sudo dist/sysclock_gui
# or
sudo dist/sysclock_gui_clear
```

To rebuild the executables (maintainer release):

```bash
pip install pyinstaller
pyinstaller -F -w --name sysclock_gui sysclock_gui.py
pyinstaller -F -w --name sysclock_gui_clear sysclock_gui_clear.py
```

> Important: always launch with `sudo`, as system-level operations require root privileges.

##### Windows 11 — Standalone Executable

A pre-built version compatible with Windows 11 is available, requiring no Python installation. The executable is located in the `dist` folder:

```
dist\SysClockControl.exe
```

> Important: launch `SysClockControl.exe` by right-clicking → Run as administrator, as system-level operations require elevated privileges.

#### Quick Launch Reference

| System | Command |
|---|---|
| Linux | `sudo python3 sysclock_gui.py` |
| Linux (standalone dark) | `sudo dist/sysclock_gui` |
| Linux (standalone clear) | `sudo dist/sysclock_gui_clear` |
| macOS | `sudo python3 sysclock_gui.py` |
| Windows | Administrator Command Prompt → `python sysclock_gui.py` |
| Windows 11 (standalone) | `dist\SysClockControl.exe` — right-click → Run as administrator |

---

#### FT8 / FT4 — DT Correction Panel

Read the DT value from WSJT-X, JTDX or MSHV (e.g. `+0.8` or `-1.2`). Enter it in the DT value (s) field and press **APPLY DT** — correction is applied with inverted sign. Use the quick buttons (±0.1s … ±2s) for instant corrections. The tolerance bar shows: green |DT| < 0.5s, orange < 1s, red ≥ 1s.

![SYSCLOCK operational panel](images/2.png)

#### SET EXACT TIME Panel

Enter the date in `YYYY-MM-DD` format and time in `HH:MM:SS` format. **NOW** pre-fills the current system time. **SET** applies to the system.

#### NTP Panel

The colored indicator shows green when NTP is active, red when inactive. **ENABLE NTP** unmasks and re-enables automatic sync. **DISABLE NTP** performs a full disable: stops, disables and masks all known daemons (including `systemd-timesyncd.socket`) with Linux kernel PLL reset. **RESTORE CLOCK FROM SNAPSHOT** restores the OS clock from the snapshot saved at disable NTP time, using the monotonic counter with no network required.

#### TIMEZONE Panel

Select timezone from the dropdown and press **APPLY**.

#### OFFSET HISTORY Chart

Cumulative offset trend updated every 500ms. Min/max shown below the chart. The dashed line marks zero.

---

### Notes and Warnings

On Linux, `clock_settime` via libc (nanosecond) is used with `adjtimex` PLL reset after every correction. Disable NTP also masks `systemd-timesyncd.socket` to prevent automatic restart via socket activation. On macOS, kernel PLL reset is not applicable. On Windows, `SetLocalTime()` via WinAPI (millisecond) is used and the application must be launched from an Administrator Command Prompt. The offset counter is local to the application and resets on close. Linux-specific functions (`clock_settime`, `adjtimex`) are never called on macOS or Windows.

---

### License

```
SYSCLOCK — System Time Control
Copyright (C) 2026  Alessandro Orlando

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```
