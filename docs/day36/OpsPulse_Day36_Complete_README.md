# Day 36 — OpsPulse Incident Management Dashboard

> **End-to-end lab and beginner-friendly code study guide**  
> Source: `manasabitra1989/winter-arc-integration-project`, Day 36 application, Docker and Compose files, inspected November 22, 2026.  
> This README combines the original Day 36 implementation notes with a detailed explanation of all files used by the dashboard. It does **not** claim that AWS, Prometheus, or Grafana were deployed.

## 1. Objective and result

We extended the existing OpsPulse project (Days 30–35), rather than creating a new application. A Flask application serves an HTML dashboard, JavaScript communicates with Flask REST APIs, and PostgreSQL stores incidents. Users can create, resolve, and reopen incidents in their browser. Docker Compose runs Flask and PostgreSQL together. The Windows browser reaches the localhost-only service on Debian2 through a PuTTY SSH tunnel.

**Verified on Day 36:** browser dashboard available; `GET /dashboard` and `GET /ready` returned HTTP 200; initial two incidents were preserved; incident #3 was created through the browser; Resolve/Reopen requests changed persisted status and updated dashboard counts. The final verified API state was incident #1 OPEN, #2 OPEN, #3 RESOLVED, with totals 3 / open 2 / resolved 1 / critical 1. Git commit `8d4900e` was pushed and the working tree was clean.

## 2. File map — understand what runs where

| File | Language | Responsibility |
|---|---|---|
| `app/app.py` | Python + embedded SQL strings | Flask routes, input validation, PostgreSQL connection and queries |
| `app/templates/dashboard.html` | HTML + embedded CSS + JavaScript | Dashboard layout, visual styling, API calls, buttons and counters |
| `app/Dockerfile` | Dockerfile instructions | Build a Flask image containing `app.py`, dependencies and the HTML template |
| `app/.dockerignore` | Pattern list | Prevent local venv, logs, Git history and sensitive files entering build context |
| `app/requirements.txt` | Python dependencies | Flask, Gunicorn and Psycopg |
| `day33-compose/compose.yaml` | YAML | Flask/Postgres services, environment, ports, network and persistent volume |
| `docs/revision-tracker.md` | Markdown | Learning review and revision priorities; not executed by the application |

**Correction to remember:** `app.py` is Python, not HTML. The HTML, CSS and JavaScript are in **one** `dashboard.html` file. Flask loads that file with `render_template()`.

## 3. Architecture and request flow

```text
Windows Chrome
  GET http://127.0.0.1:8082/dashboard
         |
PuTTY SSH tunnel  (Windows local 8082 -> Debian2 localhost 8082)
         |
Debian2 127.0.0.1:8082 -> Docker app container :8080
         |
Flask / Gunicorn (app/app.py) <-> JavaScript in dashboard.html
         |
Docker Compose internal network, hostname db :5432
         |
PostgreSQL 17 -> named volume postgres-data
```

The browser **does not connect to PostgreSQL directly**. The browser requests an API endpoint; Flask validates the request; Psycopg sends parameterized SQL to PostgreSQL; Flask returns JSON; JavaScript refreshes the browser UI.

## 4. Python `app/app.py` — code concepts, line by line by responsibility

### 4.1 Imports and Flask creation

```python
import os
from datetime import datetime, timezone
import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request

app = Flask(__name__)
```

- **`import os`** gives access to environment variables, avoiding hardcoded database settings.
- **`datetime, timezone`** produce UTC timestamps in the liveness response.
- **`psycopg`** is the PostgreSQL client library; it sends SQL queries over database connections.
- **`dict_row`** makes SQL rows accessible as dictionaries, such as `{"id": 1, "status": "OPEN"}`, which can be returned as JSON.
- **`Flask`** creates the web application. **`jsonify`** converts Python objects to JSON responses. **`request`** provides the incoming HTTP request (including JSON bodies).
- **`Flask(__name__)`** associates the app with its Python module and helps Flask find its `templates` directory.

### 4.2 PostgreSQL connection helper

```python
def get_db_connection():
    return psycopg.connect(
        host=os.environ.get("DATABASE_HOST", "db"),
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        dbname=os.environ.get("DATABASE_NAME", "opspulse"),
        user=os.environ.get("DATABASE_USER", "opspulse"),
        password=os.environ["DATABASE_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )
```

- **`def`** introduces a reusable function. All database-dependent endpoints use this helper.
- **`os.environ.get("KEY", "default")`** reads configuration from the process environment, with a fallback if the variable is unset.
- **`db`** is the internal Docker Compose **service name**, not the Windows IP address. Docker DNS resolves `db` to the database container.
- **`int(...)`** turns the text value for port 5432 into an integer.
- **`os.environ["DATABASE_PASSWORD"]`** requires an environment variable; if it is missing, Python raises an error instead of silently using an unsafe password.
- **`connect_timeout=5`** bounds how long establishing a DB connection can take.
- **`row_factory=dict_row`** returns rows with column names.
- **`with get_db_connection() as conn:`** manages the connection transaction: successful work commits, and errors roll back.

### 4.3 Database initialization and schema

```sql
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

- **`IF NOT EXISTS`** avoids failing if this table already exists.
- **`id ... IDENTITY PRIMARY KEY`** creates an automatically generated unique numeric incident ID.
- **`title`** and **`severity`** cannot be NULL.
- **`status`** starts as **OPEN** unless explicitly supplied by the INSERT.
- **`created_at`** records the current DB timestamp with time-zone support.
- The actual `initialize_database()` function runs this statement. The current GET and POST `/incidents` endpoints call it before querying/inserting. A production system should normally use explicit database migrations instead of creating tables during request handling.

### 4.4 Routes: `@app.route`, `def`, and `return`

- **`@app.route("/")`** registers the home URL. `def home()` returns application name, version and a running message as JSON.
- **`@app.route("/health")`** returns JSON containing status `healthy`, application name and a UTC timestamp. It **does not** query PostgreSQL. HTTP 200 means Flask can respond, not that every endpoint is healthy.
- **`@app.route("/dashboard")`** renders HTML:

```python
@app.route("/dashboard")
def dashboard():
    from flask import render_template
    return render_template("dashboard.html")
```

`render_template()` looks for a file named `dashboard.html` inside `templates/` next to `app.py`. In the image that means `/app/templates/dashboard.html`. Missing that file caused the actual **HTTP 500 / TemplateNotFound** issue.

### 4.5 `POST /incidents`: create an incident

The route begins with `@app.route("/incidents", methods=["POST"])`. `POST` is used to **create a record**.

```python
data = request.get_json(silent=True)
if not isinstance(data, dict):
    return jsonify({"error": "A JSON object is required"}), 400

title = data.get("title")
severity = data.get("severity", "MEDIUM")
```

- **`get_json(silent=True)`** reads the request body as JSON without automatically raising a parse exception for malformed input.
- **`isinstance(..., dict)`** verifies the value is a JSON object containing named fields.
- **`data.get`** reads the requested title and severity; MEDIUM is the default severity.
- The code rejects an empty/whitespace-only title and invalid severity (only LOW, MEDIUM, HIGH, CRITICAL). It uses `title.strip()` and `severity.upper()` before insertion.

```sql
INSERT INTO incidents (title, severity)
VALUES (%s, %s)
RETURNING id, title, severity, status, created_at
```

**`%s`** are placeholders handled by Psycopg. The Python tuple `(title.strip(), severity.upper())` supplies values separately from SQL syntax, which helps prevent SQL injection. **`RETURNING`** fetches the newly inserted row; **`fetchone()`** obtains it; **`jsonify(incident), 201`** sends HTTP 201 Created with the record.

### 4.6 `GET /incidents`: list incidents

```sql
SELECT id, title, severity, status, created_at
FROM incidents
ORDER BY id
```

- **`SELECT`** reads the records used by the dashboard.
- **`ORDER BY id`** returns ascending IDs (older first). The browser reverses their display order.
- **`fetchall()`** gives a list of rows; **`jsonify(incidents)`** sends them as a JSON array.
- Currently this sends the full list, so for a large real-world dataset we should add filtering and pagination.

### 4.7 `GET /ready`: the database-aware readiness check

```python
@app.route("/ready")
def readiness():
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "ready", "database": "connected"}), 200
    except psycopg.OperationalError:
        app.logger.warning("Readiness check failed: PostgreSQL unavailable")
        return jsonify({"status": "not_ready", "database": "unavailable"}), 503
```

- **`try`** runs code that might fail; **`except psycopg.OperationalError`** handles common DB connectivity errors.
- **`SELECT 1`** is a quick connection test, not a query on the incidents table.
- Database reachable → **200**; caught connection failure → **503** plus a warning in logs.
- **Liveness (`/health`) ≠ readiness (`/ready`)**. It is possible for Flask to be alive while PostgreSQL is unavailable.

### 4.8 `PATCH /incidents/<int:incident_id>`: resolve or reopen

```python
@app.route("/incidents/<int:incident_id>", methods=["PATCH"])
def update_incident(incident_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400
    status = data.get("status")
    if status not in ("OPEN", "RESOLVED"):
        return jsonify({"error": "Invalid status"}), 400
    with get_db_connection() as conn:
        incident = conn.execute(
            """UPDATE incidents SET status = %s WHERE id = %s
               RETURNING id, title, severity, status, created_at""",
            (status, incident_id),
        ).fetchone()
    if incident is None:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify(incident), 200
```

- **PATCH** means modify an existing incident rather than create a new one.
- **`<int:incident_id>`** extracts a number from the URL. `/incidents/3` passes `incident_id=3` to the function.
- The route allows only status **OPEN** or **RESOLVED**, returning HTTP 400 for other values.
- **`UPDATE ... WHERE id = %s`** modifies only the specified row.
- **`RETURNING`** sends back the changed row; **`fetchone()`** returns one result or None.
- **No row found** → HTTP 404; success → HTTP 200 with JSON.
- The current application has no login, authorization or audit log. Keep it accessible only through the SSH tunnel rather than publishing it publicly.

### 4.9 Python direct execution versus Docker Gunicorn

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

This block runs when `app.py` is executed directly and starts Flask's **development** server. Compose instead starts **Gunicorn** using the Dockerfile's `CMD`. Gunicorn loads the Flask object called `app` from module `app` using `app:app`. The address `0.0.0.0` means listen on all interfaces *inside that environment/container*.

## 5. HTML: `app/templates/dashboard.html`

### 5.1 Document structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpsPulse | Incident Dashboard</title>
  <style>/* CSS rules inside this element */</style>
</head>
<body>
  <main><!-- Cards, form and incident table --></main>
  <script>/* JavaScript code inside this element */</script>
</body>
</html>
```

- **DOCTYPE** uses modern HTML parsing; **lang** specifies document language; **UTF-8** supports text characters; **viewport** makes mobile scaling work.
- **`<title>`** sets the browser tab title.
- **`<head>`** contains metadata/styles; **`<body>`** contains the visible page; **`<main>`** groups its primary content.
- The real file contains CSS between `<style>` tags and JavaScript between `<script>` tags; there are no separate `.css` or `.js` files in Day 36.

### 5.2 Dashboard cards and IDs

```html
<section class="cards">
  <div class="card"><span>Total Incidents</span><strong id="total">—</strong></div>
  <div class="card"><span>Open Incidents</span><strong id="open">—</strong></div>
  <div class="card"><span>Resolved</span><strong id="resolved">—</strong></div>
  <div class="card"><span>Critical Incidents</span><strong id="critical">—</strong></div>
</section>
```

- **`section`** groups information; **`div`** is a layout container; **`span`** labels the metric; **`strong`** holds the emphasized counter.
- **`class`** is for shared CSS styling; **`id`** uniquely identifies an element for JavaScript.
- Numbers initially show a dash; JavaScript replaces each dash with counts fetched from PostgreSQL via Flask.

### 5.3 Incident creation form

```html
<form id="incidentForm" class="form-row">
  <input id="title" placeholder="Describe the incident" maxlength="200" required>
  <select id="severity">
    <option>LOW</option><option selected>MEDIUM</option>
    <option>HIGH</option><option>CRITICAL</option>
  </select>
  <button type="submit">Create Incident</button>
</form>
<p id="message" class="status" role="status"></p>
```

- **`input`** captures the title; **`required`** prevents empty browser submission; **`maxlength`** caps browser input to 200 characters.
- **`select`** is the severity dropdown; **`selected`** chooses MEDIUM by default.
- **`button type=submit`** triggers the form's submit event.
- **`p id=message`** displays success/failure feedback; **`role=status`** provides an announcement region for assistive technologies.
- Backend validation is still necessary because clients can bypass browser-side restrictions.

### 5.4 Incident table and Actions column

```html
<table>
  <thead><tr><th>ID</th><th>Incident</th><th>Severity</th>
    <th>Status</th><th>Actions</th></tr></thead>
  <tbody id="incidentRows"></tbody>
</table>
```

- **`table`** contains rows and columns; **`thead`** has headers; **`tr`** means row; **`th`** means header cell; **`tbody`** contains data rows; **`td`** is a data cell.
- The initial `<tbody>` is empty: JavaScript creates its rows dynamically after `GET /incidents`.
- The Actions column contains a **Resolve** or **Reopen** button created by JavaScript.

## 6. CSS: explanations of the styles inside `dashboard.html`

| CSS code | Meaning |
|---|---|
| `:root` | Establishes the overall font and default dark-theme colors |
| `* { box-sizing: border-box; }` | Includes padding and borders in declared element sizes |
| `body { margin: 0; padding: 32px; }` | Removes default margin and adds page spacing |
| `main { max-width: 1100px; margin: auto; }` | Keeps the dashboard centered and readable on wide screens |
| `.cards { display: grid; ... repeat(4, ...) }` | Displays four statistic cards side by side |
| `.card, .panel` | Applies common backgrounds, borders, rounded corners and padding |
| `.form-row { display: flex; flex-wrap: wrap; }` | Lets form fields wrap when the screen is narrow |
| `input, select` | Styles title input and severity menu |
| `button` | Styles green Create/Resolve/Reopen controls |
| `th, td` | Adds table text alignment, padding and separators |
| `.table-scroll { overflow-x: auto; }` | Allows a wide table to scroll horizontally |
| `.status`, `.error` | Distinguishes regular feedback from errors |
| `@media (max-width: 760px)` | Switches cards to two columns on smaller screens |

**Analogy:** HTML is the furniture; CSS determines its color and arrangement; JavaScript makes the controls react to the user.

## 7. JavaScript: the browser-side program, explained in execution order

### 7.1 Get the feedback element

```javascript
const message = document.getElementById("message");
```

- **`document`** is the browser's Document Object Model (DOM), the live representation of HTML.
- **`getElementById()`** finds one element by its ID.
- **`const`** declares a variable whose binding is not reassigned.

### 7.2 Fetch incident records

```javascript
async function loadIncidents() {
  try {
    const response = await fetch("/incidents");
    if (!response.ok) throw new Error("Cannot retrieve incidents");
    const incidents = await response.json();
    // Update counters and create rows below...
  } catch (error) {
    message.textContent = "Unable to load incidents: " + error.message;
    message.classList.add("error");
  }
}
```

- **`async`** defines an asynchronous function; **`await`** waits for completion of `fetch()` and JSON parsing without blocking the entire browser.
- **`fetch('/incidents')`** sends a same-origin HTTP GET to the Flask API.
- **`response.ok`** checks whether HTTP status indicates success; **`throw new Error()`** sends failures to `catch`.
- **`response.json()`** converts the JSON text into an array of incident objects.
- **`catch`** displays an error message when the API is unavailable or returns a failure.

### 7.3 Calculate totals from actual incidents

```javascript
document.getElementById("total").textContent = incidents.length;
document.getElementById("open").textContent =
  incidents.filter(i => i.status === "OPEN").length;
document.getElementById("resolved").textContent =
  incidents.filter(i => i.status === "RESOLVED").length;
document.getElementById("critical").textContent =
  incidents.filter(i => i.severity === "CRITICAL").length;
```

- **`.length`** counts items in the array.
- **`.filter()`** chooses only records that match a condition.
- **`i => ...`** is an arrow function evaluated for each incident.
- **`===`** checks strict equality.
- **`.textContent`** replaces the text of a dashboard element with the calculated value.
- CRITICAL is a **severity**, whereas OPEN/RESOLVED are **statuses**; a critical incident can be resolved and still count as critical.
- Counts are calculated from the API response in the browser, rather than by SQL `COUNT()` queries.

### 7.4 Build the incident table

```javascript
const tbody = document.getElementById("incidentRows");
tbody.replaceChildren();
for (const incident of [...incidents].reverse()) {
  const row = document.createElement("tr");
  for (const value of [incident.id, incident.title, incident.severity, incident.status]) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  }
  // The actual code then adds the Resolve/Reopen button.
  tbody.appendChild(row);
}
```

- **`replaceChildren()`** clears previous rows so they are not duplicated when reloading data.
- **`[...incidents]`** copies an array; **`.reverse()`** displays newest IDs first without mutating the original array.
- **`for...of`** loops over each incident.
- **`createElement()`** creates HTML elements, while **`appendChild()`** puts them in the page.
- **`cell.textContent = value`** treats incident titles as plain text instead of parsing them as HTML (safer than `innerHTML`).

### 7.5 Resolve/Reopen click handler

```javascript
const isResolved = incident.status === "RESOLVED";
button.textContent = isResolved ? "Reopen" : "Resolve";
button.addEventListener("click", async () => {
  button.disabled = true;
  const newStatus = isResolved ? "OPEN" : "RESOLVED";
  try {
    const response = await fetch(`/incidents/${incident.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (!response.ok) throw new Error("Failed to update incident");
    await loadIncidents();
    message.textContent = `Incident #${incident.id} updated to ${newStatus}`;
    message.classList.remove("error");
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  } finally {
    button.disabled = false;
  }
});
```

- **`isResolved`** is true when the incident status is RESOLVED.
- **`? :`** is the ternary operator: a short form of if/else.
- **`addEventListener('click', ...)`** registers the function to run when someone presses the button.
- **`button.disabled = true`** prevents repeated clicks while the request is in progress.
- **`${incident.id}`** and **`${newStatus}`** inside a JavaScript backtick string insert dynamic values (template literals).
- **`method: 'PATCH'`** changes an existing incident by calling Flask.
- **`JSON.stringify()`** serializes a JavaScript object into a JSON request body.
- **`Content-Type: application/json`** tells Flask the body format.
- **`await loadIncidents()`** retrieves fresh data and recalculates the UI immediately after success.
- **`finally`** enables the clicked button even if the request fails.

### 7.6 Submit Create Incident form

```javascript
document.getElementById("incidentForm").addEventListener("submit", async event => {
  event.preventDefault();
  const response = await fetch("/incidents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: document.getElementById("title").value,
      severity: document.getElementById("severity").value
    })
  });
  // Actual handler also checks response.ok, handles errors,
  // resets the form, refreshes incidents and displays feedback.
});
```

- **`submit`** is the form event; **`event.preventDefault()`** prevents a normal page-reloading browser submission.
- **`.value`** reads typed/selected values from HTML controls.
- **POST** creates a new incident via Flask and PostgreSQL.
- The actual handler checks the response, calls `form.reset()` after success, then `await loadIncidents()` and shows the feedback message.
- **`loadIncidents()`** at the end of the file runs once on page load.
- The current UI is **refresh-on-action**, not an automatically streaming or polling dashboard.

## 8. Dockerfile: explain every Docker image instruction

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ ./templates/
RUN useradd --create-home --uid 10001 opspulse
USER opspulse
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).close()" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
```

| Instruction | What happens |
|---|---|
| `FROM python:3.13-slim` | Start with the official Python 3.13 slim base image |
| `WORKDIR /app` | Set the working directory inside Docker |
| `COPY requirements.txt .` | Copy dependency list to the image |
| `RUN pip install --no-cache-dir ...` | Install dependencies in image without keeping download cache |
| `COPY app.py .` | Copy Flask Python backend into `/app` |
| `COPY templates/ ./templates/` | Copy HTML into `/app/templates` — the Day 36 fix |
| `RUN useradd ... opspulse` | Create a non-root runtime user |
| `USER opspulse` | Run app as the non-root user |
| `EXPOSE 8080` | Document image's listening port, but does not publish it on host |
| `HEALTHCHECK ... /health` | Periodically check whether Flask responds; does not check PostgreSQL readiness |
| `CMD ... gunicorn` | Start a Gunicorn WSGI server with two workers on container port 8080 |

The Docker image must be **rebuilt** after adding the new HTML template. An image is not synchronized live with host source code.

## 9. `.dockerignore`: why we exclude these files

| Pattern | Explanation |
|---|---|
| `.venv/`, `venv/` | Do not copy Debian2's local Python virtual environment into Docker |
| `__pycache__/`, `*.pyc` | Exclude generated Python bytecode |
| `*.log`, `logs/` | Exclude runtime log files |
| `.env`, `.env.*` | Exclude environment files containing possible secrets |
| `*.pem`, `*.key` | Avoid adding private keys/certificates to image build context |
| `.git/` | Exclude Git history and metadata |

The Python environment on Debian2 (`source app/.venv/bin/activate`) is **separate** from the Python packages installed inside the image.

## 10. `requirements.txt`: why these packages exist

```text
Flask==3.1.3
gunicorn>=23,<24
psycopg[binary]>=3.2,<4
```

- **Flask** provides routing, HTTP requests/responses and HTML template rendering; `==` pins the exact Flask version.
- **Gunicorn** serves the Python WSGI application with worker processes; `>=23,<24` allows compatible releases in major version 23.
- **Psycopg with binary extra** lets Flask talk to PostgreSQL; `>=3.2,<4` allows versions from 3.2 up to (but not including) 4.
- More reproducible production builds would pin transitive dependencies using a lockfile.

## 11. Docker Compose YAML: explain all important lines

```yaml
name: opspulse-day33
services:
  app:
    build:
      context: ../app
    ports:
      - "127.0.0.1:8082:8080"
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_HOST: db
      DATABASE_PORT: "5432"
      DATABASE_NAME: opspulse
      DATABASE_USER: opspulse
      DATABASE_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}
    networks:
      - opspulse-network
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: opspulse
      POSTGRES_USER: opspulse
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U opspulse -d opspulse"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - opspulse-network
networks:
  opspulse-network:
volumes:
  postgres-data:
```

- **`name`** sets a predictable Compose project prefix.
- **`services`** defines the two containers: `app` and `db`.
- **`build.context: ../app`** points Docker at the Flask source directory and Dockerfile.
- **`127.0.0.1:8082:8080`** is `HOST_IP:HOST_PORT:CONTAINER_PORT`. The app is available on Debian2's loopback address, not publicly exposed to the LAN.
- **`depends_on` with `service_healthy`** delays starting Flask until the database health check passes during Compose startup; it does not prevent future database failures.
- **`environment`** injects database settings that `get_db_connection()` reads.
- **`${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}`** is Compose variable interpolation that requires a supplied password; do not commit the real password.
- **`networks: opspulse-network`** connects both containers over an internal Docker network; Flask uses hostname **db** rather than localhost to find PostgreSQL.
- **`postgres:17-alpine`** uses PostgreSQL 17 in an Alpine-based image.
- **`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`** configure initial database creation on an empty data volume.
- **`postgres-data:/var/lib/postgresql/data`** is the named volume that stores PostgreSQL data outside the container's disposable writable layer.
- **`pg_isready`** checks whether PostgreSQL accepts connections; **`interval`, `timeout`, `retries`** configure health-check timing.
- The **db service has no published host port**, so it is reached only through the Compose network.

## 12. Day 36 commands in chronological order

### Activate existing Python venv

```bash
cd ~/winter-arc-integration-project
source app/.venv/bin/activate
which python
python --version
python -m pip show Flask
```

### Recover stopped app and database services

```bash
cd ~/winter-arc-integration-project/day33-compose
docker ps -a
docker compose up -d
docker compose ps
curl -i --max-time 5 http://127.0.0.1:8082/health
curl -i --max-time 5 http://127.0.0.1:8082/ready
curl -sS --max-time 5 http://127.0.0.1:8082/incidents
```

### Inspect and fix outdated image `/ready` 404

```bash
grep -n -A 10 '@app.route("/ready")' ../app/app.py
docker compose up -d --build --no-deps app
curl -i http://127.0.0.1:8082/ready
```

### Create dashboard and route; verify Python

```bash
cd ~/winter-arc-integration-project
mkdir -p app/templates
# Create app/templates/dashboard.html with HTML/CSS/JavaScript described above.
# Add GET /dashboard to app/app.py.
python -m py_compile app/app.py
ls -lh app/templates/dashboard.html
```

### Diagnose and fix dashboard HTTP 500

```bash
cd ~/winter-arc-integration-project/day33-compose
docker compose logs --tail=50 app
docker compose exec app ls -lh /app/templates/
cat ../app/Dockerfile
cat ../app/.dockerignore
# Add COPY templates/ ./templates/ in app/Dockerfile.
docker compose up -d --build --no-deps app
docker compose exec app ls -lh /app/templates/
curl -I http://127.0.0.1:8082/dashboard
```

### Test new incident and resolution

```bash
curl -sS http://127.0.0.1:8082/incidents
curl -i -X PATCH http://127.0.0.1:8082/incidents/3 \
  -H 'Content-Type: application/json' \
  -d '{"status":"RESOLVED"}'
```

In the browser, use the Create Incident form and Resolve/Reopen buttons. For Windows access, use PuTTY **Connection → SSH → Tunnels**, `Local` source `8082`, destination `127.0.0.1:8082`, then open `http://127.0.0.1:8082/dashboard` while the SSH session is connected.

### Validate Git changes

```bash
cd ~/winter-arc-integration-project
git diff --check
git status --short
git diff --cached --check
git log -1 --oneline
```

Day 36 commit **8d4900e** was reported synchronized with origin/main. This study guide is a subsequent documentation update and requires a separate commit if copied into the repo.

## 13. Troubleshooting and production lessons

| Symptom | Root cause | Evidence | Fix |
|---|---|---|---|
| `/ready` HTTP 404 | Running image was older than Flask source | Source had `/ready`, container lacked route | Rebuild app image with `docker compose up -d --build --no-deps app` |
| `/dashboard` HTTP 500 | HTML template missing from image | Flask logs showed `jinja2.exceptions.TemplateNotFound: dashboard.html`; `/app/templates/` absent | Add `COPY templates/ ./templates/` and rebuild |
| DB incidents unavailable while Flask `/health` healthy | App is alive but DB dependency can be unavailable | Day 33 controlled outage and DB errors | Inspect DB logs, DNS, Compose network and `/ready` |
| Dashboard works in Debian2 but Windows cannot connect | Port 8082 bound to Debian2 loopback only | Compose port mapping `127.0.0.1:8082:8080` | Use local SSH port forwarding through PuTTY |

**Production troubleshooting exercise:** Flask container is healthy but `/dashboard` returns 500. Inspect `docker compose logs --tail=50 app`, check `/app/templates`, inspect Dockerfile COPY rules, rebuild only the app, then check `/dashboard`, `/ready` and `/incidents`. A healthy health-check is not sufficient to declare every feature functional.

## 14. Interview questions with answers

**Q1. Docker image versus container?** An image is an immutable build artifact; a container is a running instance of the image. Editing source on the host does not change an existing image.

**Q2. Why did `/dashboard` fail while `/health` passed?** The web process was alive, but the HTML template was missing inside the image, causing `TemplateNotFound` for the dashboard route.

**Q3. What does SQL `WHERE id = %s` accomplish?** It selects only the requested incident for update; `%s` is safely parameterized by Psycopg.

**Q4. POST versus PATCH?** POST creates a new incident, while PATCH changes status on an existing incident.

**Q5. Why use a PostgreSQL named volume?** It stores database files independently of Flask container rebuilds, preserving incident records.

**Q6. How do liveness and readiness differ?** `/health` shows the Flask process responds; `/ready` confirms DB connectivity using `SELECT 1`.

**Q7. Why `127.0.0.1:8082:8080`?** It publishes container port 8080 only on Debian2's loopback port 8082; SSH port forwarding grants browser access without exposing a public listener.

**Q8. Why use `textContent` in JavaScript?** It inserts incident titles as text rather than interpreting potentially unsafe HTML markup.

**Q9. Why does a fresh page fetch `/incidents`?** The HTML starts with empty table/counter placeholders; JavaScript obtains live persisted values from Flask and fills the page.

**Q10. How does Docker Compose find the database?** Both services join `opspulse-network`, and internal DNS resolves the Compose service hostname `db` to the PostgreSQL container.

## 15. Current limitations and future improvements

The Day 36 dashboard is working but is not a fully production-ready incident system. It does not yet have authentication/authorization, audit history, paginated API results, schema migrations, separate automated API/frontend tests, server-side metric aggregation, or continuous browser refresh. Prometheus, Grafana and automated GitHub-to-deployment pipelines are future integration milestones. AWS Day 35 was architecture design, **not** a running AWS application deployment.

**Revision technique:** For each Create/Resolve/Reopen action, trace (1) the HTML control → (2) JavaScript event/fetch → (3) Flask route → (4) PostgreSQL SQL statement → (5) JSON response → (6) dashboard refresh.
