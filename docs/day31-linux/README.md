# OpsPulse — Complete DevOps Winter Arc Integration Project

> **End-to-end lab handbook, command reference, source-code walkthrough, troubleshooting journal, validation checklist, and interview guide**  
> Lab documented: **17 November 2026**  
> Working machine: **Debian (`debian2`)**, accessed from **Windows using PuTTY**  
> Linux user: **`bitra`**  
> Project path: **`/home/bitra/winter-arc-integration-project`**  
> GitHub: **[manasabitra1989/winter-arc-integration-project](https://github.com/manasabitra1989/winter-arc-integration-project)**

## Read this first: what is verified versus reconstructed

This README consolidates **the full sequence documented in our conversation**, including the commands supplied, the command results you shared, failures, fixes, and subsequent improvements. It is a learning record, **not a direct inspection of every file currently on your Debian machine**. Some full file contents (for example, your final `app/app.py` and `~/.bashrc`) were not pasted back into the chat; where necessary, the README gives the **lab version we created together** rather than claiming to reproduce unseen local edits. The last GitHub Actions workflow was provided for creation; **a successful GitHub Actions run was not shown**. An SSH test/push was described as apparently good, but its output was not shared. Do not mark those as independently verified until you check.

**Quick state at the end of our lab:** OpsPulse **v2** responded successfully on `/` after rollback; systemd was the intended sole process manager; a failed deployment produced HTTP `000` ten times and **the revised rollback routine subsequently reported success**. The Git repository was connected to the GitHub URL above, and SSH-key setup was performed. The CI workflow is the **next stage to verify**.

---

## 1. Project purpose and learning outcomes

**OpsPulse** is a lightweight Flask monitoring API used to combine skills learned in the DevOps Winter Arc challenge:

1. Linux navigation, file management, permissions, processes, ports, and troubleshooting.
2. Python virtual environments, package management, a Flask HTTP API, and JSON responses.
3. Shell scripting: shebang, variables, command substitution, conditions, loops, exit codes, output redirection, and log files.
4. Cron scheduling for periodic health checks.
5. systemd service lifecycle, journals, auto-restart, and ownership of port 8080.
6. logrotate for retention and compression of monitoring logs.
7. CPU, memory, disk, and API health reporting.
8. Application versioning, manual deployment, automated deployment, backups, rollback, and deliberately broken releases.
9. Git hygiene, `.gitignore`, staging, commit, push, GitHub HTTPS authentication, and SSH keys.
10. GitHub Actions continuous integration (CI): Python/Bash syntax and file existence checks.

**Analogy:** OpsPulse is a small shop. Flask is the shop counter; systemd hires and supervises the worker; `/health` tells us whether the counter responds; cron calls the shop periodically; logrotate clears old notebooks; the deployment script changes the shop's instructions; the backup lets us restore yesterday's instructions; Git preserves the instruction history; GitHub Actions checks new instructions before they are accepted.

### System architecture

```text
Windows workstation / PuTTY SSH
                |
                v
          Debian 2 server
                |
          systemd: opspulse
                |
       Python virtual environment
                |
     Flask app/app.py — TCP 8080
          |                |
        GET /          GET /health
          |                |
     JSON version     JSON healthy
                ^
                |
     cron -> health-check.sh -> logs/health-check.log
                |
     server-health.sh -> logs/server-health.log

    releases/app-v2.py -> deploy.sh -> backup -> restart
                                           |
                                    GET /health
                                      /      \
                                    200     failure
                                     |        |
                                  retain   rollback

     Git local -> GitHub -> GitHub Actions CI checks
```

> This architecture is a **local Debian lab**. It does not yet contain Kubernetes, Docker, a production web server, an external database, or automatic GitHub-to-Debian deployment.

### Local URLs and important status codes

| Item | Example | Meaning |
|---|---|---|
| Flask bind address | `0.0.0.0:8080` | Listen on all IPv4 interfaces; **not** a browser destination |
| Linux self-check | `http://127.0.0.1:8080/health` | Test on the Debian host |
| Browser access | `http://172.27.58.184:8080/` | IP shown in one lab screenshot; can change |
| `HTTP 200` | Healthy response | HTTP request succeeded |
| `HTTP 404` | Unknown endpoint | Web server responded, but route not found |
| `HTTP 000` in curl `-w` | No HTTP status received | Connection refused, timed out, or another transport problem; **not a real HTTP status** |
| Shell exit `0` | Success | Script/command succeeded |
| Shell exit `1` | Failure | Application/script-defined error, or generic failure |
| Shell exit `3` | Seen with `systemctl is-active` | Service not active (systemctl's status code) |
| Shell exit `127` | Command not found | Shell could not find the executable |

---

## 2. Files and directories

Our project structure, separating version-controlled source from generated artifacts:

```text
winter-arc-integration-project/
├── .git/
├── .gitignore
├── .github/
│   └── workflows/
│       └── opspulse-ci.yml         # CI proposed/created during Step 19
├── app/
│   ├── app.py                      # currently deployed Flask source
│   ├── .venv/                      # local Python virtual environment; IGNORE
│   └── logs/
│       └── flask.log               # if manually redirected here; IGNORE
├── scripts/
│   ├── health-check.sh
│   ├── server-health.sh
│   ├── deploy.sh
│   └── deploy.sh.old               # local backup; IGNORE
├── releases/
│   ├── app-v2.py                   # candidate release
│   ├── app-v2-working.py           # local safety copy; IGNORE
│   └── app-v2.py.before-test       # temporary rollback-test copy; IGNORE
├── backups/                        # generated snapshots; IGNORE
└── logs/
    ├── health-check.log           # cron/script output; IGNORE
    └── server-health.log          # health report; IGNORE
```

**Why two log locations?** During the lab we ran Flask manually with stdout redirected to `app/logs/flask.log`, while the health-monitoring scripts wrote to the **project-level** `logs/`. Once systemd became the process manager, `journalctl -u opspulse` became the main place to see Flask's console logs. Do not mix up `app/logs/` and `logs/`.

---

## 3. Windows PuTTY terminal: clear screenshots and command highlighting

This was part of the actual lab because distinguishing the prompt, typed commands, and output improved screenshot readability.

### 3.1 PuTTY visual settings

From a saved PuTTY SSH session: **Load** session -> **Window > Colours**. Suggested RGB settings:

| PuTTY palette entry | RGB | Goal |
|---|---|---|
| Default Background | `16,24,32` | Dark charcoal |
| Default Foreground | `220,235,240` | Readable output |
| ANSI Cyan Bold | `0,229,255` | Bright prompt |
| ANSI Yellow Bold | `255,204,51` | Commands |
| ANSI Green Bold | `185,246,165` | Positive status |

Use **Window > Appearance**, font **Consolas**, about **13–14 pt**, and increase scrollback to around **10,000** lines if useful. Return to **Session > Save** to persist the PuTTY changes.

**Important limit:** PuTTY assigns colors, but **PuTTY alone cannot tell typed shell commands apart from program output**. Bash prompt settings and a line editor add that distinction.

### 3.2 Back up `.bashrc` and create cyan PS1

```bash
cp ~/.bashrc ~/.bashrc.backup
nano ~/.bashrc
```

Append (or keep one appropriate copy of):

```bash
export PS1='\[\e[1;96m\]\u@\h:\w\$\[\e[0m\] '
```

Then:

```bash
source ~/.bashrc
```

Explanation: `PS1` is the primary shell prompt; `\u` username; `\h` hostname; `\w` current directory; `\$` `$` for regular users or `#` for root; `\e[1;96m` bold bright cyan; `\e[0m` reset color; `\[` and `\]` mark non-printing ANSI codes so cursor movement works; **the final space** keeps the command from touching the `$`.

Your Python environment may prepend `(.venv)` to this prompt while active.

### 3.3 Install ble.sh for Bash command highlighting

```bash
sudo apt update
sudo apt install -y git make gawk
cd ~
git clone --recursive --depth 1 --shallow-submodules https://github.com/akinomyoga/ble.sh.git
make -C ble.sh install PREFIX="$HOME/.local"
source "$HOME/.local/share/blesh/ble.sh"
```

Enable for interactive Bash sessions (avoid adding the same line repeatedly):

```bash
echo '[[ $- != *i* ]] || source "$HOME/.local/share/blesh/ble.sh"' >> ~/.bashrc
```

Configure command highlighting in `~/.blerc`:

```bash
ble-face -s command_builtin 'fg=yellow,bold'
ble-face -s command_file 'fg=yellow,bold'
ble-face -s command_alias 'fg=yellow,bold'
ble-face -s command_function 'fg=yellow,bold'
ble-face -s argument_option 'fg=green'
```

Open a new PuTTY session or reload ble.sh configuration (where available). Type `python -m pip show Flask` **without pressing Enter** to inspect live highlighting. The **command name** may turn yellow while options and arguments have separate colors. Do **not** expect all existing program output to become green.

### 3.4 Problems we encountered and fixed

**Warning:** `ble.sh: suspicious environment: $LANG is empty`.

Inspect:

```bash
locale
locale -a
```

We saw `C.utf8` and `en_US.utf8`; `LANG=C.UTF-8` was confirmed working. Immediate fix:

```bash
export LANG=C.UTF-8
```

Persistent shell-login setting used in the lab:

```bash
echo 'export LANG=C.UTF-8' >> ~/.bash_profile
```

Avoid duplicating this line; reload appropriately or reconnect. The mistake `locale -` returned `locale: unknown name "-"`; the intended available-locales command was **`locale -a`**.

**ble.sh multiline message** when pasting a shell command split by a trailing `\`:

```text
-- MULTILINE -- (RET or C-m: insert a newline, C-j: run)
```

This is **not a Flask or curl error**. `\` at end of line means the command continues; ble.sh uses Enter to insert newline and **Ctrl+J** to execute the multiline buffer. Use **Ctrl+C** to cancel, or use a single-line command such as:

```bash
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" --max-time 5 http://localhost:8080/health
```

---

## 4. Python and Flask setup

### 4.1 Project and virtual environment

The project was under:

```bash
cd ~/winter-arc-integration-project
mkdir -p app scripts releases backups logs
```

In this lab, the virtual environment path used by systemd and scripts was **`app/.venv`**:

```bash
cd ~/winter-arc-integration-project/app
python3 -m venv .venv
source .venv/bin/activate
which python
which pip
python --version
pip --version
```

> If your existing virtual environment is working, **do not recreate it**. These are reference/setup commands. The screenshot confirmed a virtual environment under `app/.venv`, and Python `3.13.5` was shown during installation.

Install Flask:

```bash
python -m pip install Flask
python -m pip show Flask
```

Our output showed **Flask 3.1.3**. `python -m pip` uses pip tied to the active Python interpreter, reducing confusion between system Python and `.venv` Python.

**Python basics:** a *virtual environment* isolates project packages; `pip` installs Python packages; Flask handles HTTP requests; `jsonify` serializes Python dictionaries into JSON responses.

### 4.2 Flask application — lab source

We first created a simple API, then changed the `/` endpoint for **v2**. The full example below represents the application **we designed together**; check your current `app/app.py` for differences before overwriting anything.

**`app/app.py`** (reference version):

```python
from flask import Flask, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "application": "OpsPulse",
        "version": "v2",
        "message": "Welcome to OpsPulse Version 2",
        "status": "running"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "application": "OpsPulse",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

The **actual confirmed v2 home response** was:

```json
{"application":"OpsPulse","message":"Welcome to OpsPulse Version 2","status":"running","version":"v2"}
```

#### Python breakdown — every important line

| Code | Plain-English explanation |
|---|---|
| `from flask import Flask, jsonify` | Import Flask app class and JSON response helper |
| `from datetime import datetime, timezone` | Import clock/date tools and UTC timezone |
| `app = Flask(__name__)` | Create the web application object |
| `@app.route("/")` | Register a URL path for the function below it |
| `def home():` | Declare a function called `home`; indentation marks its body |
| `return jsonify({...})` | Build a dictionary and send it as JSON over HTTP |
| `"application": "OpsPulse"` | A dictionary *key-value* pair |
| `"version": "v2"` | Identify the application release |
| `@app.route("/health")` | Register a health-check endpoint |
| `datetime.now(timezone.utc)` | Get a UTC-aware timestamp |
| `.isoformat()` | Convert timestamp into a standard ISO 8601 string |
| `if __name__ == "__main__":` | Only start server automatically when executed as the main program |
| `app.run(host="0.0.0.0", port=8080)` | Start Flask development server on port 8080 |

**Security and architecture note:** The built-in Flask server is for **development/labs**, not production. In production, use a WSGI server (e.g., Gunicorn), appropriate ingress/reverse proxy, TLS, authentication as needed, and a separate robust dependency-readiness strategy.

### 4.3 Initial manual start and API tests

With `.venv` active:

```bash
cd ~/winter-arc-integration-project/app
python app.py
```

Keep that PuTTY session open; in another session:

```bash
curl -i http://localhost:8080/
curl -i http://localhost:8080/health
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/health
```

`-i` shows HTTP headers; `-s` suppresses progress output; `-o /dev/null` discards response body; `-w` prints selected data; `%{http_code}` is curl's response-code field.

**Observed:** `/health` returned **`HTTP Status: 200`**; the browser also displayed the `/` JSON result using the Debian host's network IP.

---

## 5. Linux process and port inspection

### 5.1 Commands and observed output

```bash
ps -ef | grep '[p]ython app.py'
sudo ss -lntp | grep ':8080'
ps -C python -o pid,ppid,%cpu,%mem,rss,cmd
```

We observed:

```text
bitra 3229 2641 ... python app.py
LISTEN ... 0.0.0.0:8080 ... users:(("python",pid=3229,fd=3))
PID   PPID %CPU %MEM   RSS CMD
3229  2641  0.1  0.8 32516 python app.py
```

**Interpretation:** `PID=3229` identified that instance; `PPID=2641` was its parent; `CPU=0.1%`; memory `0.8%`; RSS `32516 KiB` (~31.8 MiB); `fd=3` was the socket's file descriptor. PIDs change every time a process starts, **so don't hard-code old PIDs**.

### 5.2 Command cheat sheet

| Command | What it answers |
|---|---|
| `ps -ef` | What processes are running? |
| `grep '[p]ython app.py'` | Find specific process without matching the `grep` process itself |
| `pgrep -af 'python.*app.py'` | Show matching PIDs plus command lines |
| `ps -fp PID` | Who started this particular process? |
| `sudo ss -lntp` | Which program listens on which TCP port? |
| `ps -C python -o ...` | How much CPU/memory does Python consume? |
| `kill PID` | Send a normal termination signal (SIGTERM) to that PID |
| `systemctl status opspulse` | What does the service manager think is running? |
| `curl .../health` | Is the HTTP app actually responsive? |

**Troubleshooting insight:** `ps -ef | grep -i 8080` did not find the Flask process, because its **command line contained `python app.py`**, not the port number. `ss -lntp` did show the owner of port 8080.

---

## 6. Logging and testing an invalid route

### 6.1 Manual log capture

Stop a foreground Flask server with **Ctrl+C** and start it with redirected output:

```bash
cd ~/winter-arc-integration-project/app
mkdir -p logs
python -u app.py > logs/flask.log 2>&1 &
```

`-u`: unbuffered Python output; `>`: send stdout into file; `2>&1`: merge stderr into stdout; `&`: launch in background; `tail -f` streams log updates.

```bash
tail -f logs/flask.log
```

In a second terminal:

```bash
curl http://localhost:8080/health
curl -i http://localhost:8080/invalid
```

Expected: `/invalid` returns **HTTP 404**, and Flask logs a line similar to `"GET /invalid HTTP/1.1" 404 -`.

**Critical later learning:** After configuring systemd, **do not also start a manual `python app.py`** on 8080. That caused our actual production-style port conflict.

---

## 7. Bash health-check script

### 7.1 Create it

```bash
cd ~/winter-arc-integration-project
mkdir -p scripts logs
nano scripts/health-check.sh
chmod +x scripts/health-check.sh
```

**`scripts/health-check.sh` — lab implementation:**

```bash
#!/usr/bin/env bash
set -u

APP_URL="http://localhost:8080/health"
PROJECT_DIR="$HOME/winter-arc-integration-project"
LOG_FILE="$PROJECT_DIR/logs/health-check.log"

mkdir -p "$(dirname "$LOG_FILE")"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

HTTP_CODE=$(curl -s -o /dev/null \
    -w "%{http_code}" \
    --connect-timeout 3 \
    --max-time 5 \
    "$APP_URL")

if [[ "$HTTP_CODE" == "200" ]]; then
    MESSAGE="[$TIMESTAMP] SUCCESS: OpsPulse is HEALTHY (HTTP $HTTP_CODE)"
    echo "$MESSAGE" | tee -a "$LOG_FILE"
    exit 0
else
    MESSAGE="[$TIMESTAMP] ERROR: OpsPulse is UNHEALTHY (HTTP $HTTP_CODE)"
    echo "$MESSAGE" | tee -a "$LOG_FILE"
    exit 1
fi
```

### 7.2 Explain the Bash line by line

| Bash element | Beginner explanation |
|---|---|
| `#!/usr/bin/env bash` | Shebang: run script with Bash when executing `./script.sh` |
| `set -u` | Error if an unset variable is referenced |
| `NAME="value"` | Define variable; **no spaces around `=`** |
| `$HOME` | Your home directory, `/home/bitra` |
| `$(...)` | Run a command and capture its output |
| `dirname "$LOG_FILE"` | Get directory part of the path |
| `mkdir -p` | Create directory if absent; don't error if it already exists |
| `date '+%Y-%m-%d %H:%M:%S'` | Format a timestamp |
| `curl --connect-timeout 3 --max-time 5` | Limit how long a dead endpoint blocks the script |
| `[[ "$HTTP_CODE" == "200" ]]` | Bash conditional comparison |
| `if ...; then ... else ... fi` | Branch based on a condition |
| `echo "$MESSAGE" \| tee -a "$LOG_FILE"` | Print to screen and append to log file |
| `exit 0` / `exit 1` | Tell other programs whether the check succeeded |

To execute:

```bash
./scripts/health-check.sh
# or explicitly:
bash scripts/health-check.sh
```

### 7.3 Real error encountered: `sh` versus `bash`

You ran:

```bash
sh health-check.sh
```

Output:

```text
health-check.sh: 19: [[: not found
ERROR: OpsPulse is UNHEALTHY (HTTP 200)
[ble: exit 1]
```

**Root cause:** Debian's `/bin/sh` is commonly **dash**. `[[ ... ]]` is Bash syntax, not portable POSIX `sh` syntax. The app was healthy, but the **condition failed**, sending the script into the wrong branch.

**Fix:**

```bash
bash health-check.sh
# or
chmod +x health-check.sh
./health-check.sh
```

`sh script.sh` **overrides the shebang**. If portability to POSIX `sh` is needed, rewrite comparisons using `[ "$HTTP_CODE" = "200" ]` and eliminate Bash-specific features.

### 7.4 Failure behavior

When Flask was intentionally stopped, curl printed **`HTTP Status: 000`**. A scripted check should record `ERROR ... (HTTP 000)` and return exit code `1`.

**Caution:** A health endpoint confirms the app responded, not that every business function or database dependency is healthy. Our script checks **only the HTTP response code**, not JSON content, latency SLOs, or application version.

---

## 8. Cron — run the health script every minute

### 8.1 Install/check scheduler

```bash
systemctl status cron --no-pager
# if missing:
sudo apt update
sudo apt install -y cron
sudo systemctl enable --now cron
```

### 8.2 Configure user's crontab

```bash
crontab -e
```

We saw **`no crontab for bitra - using an empty one`** and the editor chooser; chose `1` (**nano**). Added:

```cron
* * * * * /bin/bash /home/bitra/winter-arc-integration-project/scripts/health-check.sh
```

The five fields represent **minute, hour, day of month, month, day of week**. Five asterisks = every minute.

Verify:

```bash
crontab -l
tail -n 5 ~/winter-arc-integration-project/logs/health-check.log
sudo journalctl -u cron -n 20 --no-pager
```

**Observed:** log entries at minute intervals including a success around **02:01:01** (Debian server time). The server printed UTC timestamps while the local user was in India; always label timezone when correlating incident logs.

To disable when done with the lab:

```bash
crontab -e
# comment the line with # at the beginning
```

**Cron caveat:** Cron executes with a reduced environment and doesn't automatically load your interactive `.bashrc` or Python `.venv`. The script uses absolute paths and system `curl`; that is why it works reliably from cron. This cron task **detects** outages; it does **not restart** Flask.

---

## 9. Application failure simulation and recovery

1. Find the Flask process:
   ```bash
   pgrep -af 'python.*app.py'
   ```
2. If manually started, stop it with Ctrl+C or `kill <actual-PID>` after inspecting it.
3. Check its API:
   ```bash
   curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" --max-time 5 http://localhost:8080/health
   ```
4. **Observed:** `HTTP Status: 000` when it was down.
5. Inspect the cron log for `ERROR` on the next run:
   ```bash
   tail -n 5 ~/winter-arc-integration-project/logs/health-check.log
   ```
6. Initially, manual recovery used:
   ```bash
   cd ~/winter-arc-integration-project/app
   source .venv/bin/activate
   python -u app.py > logs/flask.log 2>&1 &
   ```
7. Once systemd is configured, **recover using `sudo systemctl start opspulse`**, not by starting a second process manually.

**Monitoring lifecycle:** `healthy (200)` -> `stopped (000)` -> `restarted (200)`.

---

## 10. systemd — manage Flask as a service

### 10.1 Stop any manually started application first

```bash
pgrep -af 'python.*app.py'
sudo ss -lntp | grep ':8080'
```

Check the owner of port 8080 and stop **only** the confirmed, manually managed OpsPulse process. Never blindly kill all `python` processes.

### 10.2 Create the service

```bash
sudo nano /etc/systemd/system/opspulse.service
```

```ini
[Unit]
Description=OpsPulse Flask Monitoring Application
After=network.target

[Service]
Type=simple
User=bitra
WorkingDirectory=/home/bitra/winter-arc-integration-project/app
ExecStart=/home/bitra/winter-arc-integration-project/app/.venv/bin/python -u app.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### systemd breakdown

| Directive | Meaning |
|---|---|
| `[Unit]` | Metadata and start ordering |
| `After=network.target` | Start after network target is reached; **not** a guarantee all network dependencies are reachable |
| `[Service]` | How to run the application |
| `Type=simple` | Treat started process as main service process |
| `User=bitra` | Don't run app as root |
| `WorkingDirectory=.../app` | Set working directory for relative files |
| `ExecStart=.../.venv/bin/python -u app.py` | Start the intended Python interpreter and code |
| `Restart=on-failure` | Restart on unexpected nonzero exits/signals; **not** after intentional `systemctl stop` |
| `RestartSec=5` | Wait five seconds before retry |
| `Environment=...` | Supply an environment variable |
| `[Install]` / `WantedBy=multi-user.target` | Allow boot-time enablement |

Apply and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now opspulse
sudo systemctl status opspulse --no-pager -l
systemctl is-active opspulse
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/health
sudo journalctl -u opspulse -n 20 --no-pager
sudo journalctl -u opspulse -f
```

`journalctl -f` follows logs; Ctrl+C stops following.

### 10.3 Test process auto-restart

```bash
systemctl show -p MainPID --value opspulse
sudo systemctl kill --signal=SIGKILL --kill-whom=main opspulse
systemctl status opspulse --no-pager
sudo journalctl -u opspulse -n 25 --no-pager
```

**Use only in the lab.** The signal kills the service process unexpectedly, so `Restart=on-failure` should relaunch it. An administrative `systemctl stop` is different: it should stay stopped.

### 10.4 Actual incident: service inactive versus crash-loop

We encountered:

```text
Active: inactive (dead)
Process ... (code=killed, signal=TERM)
opspulse.service: Deactivated successfully.
```

**Meaning:** service was stopped; log did **not prove a crash** or who requested termination. Later, after starting it, we saw a fleeting `active (running)` after **2 ms**, and then:

```text
Active: activating (auto-restart) (Result: exit-code)
ExecStart=... (code=exited, status=1/FAILURE)
Scheduled restart job, restart counter is at 4
```

That early `active` reading was **not proof of stability**. The journal ultimately showed:

```text
Address already in use
Port 8080 is in use by another program.
```

Check:

```bash
sudo systemctl stop opspulse
sudo ss -lntp | grep ':8080'
```

We saw **`python` PID `6335`** listening. `ps -ef | grep -i 8080` found only `grep`, because the Python command line did not mention 8080. The correct inspection was:

```bash
ps -fp 6335
```

After confirming that PID belonged to the **manually launched OpsPulse**, the proposed repair was:

```bash
kill 6335
sudo ss -lntp | grep ':8080'    # expect nothing
sudo systemctl start opspulse
systemctl is-active opspulse
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/health
```

**Root cause:** two separate Flask processes tried to bind the same listening address and port. **Standardize on systemd** to prevent recurrence.

---

## 11. logrotate — stop log files growing forever

### 11.1 Actual installation/PATH issue

You ran:

```bash
logrotate --version
```

and Bash replied **`logrotate: command not found`** (`exit 127`). But:

```bash
sudo apt install -y logrotate
```

said **`logrotate is already the newest version (3.22.0-1)`**. This is **not proof the package was absent** — typically `/usr/sbin` was missing from the interactive user's `$PATH`.

Diagnose:

```bash
dpkg -L logrotate | grep '/logrotate$'
/usr/sbin/logrotate --version
echo "$PATH"
```

Optional Bash `PATH` fix if `/usr/sbin` is missing:

```bash
echo 'export PATH="$PATH:/usr/sbin"' >> ~/.bashrc
source ~/.bashrc
```

Or simply call `/usr/sbin/logrotate` explicitly, as our commands below do.

### 11.2 Configuration

```bash
sudo nano /etc/logrotate.d/opspulse
```

```conf
/home/bitra/winter-arc-integration-project/logs/health-check.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    su bitra bitra
}
```

| Directive | Purpose |
|---|---|
| `daily` | Rotate on a daily schedule when logrotate runs |
| `rotate 7` | Retain up to seven rotated versions |
| `compress` | Compress older copies |
| `delaycompress` | Defer compression of the newest rotated file |
| `missingok` | Don't fail if file is missing |
| `notifempty` | Skip empty logs |
| `copytruncate` | Copy then empty active file, so a writer can keep its file handle; **small log-loss window possible** |
| `su bitra bitra` | Use that user/group for rotation |

### 11.3 Test, rotate, verify

```bash
sudo /usr/sbin/logrotate -d /etc/logrotate.d/opspulse   # dry run, no changes
sudo /usr/sbin/logrotate -f /etc/logrotate.d/opspulse   # force once for lab
ls -lh ~/winter-arc-integration-project/logs/
bash ~/winter-arc-integration-project/scripts/health-check.sh
tail -n 5 ~/winter-arc-integration-project/logs/health-check.log
```

A forced first rotation may show `health-check.log` plus `health-check.log.1`. **We discussed these commands; the complete final directory listing was not pasted into chat**. Check your server before claiming compression is verified.

---

## 12. Linux resource monitoring — `server-health.sh`

We built a script reporting CPU, memory, root disk use, and Flask health.

### 12.1 Full script used

```bash
#!/usr/bin/env bash
set -u

PROJECT_DIR="$HOME/winter-arc-integration-project"
LOG_FILE="$PROJECT_DIR/logs/server-health.log"
APP_URL="http://localhost:8080/health"
THRESHOLD=80

mkdir -p "$PROJECT_DIR/logs"

# ANSI escape sequences: pretty terminal colors
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

# CPU counters from /proc/stat at two points ~1 second apart
read -r _ u n s idle wait irq sirq steal _ < /proc/stat
total1=$((u+n+s+idle+wait+irq+sirq+steal))
idle1=$((idle+wait))

sleep 1

read -r _ u n s idle wait irq sirq steal _ < /proc/stat
total2=$((u+n+s+idle+wait+irq+sirq+steal))
idle2=$((idle+wait))

delta_total=$((total2-total1))
delta_idle=$((idle2-idle1))

if (( delta_total > 0 )); then
    CPU=$((100*(delta_total-delta_idle)/delta_total))
else
    CPU=0
fi

MEMORY=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2*100}')
DISK=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$APP_URL")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=========================================="
echo " OpsPulse Server Health Report"
echo "=========================================="
echo "Timestamp      : $TIMESTAMP"
echo "CPU Usage      : $CPU%"
echo "Memory Usage   : $MEMORY%"
echo "Disk Usage     : $DISK%"
echo "Application    : HTTP $HTTP_CODE"
echo "=========================================="

echo "[$TIMESTAMP] CPU=$CPU% MEMORY=$MEMORY% DISK=$DISK% HTTP=$HTTP_CODE" >> "$LOG_FILE"

if (( CPU >= THRESHOLD || MEMORY >= THRESHOLD || DISK >= THRESHOLD )); then
    printf "${YELLOW}WARNING: Resource threshold exceeded!\n${RESET}"
fi

if [[ "$HTTP_CODE" == "200" ]]; then
    printf "${GREEN}Application Status: HEALTHY\n${RESET}"
else
    printf "${RED}Application Status: UNHEALTHY\n${RESET}"
    exit 1
fi
```

### 12.2 Script breakdown

| Part | Explanation |
|---|---|
| `read -r ... < /proc/stat` | Read cumulative Linux CPU counters |
| `total1`, `total2` | Sum sampled CPU time counters |
| `idle1`, `idle2` | Sum idle + I/O wait counters |
| `sleep 1` | Wait one second between samples |
| `$((...))` | Shell integer arithmetic |
| `CPU=...` | Estimated percentage of CPU non-idle time over sample interval |
| `free` | Display total/used/free memory |
| `awk '/^Mem:/ {...}'` | Find memory row and compute used/total percentage |
| `df -P /` | Disk capacity of root filesystem, in POSIX output layout |
| `gsub("%","",$5)` | Remove `%` sign so shell can compare an integer |
| `THRESHOLD=80` | Warn if **any** reported resource usage is 80% or more |
| `printf` with `\033[...]` | Show color-coded message in terminal |
| `>> "$LOG_FILE"` | Append a one-line record instead of replacing the file |

**Subtle but important caveats:** This is a **lab estimate**, not a production-grade exporter. CPU is overall system activity sampled for a second; memory is `free`'s `used` field, which can misrepresent pressure due to reclaimable cache; consider `MemAvailable` for a better pressure estimate. Root `df` does not measure every mounted filesystem. HTTP `200` by itself doesn't prove all application dependencies work.

### 12.3 Actual observed health report

You executed `./server-health.sh` and shared:

```text
==========================================
 OpsPulse Server Health Report
==========================================
Timestamp      : 2026-11-17 02:28:53
CPU Usage      : 2%
Memory Usage   : 50%
Disk Usage     : 1%
Application    : HTTP 200
==========================================
Application Status: HEALTHY
```

All resource metrics were below the configured 80% warning threshold. The timestamp was from the **Debian system clock (UTC in the service logs)**.

### 12.4 Additional Linux commands for incident triage

```bash
top
ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head
free -h
vmstat 1 5
df -h
du -sh ~/winter-arc-integration-project/logs
du -ah ~/winter-arc-integration-project/logs | sort -h | tail -10
```

Check **which** mount is full and **which** process actually consumes resources; don't blindly delete logs or restart production systems.

---

## 13. Manual OpsPulse v2 release

### 13.1 Create a backup and release candidate

```bash
cd ~/winter-arc-integration-project
mkdir -p releases backups
ls -lh app/app.py
systemctl is-active opspulse
cp app/app.py backups/app.py.v1
cp app/app.py releases/app-v2.py
nano releases/app-v2.py
```

In `home()`, set the version and welcome message:

```python
@app.route("/")
def home():
    return jsonify({
        "application": "OpsPulse",
        "version": "v2",
        "message": "Welcome to OpsPulse Version 2",
        "status": "running"
    })
```

Keep `/health` and main entry point unchanged.

### 13.2 Verify syntax, deploy, verify

```bash
app/.venv/bin/python -m py_compile releases/app-v2.py
cp releases/app-v2.py app/app.py
sudo systemctl restart opspulse
systemctl is-active opspulse
curl -s http://localhost:8080/
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/health
```

**Manual rollback if needed:**

```bash
cp backups/app.py.v1 app/app.py
sudo systemctl restart opspulse
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/health
```

These commands show the **backup-first principle**: never discard a known working release until the new version is verified.

---

## 14. Automated deploy-and-rollback script — final recreated version

The earlier script checked rollback health **only once** and mistakenly reported `CRITICAL` before Flask had finished starting. We therefore **recreated the entire script** using a quoted heredoc, so no tricky Nano line editing was needed.

### 14.1 Create and preserve previous file

```bash
cd ~/winter-arc-integration-project
cp scripts/deploy.sh scripts/deploy.sh.old
```

To write a complete file directly into PuTTY, use:

```bash
cat > scripts/deploy.sh <<'EOF'
# paste the ENTIRE SCRIPT below here, without the Markdown fences
EOF
```

Quoted `<<'EOF'` **prevents the calling shell from expanding `$VARIABLES` while the file is being created**. Keep the final `EOF` alone on its own line.

### 14.2 Complete `scripts/deploy.sh` from our final lab

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="$HOME/winter-arc-integration-project"
APP="$PROJECT/app/app.py"
PYTHON="$PROJECT/app/.venv/bin/python"
RELEASE="$PROJECT/releases/app-v2.py"
BACKUP_DIR="$PROJECT/backups"
HEALTH_URL="http://127.0.0.1:8080/health"
SERVICE="opspulse"

mkdir -p "$BACKUP_DIR"

# Check required files
[[ -f "$APP" ]] || { echo "ERROR: Application missing"; exit 1; }
[[ -f "$RELEASE" ]] || { echo "ERROR: Release missing"; exit 1; }
[[ -x "$PYTHON" ]] || { echo "ERROR: Python missing"; exit 1; }

# Validate Python syntax
"$PYTHON" -m py_compile "$RELEASE"

# Ensure current application is healthy
if ! systemctl is-active --quiet "$SERVICE"; then
    echo "ERROR: Service is not running."
    exit 1
fi

if ! curl -fsS --max-time 5 "$HEALTH_URL" > /dev/null; then
    echo "ERROR: Current application is unhealthy."
    exit 1
fi

# Backup current application
BACKUP="$BACKUP_DIR/app-$(date +%Y%m%d-%H%M%S)-$$.py"
cp -p "$APP" "$BACKUP"

echo "Backup created: $BACKUP"
echo "Deploying OpsPulse..."

# Function to verify application health
check_health() {
    local attempt http_code

    for attempt in {1..10}; do
        http_code=$(curl -s -o /dev/null -w '%{http_code}' \
            --max-time 3 "$HEALTH_URL" || true)

        if systemctl is-active --quiet "$SERVICE" &&
           [[ "$http_code" == "200" ]]; then
            return 0
        fi

        echo "Health check $attempt/10: HTTP $http_code"
        sleep 2
    done

    return 1
}

# Deploy release
cp "$RELEASE" "$APP"

if ! sudo systemctl restart "$SERVICE"; then
    echo "WARNING: Deployment restart failed."
fi

# Verify new release
if check_health; then
    echo "SUCCESS: OpsPulse deployment completed!"
    echo "Backup: $BACKUP"
    exit 0
fi

# Automatic rollback
echo "FAILED: Deployment unhealthy. Rolling back..."
cp "$BACKUP" "$APP"

if ! sudo systemctl restart "$SERVICE"; then
    echo "WARNING: Rollback restart failed."
fi

if check_health; then
    echo "ROLLBACK SUCCESSFUL: Previous version restored."
else
    echo "CRITICAL: Rollback verification failed!"
    sudo journalctl -u "$SERVICE" -n 15 --no-pager
fi

exit 1
```

### 14.3 Explain the deployment Bash script section by section

| Code/feature | Meaning and why it matters |
|---|---|
| `set -Eeuo pipefail` | Defensive shell options: `-e` exit on many uncaught command failures; `-E` propagate ERR trap behavior (if traps are defined); `-u` unset variable error; `pipefail` pipeline fails if any component fails. **These are not a substitute for testing all failure paths.** |
| `PROJECT=...` | One path variable, reused consistently |
| `APP=...` | Live application file that systemd executes |
| `PYTHON=...` | The exact virtual environment Python |
| `RELEASE=...` | Candidate release copied to live location |
| `BACKUP_DIR=...` | Snapshot directory |
| `HEALTH_URL=...` | HTTP endpoint used after restart |
| `SERVICE=opspulse` | systemd unit name |
| `[[ -f ... ]]` | File must exist |
| `[[ -x ... ]]` | Python binary must exist and be executable |
| `\|\| { ...; exit 1; }` | If prerequisite fails, print message and abort |
| `py_compile` | Parse/compile Python; catches syntax errors but **not runtime failure** |
| `systemctl is-active --quiet` | Require currently running service before deployment |
| `curl -fsS` | Quiet but fail on HTTP errors; ensure baseline responds before modifying it |
| `$(date ...)` | Timestamp embedded in unique backup file name |
| `$$` | PID of the current shell/script; helps distinguish backup filenames |
| `cp -p` | Copy file preserving metadata where possible |
| `check_health() { ... }` | Define reusable Bash function for deploy and rollback |
| `local attempt http_code` | Function-local variables |
| `for attempt in {1..10}` | Up to ten health-check attempts |
| `curl ... \|\| true` | Avoid an expected connection failure aborting the whole script under `set -e` |
| `&&` | Require **both** active service and HTTP 200 |
| `return 0` / `return 1` | Function reports pass/fail to caller |
| `sleep 2` | Give server time to come up |
| `sudo systemctl restart` | Restart service with the new file |
| `cp "$BACKUP" "$APP"` | Restore last working file on failure |
| `journalctl` | Gather recent systemd application logs if rollback still unhealthy |
| final `exit 1` | Deployment failed even if rollback recovered; CI must detect this |

### 14.4 Check executable, syntax, run

```bash
chmod +x scripts/deploy.sh
bash -n scripts/deploy.sh
systemctl is-active opspulse
curl -s http://localhost:8080/
./scripts/deploy.sh
```

`bash -n` parses a Bash script without executing it. The `-n` check **does not prove the deployment logic works**; the failure exercise below did that.

### 14.5 What actually happened in our final deploy.sh run

You shared:

```text
{"application":"OpsPulse","message":"Welcome to OpsPulse Version 2","status":"running","version":"v2"}
Backup created: /home/bitra/winter-arc-integration-project/backups/app-20261117-030029-8209.py
Deploying OpsPulse...
Health check 1/10: HTTP 000
Health check 2/10: HTTP 000
Health check 3/10: HTTP 000
Health check 4/10: HTTP 000
Health check 5/10: HTTP 000
Health check 6/10: HTTP 000
Health check 7/10: HTTP 000
Health check 8/10: HTTP 000
Health check 9/10: HTTP 000
Health check 10/10: HTTP 000
FAILED: Deployment unhealthy. Rolling back...
Health check 1/10: HTTP 000
ROLLBACK SUCCESSFUL: Previous version restored.
[ble: exit 1]
```

And immediately afterward:

```json
{"application":"OpsPulse","message":"Welcome to OpsPulse Version 2","status":"running","version":"v2"}
```

**What is proven:** The deployed candidate did not become reachable during ten health checks; the script restored a backup and its recovery checker **eventually** observed healthy status; the final application reported v2; the script appropriately returned failure (`exit 1`) for the failed deployment.

**What is not proven:** The exact reason the candidate failed in that last run. The earlier deliberate `RuntimeError` is one possibility, but without logs from this particular deployment we **must not assert it as fact**. The right next investigation is `sudo journalctl -u opspulse -n 80 --no-pager`, followed by inspecting `releases/app-v2.py`.

### 14.6 One key limitation to improve later

Current checks require HTTP `200` but **do not verify the expected release version or JSON schema**. A stale/incorrect process could satisfy `/health`. In a later improvement, add version assertions, an exclusive deployment lock (`flock`), application tests, a safe atomic release strategy, and rollback failure escalation. Do not put production secrets in the script or repository. Also be aware that a `set -e` exit during certain file-copy failures can bypass the manual rollback path; a production-grade script needs an explicit failure trap and release transaction design.

---

## 15. Deliberately break a release to test rollback

### 15.1 Prepare a known working version

```bash
cd ~/winter-arc-integration-project
systemctl is-active opspulse
curl -fsS http://127.0.0.1:8080/health
cp app/app.py releases/app-v2-working.py
cp releases/app-v2.py releases/app-v2.py.before-test
cp app/app.py releases/app-v2.py
```

### 15.2 Introduce an intentional startup error

The lab initially discussed appending an exception at the bottom of the file; **that is unreliable** if an earlier `app.run()` blocks forever. The correction was to **prepend** the error:

```bash
sed -i '1i raise RuntimeError("Intentional rollback test")' releases/app-v2.py
app/.venv/bin/python -m py_compile releases/app-v2.py
```

**Important:** `py_compile` can succeed because `raise RuntimeError(...)` is perfectly valid Python **syntax**; the exception only occurs **when Python runs the module**.

### 15.3 Run rollback test and inspect logs

```bash
./scripts/deploy.sh
systemctl is-active opspulse
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/
sudo journalctl -u opspulse -n 30 --no-pager
```

**Original test outcome:**

```text
FAILED: Rolling back to previous version...
CRITICAL: Rollback verification failed!
[ble: exit 1]
```

**Investigation:** The subsequent journal showed the injected `RuntimeError`, systemd retrying, then Flask starting and serving HTTP 200. The **original script checked rollback recovery too soon**, yielding a *false negative*. It was later replaced with a script that retries recovery.

### 15.4 Restore the clean candidate release

```bash
cd ~/winter-arc-integration-project
if [ -f releases/app-v2.py.before-test ]; then cp releases/app-v2.py.before-test releases/app-v2.py; fi
grep -n 'Intentional rollback test' releases/app-v2.py || echo "No test error found"
app/.venv/bin/python -m py_compile releases/app-v2.py
```

Check **both** the runtime application and release candidate:

```bash
systemctl is-active opspulse
curl -s http://127.0.0.1:8080/
cmp app/app.py releases/app-v2.py && echo "Release and running application match"
```

If `cmp` reports a difference, **inspect the difference** (`diff -u app/app.py releases/app-v2.py`) rather than blindly replacing one with the other.

---

## 16. Git project: safe version control

### 16.1 Verify repository and remote

```bash
cd ~/winter-arc-integration-project
git status
git remote -v
ls -la .github/workflows 2>/dev/null || echo "No GitHub Actions workflows yet"
```

**Observed:** existing branch `main`, remote:

```text
origin https://github.com/manasabitra1989/winter-arc-integration-project.git (fetch)
origin https://github.com/manasabitra1989/winter-arc-integration-project.git (push)
```

Initially `app/`, `backups/`, `logs/`, `releases/`, and `scripts/` were untracked; no workflow directory existed yet.

### 16.2 `.gitignore`

Protect **generated logs, backups, virtual environments, tokens, and private keys**:

```gitignore
# Python virtual environments
.venv/
venv/
env/

# Python generated files
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/

# Logs and deployment backups
*.log
logs/
backups/

# Secrets and credentials
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
*.secret

# Editors and OS
.vscode/
.idea/
.DS_Store
*.swp

# Temp files
*.tmp
*.bak
releases/*.before-test
releases/*.py.before-test
scripts/*.old
releases/*-working.py
```

`.gitignore` does **not remove a secret that Git already committed or staged**; remove it from the index and rotate leaked credentials if necessary. Exclusion patterns should be reviewed before `git add`.

### 16.3 Stage, inspect, commit, push

```bash
git status --short
git status --short --ignored
git add -n .                 # preview what would be staged
git add .gitignore app/app.py scripts/ releases/
git status
```

The actual staging included `scripts/deploy.sh.old` and `releases/app-v2-working.py`, which are **local backups**, not desirable project source. We corrected that by:

```bash
git restore --staged scripts/deploy.sh.old
git restore --staged releases/app-v2-working.py
# append ignore patterns to .gitignore and then:
git add .gitignore
```

Verify:

```bash
git diff --cached --check
git diff --cached --stat
git status
```

Commit and synchronize:

```bash
git commit -m "Add OpsPulse monitoring and deployment automation"
git log -1 --oneline
git fetch origin
git status -sb
git push -u origin main
```

Never `git push --force` merely to overcome a non-fast-forward error. Fetch, inspect the histories, and reconcile properly.

**Actual post-push observation:**

```text
On branch main
Your branch is up to date with 'origin/main'.
Changes not staged for commit:
    modified: .gitignore
```

Thus the remote branch was synchronized at that moment, but one **local `.gitignore` edit remained**. We discussed reviewing and committing it separately:

```bash
git diff -- .gitignore
git add .gitignore
git commit -m "Update gitignore for temporary and backup files"
git push origin main
```

Do not claim the final `.gitignore` commit was pushed unless `git status` and GitHub confirm it.

---

## 17. GitHub authentication — HTTPS PAT and then SSH

### 17.1 Why Git asked for a password

Your terminal prompted:

```text
Username for 'https://github.com': manasabitra1989
Password for 'https://manasabitra1989@github.com':
```

GitHub account passwords do not authenticate HTTPS Git operations. The password field expects a **Personal Access Token (PAT)** or an appropriate credential manager integration, **not** your GitHub account password.

We discussed a fine-grained PAT restricted to the specific repository with **Contents: Read and write**, with short expiration. **Never place a token in the README, chat, `.env` committed to Git, or a command line that persists in history.**

### 17.2 Why we switched to SSH

SSH public-key authentication lets Git use a private key on Debian instead of repeatedly prompting for username/PAT.

Check existing public keys:

```bash
ls -la ~/.ssh/*.pub
```

**Observed:** no matching `.pub` file existed.

Generate a new dedicated key:

```bash
ssh-keygen -t ed25519 -C "GitHub OpsPulse" -f ~/.ssh/id_ed25519_github
```

This creates:

| File | Safe to share with GitHub? | Use |
|---|---|---|
| `~/.ssh/id_ed25519_github.pub` | **Yes** | Public authentication key |
| `~/.ssh/id_ed25519_github` | **No** | Private key; keep secret |

Copy **only** the public key:

```bash
cat ~/.ssh/id_ed25519_github.pub
```

Add it at **[GitHub SSH key settings](https://github.com/settings/ssh/new)**; in our conversation you confirmed **“ssh key added.”**

### 17.3 SSH config and test

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
EOF
chmod 700 ~/.ssh
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519_github
ssh -T git@github.com
```

First-time host-key prompt: check fingerprint against **[GitHub's published SSH host key fingerprints](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints)** before accepting.

Typical GitHub success message:

```text
Hi manasabitra1989! You've successfully authenticated, but GitHub does not provide shell access.
```

If a **passphrase** was assigned to the private key, it may still be requested. Use a trusted SSH agent for convenience; **do not remove your passphrase just to avoid prompts**.

Change Git remote to SSH:

```bash
cd ~/winter-arc-integration-project
git remote set-url origin git@github.com:manasabitra1989/winter-arc-integration-project.git
git remote -v
git push origin main
```

**Observed from chat:** you said the setup “seems all good,” but did not share `ssh -T` or a successful SSH push transcript. Verify when documenting project completion.

---

## 18. GitHub Actions: first CI pipeline (proposed workflow)

### 18.1 Why CI?

Without CI, a malformed Python file or invalid Bash script can be committed and only fail on the server. Continuous integration checks code automatically after pushes/pull requests. **Our first workflow is CI only; it does not yet deploy the application.**

### 18.2 Create `.github/workflows/opspulse-ci.yml`

```bash
cd ~/winter-arc-integration-project
mkdir -p .github/workflows
cat > .github/workflows/opspulse-ci.yml <<'EOF'
name: OpsPulse CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  validate:
    name: Validate Python and Bash
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Validate Python syntax
        run: |
          python -m py_compile app/app.py
          python -m py_compile releases/app-v2.py

      - name: Validate Bash scripts
        run: |
          bash -n scripts/deploy.sh
          bash -n scripts/health-check.sh
          bash -n scripts/server-health.sh

      - name: Verify required files
        run: |
          test -f app/app.py
          test -f scripts/deploy.sh
          test -f scripts/health-check.sh
          test -f scripts/server-health.sh

      - name: CI validation successful
        run: echo "OpsPulse CI checks passed!"
EOF
```

### 18.3 Explain workflow YAML

| Field | Plain-English meaning |
|---|---|
| `name:` | Name shown in GitHub Actions |
| `on: push` | Run after push to main |
| `pull_request` | Run when a PR targets main |
| `workflow_dispatch` | Enable manual trigger |
| `jobs:` | Jobs to execute |
| `runs-on: ubuntu-latest` | GitHub-hosted Linux runner |
| `steps:` | Ordered tasks inside job |
| `actions/checkout@v4` | Download repository into runner |
| `actions/setup-python@v5` | Select Python runtime |
| `run: \|` | Execute multiple shell command lines |
| `python -m py_compile` | Syntax check; not a functional test |
| `bash -n` | Bash syntax check; not an end-to-end script test |
| `test -f` | Check required path exists |

Commit and push:

```bash
git add .github/workflows/opspulse-ci.yml
git commit -m "Add GitHub Actions CI pipeline for OpsPulse"
git push origin main
```

Inspect the **[Actions tab](https://github.com/manasabitra1989/winter-arc-integration-project/actions)**. A green run shows **syntax and file checks** passed, **not** that the app actually started or the `/health` endpoint worked.

**Verification status:** We **provided** this workflow in the chat. No subsequent Actions result was shared; the workflow's run status remains **unverified**.

---

## 19. Complete incident and troubleshooting journal

| # | Symptom or failure | Real cause / evidence | Fix or investigation | General lesson |
|---|---|---|---|---|
| 1 | PuTTY text hard to distinguish | PS1, commands, and output looked similar | PuTTY colors + Bash PS1 + ble.sh | Terminal colors come from several layers |
| 2 | ble.sh said `$LANG` empty | Login locale not set | `locale -a`, `export LANG=C.UTF-8`, persistent login setting | Interactive shell environment matters |
| 3 | `locale -` unknown name | Wrong option typed | Correct `locale -a` | Small CLI syntax errors matter |
| 4 | ble.sh showed `-- MULTILINE --` | Backslash at line end kept command open | Ctrl+J to execute, Ctrl+C cancel, or one-line curl | Multiline input is editor behavior |
| 5 | `[[: not found` and false unhealthy 200 | `sh` ran dash, but script used Bash `[[ ]]` | `bash health-check.sh` or executable with shebang | Shebang does not override explicit `sh` |
| 6 | curl returned `HTTP 000` | No HTTP response when Flask stopped | Restore service / inspect network and port | `000` is curl placeholder, not HTTP code |
| 7 | `logrotate: command not found` though installed | Executable likely in `/usr/sbin` outside PATH | `/usr/sbin/logrotate --version`, inspect PATH | Installed != discoverable via current PATH |
| 8 | `systemctl is-active` -> `inactive` | Service not running; earlier shutdown by SIGTERM | Inspect status, port and journal before restart | Inactive != necessarily crashed |
| 9 | Service briefly `active` then `auto-restart` | Early observation before startup settled | Recheck after delay and inspect journal | Wait for stable health, not transient state |
| 10 | Flask failed with `Address already in use` | Separate manually started `python` occupied port 8080 | `ss -lntp`, inspect PID 6335, stop only that process, start systemd | One application instance / one owner of port |
| 11 | `ps | grep 8080` found no owner | Command line did not contain port number | `sudo ss -lntp | grep ':8080'` | Socket tools answer port questions |
| 12 | `py_compile` passed but broken release crashed | Python `raise RuntimeError(...)` is valid syntax | Runtime health check and rollback | Syntax != execution correctness |
| 13 | Rollback said `CRITICAL`, but Flask later healthy | Original rollback checked too soon | Health retry loop after restore | Startup needs time; verify recovery robustly |
| 14 | Revised deploy made 10 HTTP `000` attempts then rolled back | Candidate didn't become reachable; exact cause for **that run** unconfirmed | Inspect journal/release; verify backup restored | Preserve evidence; don't guess cause |
| 15 | Git staged `deploy.sh.old` and `app-v2-working.py` | `git add` included temporary files | `git restore --staged`, update `.gitignore` | Review staging, not just repository content |
| 16 | GitHub HTTPS password prompt | Password auth not supported for HTTPS Git | PAT or SSH | Never store account password in repo |
| 17 | No `~/.ssh/*.pub` | No public key at that location | `ssh-keygen -t ed25519 ...`, add `.pub` to GitHub | Public vs private key distinction |
| 18 | `git status` showed `.gitignore` modified after push | Local ignored-file policy edit uncommitted | Review, stage, commit, push separately | Synced branch can still have local changes |

---

## 20. Daily verification and production-style operational checklist

### 20.1 Before starting the lab

- [ ] `pwd` points to the correct project; `git status` reviewed.
- [ ] Only one process manager is responsible for port 8080.
- [ ] `systemctl is-active opspulse` is `active`.
- [ ] `sudo ss -lntp | grep ':8080'` shows expected Python PID.
- [ ] `curl -fsS http://127.0.0.1:8080/health` succeeds.
- [ ] `curl -s http://127.0.0.1:8080/` shows expected version.
- [ ] `journalctl -u opspulse` has no unexplained restart loop.
- [ ] Disk space: `df -h`; memory: `free -h`; resource snapshot as needed.
- [ ] `crontab -l` and monitoring logs match the intended lab schedule.
- [ ] No stale bad release still contains the injected `RuntimeError`.

### 20.2 Before every deployment

- [ ] Confirm **working previous version** and a recent backup.
- [ ] Confirm `releases/app-v2.py` is the **intended** release, not the broken test candidate.
- [ ] Check Python syntax and test the **actual endpoint behavior**.
- [ ] Check Bash syntax: `bash -n scripts/deploy.sh`.
- [ ] Check port 8080 and service status.
- [ ] Confirm ability to run `sudo systemctl restart opspulse`.
- [ ] Confirm free disk space for backup and logs.
- [ ] Know rollback plan and command; don't run multiple deployments at once.
- [ ] Preserve incident evidence if it fails (`journalctl`, backup path, diff).

### 20.3 After deployment

- [ ] Service is **stable** (not briefly active before failing).
- [ ] HTTP `/health` returns 200 after readiness retries.
- [ ] Root route returns **expected version**, not merely any healthy response.
- [ ] Logs contain no errors / restart loops.
- [ ] Deployment exit code reviewed (`0` success; `1` failure even after rollback).
- [ ] Confirm backup was created and stored safely.
- [ ] Check cron health-log transitions for any downtime.

### 20.4 At the end of the practice session

- [ ] Disable the per-minute cron task if no longer needed.
- [ ] Decide whether to leave systemd running; stop if not required.
- [ ] Verify no manually launched duplicate Flask process remains.
- [ ] Preserve project source, not virtual env/log/backup artifacts, in Git.
- [ ] Verify `git status`, `git remote -v`, and latest push results.
- [ ] Keep SSH private keys and tokens off GitHub.

### Useful single-screen health commands

```bash
cd ~/winter-arc-integration-project
systemctl is-active opspulse
sudo ss -lntp | grep ':8080'
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" --max-time 5 http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/
bash scripts/health-check.sh
bash scripts/server-health.sh
sudo journalctl -u opspulse -n 20 --no-pager
tail -n 5 logs/health-check.log
git status -sb
```

---

## 21. Beginner-friendly command reference

| Command | Meaning | Example |
|---|---|---|
| `pwd` | Present working directory | `pwd` |
| `cd` | Change directory | `cd ~/winter-arc-integration-project` |
| `ls -lh` | List human-readable file sizes | `ls -lh backups/` |
| `mkdir -p` | Create directory tree | `mkdir -p scripts logs` |
| `cp` | Copy file | `cp app/app.py backups/app.py.v1` |
| `mv` | Move/rename file | `mv old.py new.py` |
| `nano` | Edit a file | `nano app/app.py` |
| `cat` | Print contents | `cat ~/.ssh/id_ed25519_github.pub` |
| `cat > FILE <<'EOF'` | Create whole file from pasted block | Recreate `deploy.sh` |
| `chmod +x` | Make script executable | `chmod +x scripts/deploy.sh` |
| `source` | Load file into current shell | `source app/.venv/bin/activate` |
| `grep` | Filter matching lines | `grep ':8080'` |
| `tail -n 5` | Last five lines | `tail -n 5 logs/health-check.log` |
| `tail -f` | Follow new log lines | `tail -f app/logs/flask.log` |
| `ps` | Show processes | `ps -fp PID` |
| `ss` | Show sockets | `sudo ss -lntp` |
| `curl` | HTTP request | `curl -i localhost:8080/health` |
| `systemctl` | Service control | `sudo systemctl restart opspulse` |
| `journalctl` | Read systemd journal | `sudo journalctl -u opspulse -n 30` |
| `crontab -e` | Edit scheduled jobs | Every-minute health check |
| `logrotate` | Rotate old logs | `sudo /usr/sbin/logrotate -d ...` |
| `df` | Disk filesystem usage | `df -h` |
| `du` | Directory/file size | `du -sh logs` |
| `free` | RAM summary | `free -h` |
| `top` | Live process activity | `top` |
| `git add` | Stage changes | `git add app/app.py` |
| `git diff --cached` | Review staged changes | `git diff --cached --stat` |
| `git commit` | Create version snapshot | `git commit -m "..."` |
| `git push` | Send commits to remote | `git push origin main` |

---

## 22. Interview questions and self-test answers

Try answering each in your own words first.

1. **Image vs process?** — A Docker image is a packaged template; a running process is an active program. (Docker will be integrated later.)
2. **What is a Python virtual environment?** — An isolated place for one project's Python packages and interpreter paths.
3. **Why `python -m pip`?** — To install packages with the pip associated with the selected Python interpreter.
4. **What is Flask?** — A Python web framework for mapping routes to handler functions and returning HTTP responses.
5. **What is an API endpoint?** — An HTTP URL path such as `/health` that triggers application behavior.
6. **Why JSON?** — A lightweight structured data format understood by apps and scripts.
7. **What's the difference between `localhost` and `0.0.0.0`?** — `localhost` targets the machine itself; `0.0.0.0` in server bind settings means listen on all IPv4 interfaces.
8. **Why do Pods/services or apps use health checks?** — To detect whether a service can respond to requests; Kubernetes integration can later use readiness/liveness probes.
9. **`200` vs `404` vs `000`?** — Success; route not found; curl did not receive an HTTP response status.
10. **Why can a process be running but unhealthy?** — It might hang, fail to bind, return 500 errors, or have broken dependencies.
11. **Why use `ss` rather than `grep 8080` on `ps`?** — `ss` maps listening sockets to PIDs even when the process command line omits the port.
12. **PID vs PPID?** — Process ID vs parent process ID.
13. **What's the difference between `sh` and `bash`?** — They may be different shells; dash (common Debian `/bin/sh`) doesn't support Bash `[[ ]]`.
14. **Why did `sh health-check.sh` return unhealthy when Flask returned 200?** — Unsupported Bash conditional syntax caused the wrong branch to run.
15. **What does `#!/usr/bin/env bash` do?** — Selects Bash when the file is executed directly; explicit `sh filename` bypasses it.
16. **What is `$?`?** — Exit status of the most recent command.
17. **What is `2>&1`?** — Redirect stderr to the current stdout destination.
18. **What is `&` after a command?** — Run it in the background.
19. **Why use `tee -a`?** — Show a message and append it to a log simultaneously.
20. **Cron vs systemd?** — Cron schedules periodic commands; systemd manages service lifecycles and can restart failing processes.
21. **Why not use cron to start Flask every minute?** — It can launch duplicates and cause port conflicts; let systemd own the long-running app.
22. **What does `Restart=on-failure` mean?** — Restart on failure, not after intentional administrative stop.
23. **`inactive (dead)` vs `failed`?** — Stopped without systemd classifying failure vs service failed; read logs for context.
24. **What did `restart counter is at 4` indicate?** — Several attempts to restart; not proof the app is healthy.
25. **What caused our port conflict?** — A manually started Flask instance was still listening on 8080 while systemd tried to start another.
26. **Why logrotate?** — Bound log growth to protect disk space.
27. **Why can `logrotate` be installed but `command not found`?** — Binary exists outside the user's PATH.
28. **What does `copytruncate` trade off?** — Keeps writers using the same file but can lose a small amount of data while copying/truncating.
29. **What does `awk` do?** — Selects and processes structured text, here `free` and `df` output.
30. **What is `/proc/stat`?** — Kernel CPU activity counters used to calculate usage from differences between samples.
31. **Why is `free` used-percent an imperfect memory-pressure signal?** — Reclaimable cache affects memory reporting; `MemAvailable` is usually more helpful.
32. **Why take a backup before a release?** — To preserve a known working state for rollback.
33. **Why didn't `py_compile` catch `RuntimeError`?** — It checks syntax, not whether running the program succeeds.
34. **Why did our first rollback verification say CRITICAL?** — One immediate health check ran before Flask recovery had settled.
35. **Why return exit 1 after a successful rollback?** — The deployment itself still failed; CI/CD must register the release failure.
36. **Can HTTP 200 guarantee correct deployment version?** — No; also assert the API version and expected behavior.
37. **What is `set -Eeuo pipefail`?** — A bundle of shell failure-detection options, with limitations.
38. **Why keep credentials out of Git?** — Cloned repository history can expose them indefinitely.
39. **Why use `.gitignore`?** — Exclude generated files, local environment data, credentials, and temporary backups from staging by default.
40. **Difference between Git HTTPS PAT and SSH?** — PAT authenticates HTTP Git requests; SSH authenticates with a public/private key pair.
41. **Which SSH key goes to GitHub?** — The **public `.pub`** key, never the private key.
42. **What does GitHub Actions currently check?** — File existence and Python/Bash syntax; functional integration tests are a future improvement.
43. **What makes CI different from CD?** — CI checks and integrates code; delivery/deployment workflows distribute or release it.
44. **What would you check when a deployment repeatedly returns HTTP 000?** — `systemctl`, journal errors, port ownership, bind address, Python exceptions, permissions, deployed code, network, and dependencies.
45. **What is the production-safe alternative to Flask's development server?** — A production WSGI server, appropriate proxy/TLS, proper service management, observability, and security controls.

### Scenario practice: discuss in an interview

**Scenario A — 8080 already used:** Explain how you found PID with `ss`, checked its command with `ps`, prevented duplicate manually started processes, and standardized on systemd.

**Scenario B — false-positive health or false-negative rollback:** Explain why startup timing matters and why retry-based readiness checks are necessary. Distinguish the **candidate deployment failing** from the **rollback itself recovering**.

**Scenario C — syntax passes, runtime fails:** Explain `py_compile` versus execution, runtime imports/config/files/port availability, and rollback.

**Scenario D — disk full:** Demonstrate `df -h`, `du`, logrotate, identifying the responsible filesystem, retention, and safe cleanup.

**Scenario E — an SSH push fails:** Check key permissions, GitHub public key registration, `ssh -T`, host fingerprint, remote URL, and repository permission; **never expose the private key**.

---

## 23. Gaps, next steps, and upgrades

These items are **not yet all completed/verified** in our conversation:

- [ ] Confirm a **clean** `releases/app-v2.py` without test-only `RuntimeError` and run an intentional **successful** deployment end to end.
- [ ] Validate the version returned by `/`, not just HTTP 200 from `/health`.
- [ ] Add repeatable Python API tests (e.g., Flask `test_client`, `pytest`) including `200`, JSON fields, and a failing test.
- [ ] Add dependency manifest: `requirements.txt` with appropriate version constraints; install during CI. Syntax-only checks require no Flask import execution, but functional tests **do**.
- [ ] Confirm `.github/workflows/opspulse-ci.yml` was committed and a GitHub Actions run passed.
- [ ] Add CI tests, linting, and perhaps ShellCheck; pin/upgrade GitHub Actions appropriately.
- [ ] Protect `main` with PR checks; no unreviewed deploy from arbitrary commits.
- [ ] Make deploy script verify app version and use concurrency lock / transactional release workflow.
- [ ] Add timestamps, structured log fields, alerts, and appropriate rotation for **both** health and server-health logs.
- [ ] Move Flask from its development server to a production WSGI server before any real exposure.
- [ ] Introduce Docker image and Compose; then Kubernetes Deployment/Service/probes, and AWS architecture when this stage is completed.
- [ ] Add a top-level project usage guide, screenshots, and a sanitized CI badge after the workflow is verified.
- [ ] Keep infrastructure configuration (e.g., example systemd unit, sanitized cron and logrotate configs) in version control **as templates**, while still installing them to `/etc` on the machine.

---

## 24. Complete quick-start recap (for a future review)

> **Do not paste all commands blindly.** This is a quick-reference sequence for an environment that is **already configured**. Check and stop if any prerequisite fails.

```bash
# 1. Inspect project and version control
cd ~/winter-arc-integration-project
git status -sb
git remote -v

# 2. Verify Python and release source
app/.venv/bin/python --version
app/.venv/bin/python -m py_compile app/app.py
app/.venv/bin/python -m py_compile releases/app-v2.py
bash -n scripts/deploy.sh
bash -n scripts/health-check.sh
bash -n scripts/server-health.sh

# 3. Verify systemd, port, and API
systemctl is-active opspulse
sudo ss -lntp | grep ':8080'
curl -s http://127.0.0.1:8080/
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8080/health

# 4. Verify monitoring and logs
bash scripts/health-check.sh
bash scripts/server-health.sh
crontab -l
tail -n 5 logs/health-check.log
tail -n 5 logs/server-health.log
sudo journalctl -u opspulse -n 30 --no-pager

# 5. Check logrotate config without making changes
sudo /usr/sbin/logrotate -d /etc/logrotate.d/opspulse

# 6. Inspect backup files and release contents BEFORE deployment
ls -lh backups/ releases/
grep -n 'Intentional rollback test' releases/app-v2.py || true
diff -u app/app.py releases/app-v2.py || true

# 7. ONLY after verifying a clean candidate and active service:
# ./scripts/deploy.sh
```

## 25. What to say about this assignment in an interview or LinkedIn post

> **Built OpsPulse, a Flask-based Linux monitoring lab, and operated it through systemd.** Implemented HTTP health checks and Bash monitoring, scheduled checks using cron, configured logrotate, measured CPU/memory/disk utilization, created backup-first deployment automation with health-gated rollback, investigated a TCP port conflict and a Python runtime failure, and used Git/GitHub for source control. Began adding GitHub Actions CI validation. Key lessons: process presence is not application health; syntax checks do not catch runtime errors; readiness retries are essential; and failed releases must be reflected as nonzero exit codes even after recovery.

---

## 26. Official learning references

- [Python documentation](https://docs.python.org/3/)
- [Python `venv`](https://docs.python.org/3/library/venv.html)
- [Flask documentation](https://flask.palletsprojects.com/)
- [GNU Bash manual](https://www.gnu.org/software/bash/manual/)
- [curl documentation](https://curl.se/docs/)
- [systemd service manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemctl manual](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [GitHub SSH authentication](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [ble.sh project](https://github.com/akinomyoga/ble.sh)

---

### Final learning summary

We did **more than get an app running**: we exercised a full operational loop — build -> test -> observe -> simulate failure -> investigate logs/process/port -> recover -> automate -> version-control -> start CI. The most valuable incident was the contrast between **“Deployment failed”** and **“Rollback eventually recovered”**: those are different facts, and reliable automation must report both accurately.

*README compiled from the OpsPulse lab conversation, not from a live scan of your Debian filesystem. Verify commands and code against the current repository before treating this as an exact snapshot of running software.*
