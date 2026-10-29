import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timezone

from ..core.config import DATA_DIR
from .validation import DataValidator, DataValidationError

class DataIngestionService:
    """
    Ingests and normalizes precipitation observations and district metadata.
    Enforces validation, duplicate pruning, and stale detection.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self._cache: Dict[str, pd.DataFrame] = {}
        self._districts: Optional[List[Dict[str, Any]]] = None

    def get_districts_metadata(self) -> List[Dict[str, Any]]:
        if self._districts is not None:
            return self._districts
        meta_file = self.data_dir / "districts_metadata.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Districts metadata not found at {meta_file}")
        with open(meta_file, "r", encoding="utf-8") as f:
            self._districts = json.load(f)
        return self._districts

    def get_district_info(self, district_id: str) -> Dict[str, Any]:
        districts = self.get_districts_metadata()
        for d in districts:
            if d["id"].lower() == district_id.lower():
                return d
        raise DataValidationError(f"District '{district_id}' is not in the supported pilot registry.")

    def load_daily_rainfall(
        self,
        district_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Loads, validates and filters daily rainfall for a district.
        """
        district_id = district_id.lower()
        # Verify district exists
        self.get_district_info(district_id)

        # Cache check
        if district_id not in self._cache:
            csv_path = self.data_dir / f"{district_id}_chirps_daily.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Daily precipitation series not found for '{district_id}'")
            raw_df = pd.read_csv(csv_path)
            clean_df, report = DataValidator.validate_and_clean_rainfall_df(
                raw_df, date_col="date", val_col="rainfall_mm"
            )
            self._cache[district_id] = clean_df

        df = self._cache[district_id].copy()

        # Date filtering
        if start_date:
            df = df[df["date"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["date"] <= pd.to_datetime(end_date)]

        return df
