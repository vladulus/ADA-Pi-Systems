import os
import time
import json
from datetime import datetime, timedelta
import shutil


class StorageManager:
    """
    ADA-Pi Storage System
    =====================

    Handles:
      - Daily / weekly / monthly / yearly tacho logs
      - Upload metadata tracking
      - Log rotation
      - Temporary files
      - OTA downloads
      - Cloud snapshot creation
    """

    BASE_DIR = "/opt/ada-pi/data"

    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    TACHO_DIR = os.path.join(BASE_DIR, "tacho")
    OTA_DIR = os.path.join(BASE_DIR, "ota")
    TMP_DIR = os.path.join(BASE_DIR, "tmp")

    META_FILE = os.path.join(TACHO_DIR, "upload_status.json")

    # rotation rules
    DAILY_MAX_AGE = 30          # days
    WEEKLY_MAX_AGE = 90         # days
    MONTHLY_MAX_AGE = 365       # days
    YEARLY_MAX_AGE = 99999      # never delete

    def __init__(self):
        self._ensure_directories()
        self.meta = self._load_meta()

    # ------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------

    def _load_meta(self):
        if not os.path.exists(self.META_FILE):
            return {"daily": {}, "weekly": {}, "monthly": {}, "yearly": {}}

        try:
            with open(self.META_FILE, "r") as f:
                return json.load(f)
        except:
            return {"daily": {}, "weekly": {}, "monthly": {}, "yearly": {}}

    def _save_meta(self):
        with open(self.META_FILE, "w") as f:
            json.dump(self.meta, f, indent=2)

    def mark_uploaded(self, category, filename):
        self.meta.setdefault(category, {})[filename] = True
        self._save_meta()

    def is_uploaded(self, category, filename):
        return self.meta.get(category, {}).get(filename, False)

    # ------------------------------------------------------------
    # DIRECTORIES
    # ------------------------------------------------------------

    def _ensure_directories(self):
        for d in [
            self.BASE_DIR,
            self.LOGS_DIR,
            self.TACHO_DIR,
            self.TMP_DIR,
            self.OTA_DIR,
        ]:
            os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------
    # DAILY LOGGING
    # ------------------------------------------------------------

    def save_tacho_snapshot(self, data: dict):
        """
        Save tacho data to DAILY log CSV.
        """
        date = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(self.TACHO_DIR, f"{date}.csv")

        header = (
            "timestamp,latitude,longitude,speed_kmh,"
            "rpm,obd_speed,temp_coolant\n"
        )

        # create new file with header
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                f.write(header)

        line = (
            f"{int(time.time())},"
            f"{data.get('lat')},"
            f"{data.get('lon')},"
            f"{data.get('speed')},"
            f"{data.get('rpm')},"
            f"{data.get('obd_speed')},"
            f"{data.get('coolant_temp')}\n"
        )

        with open(filename, "a") as f:
            f.write(line)

        return filename

    # ------------------------------------------------------------
    # LISTING LOGS
    # ------------------------------------------------------------

    def get_daily_logs(self):
        return sorted([f for f in os.listdir(self.TACHO_DIR) if f.endswith(".csv")])

    def get_weekly_logs(self):
        return sorted([f for f in os.listdir(self.TACHO_DIR) if f.startswith("week_")])

    def get_monthly_logs(self):
        return sorted([f for f in os.listdir(self.TACHO_DIR) if f.startswith("month_")])

    def get_yearly_logs(self):
        return sorted([f for f in os.listdir(self.TACHO_DIR) if f.startswith("year_")])

    # ------------------------------------------------------------
    # HELPER: APPEND CSV FILE INTO ANOTHER
    # ------------------------------------------------------------

    def _append_csv(self, source, dest):
        with open(dest, "a") as out, open(source, "r") as src:
            next(src)  # skip header
            for line in src:
                out.write(line)

    # ------------------------------------------------------------
    # ROTATION: DAILY → WEEKLY
    # ------------------------------------------------------------

    def rotate_daily_to_weekly(self):
        """
        Creates a weekly CSV based on ISO week numbers.
        Example: week_2025-W07.csv
        """
        daily_logs = self.get_daily_logs()

        for file in daily_logs:
            date_str = file.replace(".csv", "")
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                continue

            iso_year, iso_week, _ = date_obj.isocalendar()
            weekly_filename = f"week_{iso_year}-W{iso_week:02d}.csv"
            weekly_path = os.path.join(self.TACHO_DIR, weekly_filename)

            # create weekly file with header if not exists
            if not os.path.exists(weekly_path):
                with open(weekly_path, "w") as f:
                    f.write("timestamp,latitude,longitude,speed_kmh,rpm,obd_speed,temp_coolant\n")

            # append content
            daily_path = os.path.join(self.TACHO_DIR, file)
            self._append_csv(daily_path, weekly_path)

    # ------------------------------------------------------------
    # ROTATION: WEEKLY → MONTHLY
    # ------------------------------------------------------------

    def rotate_weekly_to_monthly(self):
        weekly_logs = self.get_weekly_logs()

        for file in weekly_logs:
            # parse ISO week file name
            try:
                _, year_week = file.split("_")
                year_str, week_str = year_week.replace(".csv", "").split("-W")
                year = int(year_str)
                week = int(week_str)
            except:
                continue

            # determine first day of ISO week
            week_start = datetime.strptime(f"{year}-W{week}-1", "%G-W%V-%u")

            month_str = week_start.strftime("%Y-%m")
            monthly_filename = f"month_{month_str}.csv"
            monthly_path = os.path.join(self.TACHO_DIR, monthly_filename)

            # create with header if needed
            if not os.path.exists(monthly_path):
                with open(monthly_path, "w") as f:
                    f.write("timestamp,latitude,longitude,speed_kmh,rpm,obd_speed,temp_coolant\n")

            # append
            weekly_path = os.path.join(self.TACHO_DIR, file)
            self._append_csv(weekly_path, monthly_path)

    # ------------------------------------------------------------
    # ROTATION: MONTHLY → YEARLY
    # ------------------------------------------------------------

    def rotate_monthly_to_yearly(self):
        monthly_logs = self.get_monthly_logs()

        for file in monthly_logs:
            try:
                _, ym_str = file.split("_")
                ym_str = ym_str.replace(".csv", "")
                year_str, month_str = ym_str.split("-")
                year = int(year_str)
            except:
                continue

            yearly_filename = f"year_{year}.csv"
            yearly_path = os.path.join(self.TACHO_DIR, yearly_filename)

            if not os.path.exists(yearly_path):
                with open(yearly_path, "w") as f:
                    f.write("timestamp,latitude,longitude,speed_kmh,rpm,obd_speed,temp_coolant\n")

            monthly_path = os.path.join(self.TACHO_DIR, file)
            self._append_csv(monthly_path, yearly_path)

    # ------------------------------------------------------------
    # CLEANUP / DELETION RULES
    # ------------------------------------------------------------

    def delete_old_logs(self):
        now = time.time()

        # DAILY
        for file in self.get_daily_logs():
            path = os.path.join(self.TACHO_DIR, file)
            age_days = (now - os.path.getmtime(path)) / 86400

            if self.is_uploaded("daily", file) or age_days > self.DAILY_MAX_AGE:
                try:
                    os.remove(path)
                except:
                    pass

        # WEEKLY
        for file in self.get_weekly_logs():
            path = os.path.join(self.TACHO_DIR, file)
            age_days = (now - os.path.getmtime(path)) / 86400

            if self.is_uploaded("weekly", file) or age_days > self.WEEKLY_MAX_AGE:
                try:
                    os.remove(path)
                except:
                    pass

        # MONTHLY
        for file in self.get_monthly_logs():
            path = os.path.join(self.TACHO_DIR, file)
            age_days = (now - os.path.getmtime(path)) / 86400

            if self.is_uploaded("monthly", file) or age_days > self.MONTHLY_MAX_AGE:
                try:
                    os.remove(path)
                except:
                    pass

        # YEARLY — NEVER auto delete

    # ------------------------------------------------------------
    # CLOUD SNAPSHOT
    # ------------------------------------------------------------

    def prepare_snapshot(self, modules: dict):
        path = os.path.join(self.TMP_DIR, f"snapshot_{int(time.time())}.json")

        data = {name: m.read_status() for name, m in modules.items()}

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return path

    # ------------------------------------------------------------
    # TEMP CLEANUP
    # ------------------------------------------------------------

    def cleanup_tmp(self, max_age_seconds=3600):
        now = time.time()

        for f in os.listdir(self.TMP_DIR):
            path = os.path.join(self.TMP_DIR, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
                try:
                    os.remove(path)
                except:
                    pass
