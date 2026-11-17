"""
Daily run history manager.
Saves snapshots of machine data; last run of each day is the official record.
Auto-saves on each app load so every day has a record automatically.
Data stored as JSON files in data/history/{area_key}_{YYYY-MM-DD}.json
"""
import os, json, datetime
import pandas as pd


def _history_dir(base: str) -> str:
    d = os.path.join(base, "data", "history")
    os.makedirs(d, exist_ok=True)
    return d


def save_run(base: str, area_key: str, df: pd.DataFrame, label: str = "manual"):
    """
    Save current run snapshot for today.
    Each call overwrites any earlier run today (last-run-wins per day).
    label: 'auto' for automatic saves, 'manual' for user-clicked saves.
    """
    today = datetime.date.today().isoformat()
    hdir  = _history_dir(base)
    fpath = os.path.join(hdir, f"{area_key}_{today}.json")
    record = {
        "area":      area_key,
        "date":      today,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "label":     label,
        "data":      df.to_dict(orient="records"),
    }
    with open(fpath, "w") as f:
        json.dump(record, f)


def auto_save_if_needed(base: str, area_key: str, df: pd.DataFrame):
    """
    Auto-save today's state if no save exists yet for today.
    Call this on every page load so each working day is captured automatically.
    """
    today = datetime.date.today().isoformat()
    hdir  = _history_dir(base)
    fpath = os.path.join(hdir, f"{area_key}_{today}.json")
    if not os.path.exists(fpath):
        save_run(base, area_key, df, label="auto")


def list_dates(base: str, area_key: str) -> list[dict]:
    """
    Return list of dicts: [{date, label, timestamp, is_today}]
    sorted newest first.
    """
    hdir = _history_dir(base)
    entries = []
    today = datetime.date.today().isoformat()
    for fname in os.listdir(hdir):
        if fname.startswith(area_key + "_") and fname.endswith(".json"):
            date_str = fname[len(area_key)+1:-5]
            try:
                fpath = os.path.join(hdir, fname)
                with open(fpath) as f:
                    rec = json.load(f)
                ts    = rec.get("timestamp", "")
                lbl   = rec.get("label", "manual")
                entries.append({
                    "date":       date_str,
                    "timestamp":  ts,
                    "label":      lbl,
                    "is_today":   date_str == today,
                })
            except Exception:
                entries.append({"date": date_str, "timestamp": "", "label": "?", "is_today": date_str == today})
    return sorted(entries, key=lambda e: e["date"], reverse=True)


def load_run(base: str, area_key: str, date_str: str) -> pd.DataFrame | None:
    """Load the saved run for a specific date. Returns None if not found."""
    hdir  = _history_dir(base)
    fpath = os.path.join(hdir, f"{area_key}_{date_str}.json")
    if not os.path.exists(fpath):
        return None
    with open(fpath) as f:
        record = json.load(f)
    return pd.DataFrame(record["data"])
