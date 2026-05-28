# PNW Picker

Play & Win prize picker for Geekway to the West. It pulls game copies and plays from the [`ruleslawyer-backend`](https://github.com/geekwaytothewest/ruleslawyer-backend) library API, filters down to eligible plays, randomly selects winners for each awardable game copy, and produces winner lists and printable labels.

A standalone Python tool — not part of the Docker stack — that ships with a [Gooey](https://github.com/chriskiehl/Gooey) GUI but can also run headless from the command line.

## How it works

1. Loads game copies and plays (from the API, or from local JSON files with `--local`).
2. Keeps only awardable Play & Win copies and eligible plays (filtering out plays outside the allowed duration and players who don't want to win or are on the ineligible list).
3. Awards each copy a winner using one of two methods:
   - **`old_school`** — shuffle the plays, then pick one eligible player per play until all copies are awarded (falls back to `standard` if it runs out of plays).
   - **`standard`** — pick winners weighted by number of plays (more plays = more chances).
4. Writes the winners, printable labels, and any unawarded games to files.

## Requirements

- [Anaconda/Miniconda](https://www.anaconda.com/) (Python 3.12)
- Auth0 credentials with access to the Rules Lawyer API
- Python packages: `pylabels`, `reportlab`, `requests`, `gooey`

## Setup

Create and activate a conda environment named `pnw`:

```bash
conda create -n pnw python=3.12
conda env create -f environment.yaml   # installs from conda_packages.txt
conda activate pnw
pip install pylabels reportlab requests gooey
```

See [`Anaconda Setup.txt`](Anaconda%20Setup.txt) for OS-specific notes (Ubuntu, Arch, macOS).

Create the output directories if they don't already exist:

```bash
mkdir -p data log
```

## Configuration

Authentication uses the Auth0 `client_credentials` grant. Copy `.env.example` to `.env` and fill in:

| Variable             | Description                  |
| -------------------- | ---------------------------- |
| `AUTH0_CLIENT_ID`    | Auth0 machine-to-machine client ID |
| `AUTH0_CLIENT_SECRET`| Auth0 machine-to-machine client secret |

The code reads these from the environment (it does **not** auto-load `.env`), so export them into your shell before running, e.g.:

```bash
set -a; source .env; set +a
```

## Usage

Running the tool launches the Gooey GUI:

```bash
python pnw_picker.py
```

To run headless from the command line, pass `--ignore-gooey` along with the arguments:

```bash
python pnw_picker.py --ignore-gooey winners --method old_school --ineligible_players_fn staff.tsv
```

### Arguments

| Argument                    | Description                                                        |
| --------------------------- | ----------------------------------------------------------------- |
| `output_fn_prefix`          | (required) prefix for the output filenames                        |
| `--method`                  | `old_school` or `standard`                                         |
| `--ineligible_players_fn`   | TSV of `ID, Player Name` to exclude (e.g. staff and family)       |
| `--duration_min`            | minimum play duration in minutes for a play to count              |
| `--duration_max`            | maximum play duration in minutes for a play to count              |
| `--local`                   | read from local JSON files instead of the API                     |
| `-g`, `--games_source`      | local games JSON (used with `--local`)                            |
| `-p`, `--plays_source`      | local plays JSON (used with `--local`)                            |

### Outputs

Files are named `<prefix>.<suffix>.<ext>`, where `<suffix>` is a timestamp unless you supply one.

- `<prefix>.<suffix>.tsv` — winners and the games they won, sorted by winner name
- `<prefix>.<suffix>.pdf` — labels to stick on the won games (Avery 6460), sorted by game name
- `<prefix>.<suffix>.unawarded.tsv` — plays for games that couldn't be fully awarded
- `data/games.<suffix>.json`, `data/plays.<suffix>.json` — raw API responses (API mode only)
- `log/*.tsv` — debug dumps (all games, P&W games, awardable plays, filtered plays)

## Layout

- `pnw_picker.py` — entry point: winner selection logic and CLI/GUI
- `pnw.py` — data model (`Game`, `Copy`, `GameCheckout`, `Win`) and parsing/output helpers
- `pnw_api.py` — Auth0 authentication and Rules Lawyer API requests
- `create_mock_plays.py` — generates mock plays for testing
- `test_pnw.py`, `test_requests.py` — unit tests
- `SQL Scripts/` — analytics queries against the database (play stats, hoarding reports, etc.)
- `Random Scripts/` — one-off analysis utilities (BGG comparisons, checkout-over-time)

## Tests

```bash
python -m unittest test_pnw.py
```

## License

Licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE).
