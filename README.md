# Business Scraper

A Python scraper that searches Google Maps by business category
and location, visits each company website to look for public email addresses,
and exports the results to a CSV file.

You can use it from a web interface (Streamlit) or from the command line.

## Requirements

- Windows with PowerShell (the commands below are written for PowerShell)
- Python 3.13 or newer
- An internet connection
- About 2 GB of free disk space for the Python packages and Chromium browser

Check your Python version:

```powershell
python --version
```

## Installation

Run these commands from the project folder.

**1. Create a virtual environment**

```powershell
python -m venv .venv
```

**2. Install the Python packages**

```powershell
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Install a compatible version of selectolax**

This step is required. The app does not start with selectolax 1.0 or newer,
which is the version step 2 installs.

```powershell
.venv\Scripts\python.exe -m pip install "selectolax<1"
```

**4. Install the Chromium browser**

```powershell
.venv\Scripts\python.exe -m playwright install chromium
```

**5. Confirm the installation**

```powershell
.venv\Scripts\python.exe -c "import app.main; print('Installation OK')"
```

You should see `Installation OK`.

## Run the web interface

```powershell
.venv\Scripts\python.exe -m streamlit run app/ui.py
```

The app opens in your browser at <http://localhost:8501>. If it does not open
by itself, paste that address into your browser.

1. Enter a **Business category**, such as `dentist`.
2. Enter a **Location**, such as `Dallas, TX`.
3. Set **Max Google Maps results** (5 to 200) and **Concurrency** (1 to 10).
4. Click **Run scraper**.
5. When the run finishes, review the table and click **Download CSV**.

Press `Ctrl+C` in the terminal to stop the app.

## Run from the command line

```powershell
.venv\Scripts\python.exe -m app.main "dentist" "Dallas, TX"
```

The category and location are required. These options are available:

| Option | Description | Default |
| --- | --- | --- |
| `--output <path>` | CSV file to write to | `output/results.csv` |
| `--concurrency <n>` | Number of businesses processed at the same time | `5` |

Example:

```powershell
# Save to a specific file and process 3 businesses at a time
.venv\Scripts\python.exe -m app.main "dentist" "Dallas, TX" --output output/dentists.csv --concurrency 3
```

## Deploy to Vercel

The Vercel version runs the Google Maps scraper and Chromium in a container
(`Dockerfile.vercel`). It works differently from the local app:

- Each search returns up to 50 businesses and stops after about 4 minutes.
- Each server instance runs one search at a time.
- Results are downloaded from the page and are not saved on the server.
- Google Maps may block searches from cloud servers.

Log in and create a preview deployment:

```powershell
npx vercel login
npx vercel
```

When the preview works, publish it to production:

```powershell
npx vercel --prod
```

The deployed page is public, so anyone with the link can run searches.

## Configuration (optional)

The app works without any configuration. To change a default, create a file
named `.env` in the project folder and add the settings you want:

```env
HEADLESS=false
GOOGLE_MAPS_MAX_RESULTS=30
LOG_LEVEL=DEBUG
```

| Setting | Description | Default |
| --- | --- | --- |
| `GOOGLE_MAPS_MAX_RESULTS` | Maximum Google Maps results | `60` |
| `CONCURRENCY` | Number of businesses processed at the same time | `5` |
| `HEADLESS` | `true` hides the browser window, `false` shows it | `true` |
| `USER_AGENT` | Browser user agent | Chrome on Windows |
| `BROWSER_TIMEOUT_MS` | Browser timeout in milliseconds | `30000` |
| `HTTP_TIMEOUT_SEC` | Website request timeout in seconds | `15.0` |
| `REQUEST_DELAY_SEC` | Delay between requests in seconds | `1.0` |
| `EMAIL_FLUSH_SIZE` | Rows held in memory before writing to the CSV | `25` |
| `OUTPUT_DIR` | Folder for CSV files | `output` |
| `LOGS_DIR` | Folder for log files | `logs` |
| `LOG_LEVEL` | Console log detail, such as `INFO` or `DEBUG` | `INFO` |

## Output

CSV files contain these columns:

`Company Name, Phone, Website, Email, Address, Source, Source URL`

- The web interface creates a new file for each run: `output/results_<timestamp>.csv`.
- The command line adds rows to `output/results.csv`, so results from earlier
  runs stay in the file. Use `--output` to keep a run separate.
- Logs are saved in the `logs` folder and kept for 7 days.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `ImportError: Modest backend is deprecated` | Run `.venv\Scripts\python.exe -m pip install "selectolax<1"`. |
| `Executable doesn't exist` when a run starts | Run `.venv\Scripts\python.exe -m playwright install chromium`. |
| `No module named streamlit` or another missing module | Repeat installation steps 2 and 3, and start the app with `.venv\Scripts\python.exe`. |
| Port 8501 is already in use | Add `--server.port 8502` to the Streamlit command, then open <http://localhost:8502>. |
| Google Maps returns no results | Google may be showing a consent or bot check. Set `HEADLESS=false` to watch the browser, or try again later. |

## Project structure

```text
app/
├── main.py       Command-line entry point and scraping pipeline
├── ui.py         Streamlit web interface
├── config.py     Settings loaded from .env
├── schemas.py    Business data model
├── scraper/      Google Maps and browser code
├── crawler/      Website crawling and email extraction
├── exporter/     CSV export
└── utils/        Logging, retries, URLs, and helpers
output/           Generated CSV files
logs/             Generated log files
```
