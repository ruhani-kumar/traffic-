# Traffic Tracker

Collects live traffic around Jadavpur, Kolkata, from TomTom every 15 minutes and stores it in
MongoDB Atlas for historical analysis. Monthly CSV files are written as a backup.

## What one run collects

`python traffic_snapshot.py` makes 15 TomTom requests at most and saves:

| MongoDB collection | Contents | How often |
|---|---|---|
| `route_snapshots` | 8 routes: live, usual and empty-road time, delay, Travel Time Index, speed | Every run |
| `location_snapshots` | 6 points: current vs normal speed, confidence, road closed | Every run |
| `incident_summaries` | Counts of jams, closures, accidents, road works, total delay | Every run |
| `incident_snapshots` | Full list of incidents in the area | Once an hour |
| `raw_responses` | TomTom's complete JSON reply, with `response_ms` and `response_kb` | Routes and points every run; incidents once an hour |

Every document has `run_time_ist` and a timezone-aware `observed_at`, plus weekday, weekend,
holiday and weather (Open-Meteo). If the weather service is down, those fields are left empty.

Routes, points and the incident search area are set in `config.py`. Add West Bengal festival days
to `FESTIVAL_DAYS` there.

## Setup on a laptop

Create a `.env` file in the project folder. Do not commit it or share the connection string.

```text
TOMTOM_KEY=your_tomtom_key
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
MONGODB_DATABASE=traffic-tracker
MAPBOX_TOKEN=your_mapbox_token
```

`MAPBOX_TOKEN` is only needed for the comparison tools below. In Atlas, the machine's IP address
must be allowed under Network Access.

```powershell
pip install -r requirements.txt
python traffic_snapshot.py
```

## Automatic collection

`.github/workflows/log_traffic.yml` runs `traffic_snapshot.py` on GitHub. GitHub's own schedule is
unreliable (it ran about 6 times a day here, not 96), so it is only an hourly backup. The 15-minute
runs are started by cron-job.org, which calls GitHub's `workflow_dispatch` API. A backup run can land
close to a 15-minute run, so remove near-duplicate runs during analysis.

Repository secrets (**Settings > Secrets and variables > Actions**): `TOMTOM_KEY`, `MONGODB_URI`,
`MONGODB_DATABASE`.

If a run cannot save to MongoDB, or every route fails, the run shows as failed and its CSV files are
kept as a downloadable artifact on that run's page.

## Comparison and checking tools

These are run by hand and are not part of the automatic job.

| Command | What it does |
|---|---|
| `python check_coverage.py` | Compares Mapbox and TomTom on the final routes; saves to `coverage_route_snapshots` and `point_snapshots` |
| `python check_coverage.py --summary` | Gives a verdict per road from all saved test runs |
| `python check_routes.py` | Draws routes, points and incidents on `maps/routes_map.html` |
| `python check_incidents.py` | Lists current incidents; saves to `incident_snapshots` and `incident_runs` |

## Historical analysis

MongoDB Compass or a script can query a time window using `observed_at`:

```javascript
db.route_snapshots.find({
  observed_at: {
    $gte: ISODate("2026-11-02T00:00:00+05:30"),
    $lt: ISODate("2026-11-09T00:00:00+05:30")
  },
  route_name: "RSC_Mullick_Gariahat_to_Jadavpur"
}).sort({ observed_at: 1 })
```

## GitHub checks

`.github/workflows/ci.yml` runs on every push and pull request. It installs the dependencies,
compiles all Python files, and checks that routes, points, timezone and MongoDB collections are
configured. It does not call TomTom or MongoDB, so it needs no secrets.
