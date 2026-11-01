# Traffic Tracker

This project collects live traffic observations around Kolkata, from Mapbox and TomTom.
It keeps the existing monthly CSV files as a local backup and can also persist observations to
MongoDB Atlas for historical analysis.

## MongoDB Atlas setup

Create a MongoDB Atlas cluster and database user, then add a `.env` file in the project directory:

```text
MAPBOX_TOKEN=your_mapbox_token
TOMTOM_KEY=your_tomtom_key
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=jadavpur_traffic
```

In Atlas, add the machine's IP address to the project's network access list. Do not commit the
`.env` file or share the connection string.

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Hourly collection

For the seven-day study, run these two commands once every hour:

```powershell
python check_coverage.py
python check_incidents.py
```

`check_coverage.py` stores Mapbox and TomTom route observations plus TomTom point-flow
observations. `check_incidents.py` stores both individual incidents and an incident-run record,
including runs where TomTom reports zero incidents. The existing `traffic_snapshot.py` command
also writes primary Mapbox snapshots, but it is not needed in the hourly job because
`check_coverage.py` already includes those routes.

The MongoDB collections are:

| Collection | Contents |
|---|---|
| `coverage_route_snapshots` | Mapbox/TomTom measurements for primary and candidate routes |
| `point_snapshots` | TomTom speed, free-flow speed, confidence, and road matching |
| `incident_snapshots` | Individual incident records |
| `incident_runs` | One record per collection run, including `incident_count = 0` |
| `route_snapshots` | Primary Mapbox snapshots from the optional `traffic_snapshot.py` command |

Every document contains the original `run_time_ist` and a timezone-aware `observed_at` field.
Indexes are created on time and route/point names so historical queries remain practical.

## Scheduling with GitHub Actions

The repository includes `.github/workflows/log_traffic.yml`. It runs hourly and can also be
started manually from the **Actions** tab. GitHub-hosted runners run in UTC; the configured
`30 * * * *` schedule corresponds to approximately every hour at minute `00` in India Standard
Time. GitHub may delay scheduled jobs by a few minutes.

Add these repository secrets under **Settings → Secrets and variables → Actions → New repository
secret**:

| Secret | Value |
|---|---|
| `MAPBOX_TOKEN` | Your Mapbox access token |
| `TOMTOM_KEY` | Your TomTom API key |
| `MONGODB_URI` | Your MongoDB Atlas connection string |
| `MONGODB_DATABASE` | `jadavpur_traffic` |

The workflow runs `check_coverage.py` and `check_incidents.py`, so it stores route, point-flow, and
incident data in Atlas. It no longer commits generated CSV files back to GitHub; Atlas is the
historical store and the CSV files remain a local backup when running locally.

## Scheduling on Windows

Use Windows Task Scheduler to run the commands hourly. The simplest approach is to create one
task for each command, set the trigger to repeat every 1 hour for the duration of the study, and
set the action's working directory to this project folder. Use the same Python interpreter where
`pymongo` was installed.

After seven days, the dataset will contain approximately 168 hourly collection runs for each
scheduled command. If one run fails, the next run remains independent and can continue collecting
data.

## Historical analysis

MongoDB Compass or an analysis script can query a seven-day window using `observed_at`, for example:

```javascript
db.coverage_route_snapshots.find({
  observed_at: {
    $gte: ISODate("2026-11-01T00:00:00+05:30"),
    $lt: ISODate("2026-11-08T00:00:00+05:30")
  },
  route_name: "Jadavpur_Stn_to_8B"
}).sort({ observed_at: 1 })
```

This makes it possible to study hourly congestion patterns, compare providers, calculate average
and peak travel times, and correlate traffic with incidents.

## GitHub checks

The `.github/workflows/ci.yml` workflow runs on every push and pull request. It:

- Installs the dependencies from `requirements.txt`.
- Checks that installed dependencies are consistent.
- Compiles all Python files to catch syntax errors.
- Imports the project configuration and verifies that routes, points, timezone, and MongoDB
  collection mappings are present.

These checks do not call Mapbox, TomTom, or MongoDB, so they do not require secrets and are safe
to run on pull requests. The separate `Log Traffic` workflow uses the repository secrets and runs
only on its hourly schedule or when manually triggered.