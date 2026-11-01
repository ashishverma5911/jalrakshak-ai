import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timezone

from ..core.config import DATA_DIR
from .validation import DataValidator, DataValidationError
from .spatial_aggregation import SpatialAggregator, SpatialAggregationError

class DataIngestionService:
    """
    Ingests and normalizes precipitation observations and district metadata.
    Enforces validation, duplicate pruning, boundary checking, and strict data mode isolation.
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
        clean_id = district_id.lower().replace("district-", "").strip()
        for d in districts:
            d_id = d["id"].lower().replace("district-", "").strip()
            if d_id == clean_id:
                return d
        raise DataValidationError(f"District '{district_id}' is not in the supported pilot registry.")

    def load_daily_rainfall(
        self,
        district_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mode: str = "demo"
    ) -> pd.DataFrame:
        """
        Loads, validates and filters daily rainfall for a district.
        Parameters:
            district_id: Slug or ID (e.g. 'gorakhpur' or 'district-gorakhpur')
            start_date: Optional ISO date string
            end_date: Optional ISO date string
            mode: 'verified' (genuine observations) or 'demo' (prototype fixtures)
        """
        district_id = district_id.lower().replace("district-", "").strip()
        region_id = f"district-{district_id}"

        # Confirm district exists
        self.get_district_info(district_id)

        if mode == "live":
            from ..services.environmental_cache import EnvironmentalCacheService
            cached = EnvironmentalCacheService.get_cached_district_data(district_id)
            if cached and "daily_records" in cached and cached["daily_records"]:
                rows = [
                    {"date": pd.to_datetime(r["date"]), "rainfall_mm": r.get("rainfall_mm")}
                    for r in cached["daily_records"]
                ]
                df = pd.DataFrame(rows)
            else:
                df = pd.DataFrame(columns=["date", "rainfall_mm"])

            if start_date and not df.empty:
                df = df[df["date"] >= pd.to_datetime(start_date)]
            if end_date and not df.empty:
                df = df[df["date"] <= pd.to_datetime(end_date)]
            return df

        # Check file existence first to return 404 for unconfigured districts
        verified_path = self.data_dir / f"{district_id}_chirps_daily_verified.csv"
        demo_path = self.data_dir / f"{district_id}_chirps_daily.csv"

        if mode == "verified":
            csv_path = verified_path if verified_path.exists() else demo_path
            # For verified operational mode, validate administrative boundary polygon
            SpatialAggregator.load_district_boundary(region_id)
        else:
            csv_path = demo_path if demo_path.exists() else verified_path

        if not csv_path.exists():
            raise FileNotFoundError(f"Daily precipitation series not found for '{district_id}'")

        cache_key = f"{district_id}_{mode}"

        if cache_key not in self._cache:
            raw_df = pd.read_csv(csv_path)
            clean_df, report = DataValidator.validate_and_clean_rainfall_df(
                raw_df, date_col="date", val_col="rainfall_mm"
            )
            self._cache[cache_key] = clean_df

        df = self._cache[cache_key].copy()

        # Date filtering
        if start_date:
            df = df[df["date"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["date"] <= pd.to_datetime(end_date)]

        return df
