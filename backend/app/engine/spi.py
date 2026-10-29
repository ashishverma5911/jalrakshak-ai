import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from scipy import stats

class SPIEngine:
    """
    Standardized Precipitation Index (SPI) Calculator
    Implements McKee et al. (1993) and WMO Guidelines (WMO-No. 1090).
    Fits a two-parameter Gamma distribution to 3-month rolling rainfall sums
    and transforms the cumulative probability into standard normal Z-scores.
    """

    CATEGORIES = [
        (2.0, "Extremely Wet"),
        (1.5, "Very Wet"),
        (1.0, "Moderately Wet"),
        (-1.0, "Near Normal"),
        (-1.5, "Moderately Dry"),
        (-2.0, "Severely Dry"),
        (-99.0, "Extremely Dry"),
    ]

    @staticmethod
    def classify_spi(spi_val: float) -> str:
        for threshold, label in SPIEngine.CATEGORIES:
            if spi_val >= threshold:
                return label
        return "Extremely Dry"

    @classmethod
    def fit_gamma_parameters(cls, data: np.ndarray) -> Tuple[float, float, float]:
        """
        Fits 2-parameter Gamma distribution with zero-precipitation probability adjustment:
        Returns: (alpha/shape, beta/scale, zero_prob_q)
        """
        zeros_count = np.sum(data == 0)
        n = len(data)
        q = zeros_count / n if n > 0 else 0.0

        non_zeros = data[data > 0]
        if len(non_zeros) < 5:
            # Insufficient non-zero points for stable MLE fit
            return 1.0, 1.0, q

        # Maximum Likelihood Estimation via scipy.stats
        # floc=0 enforces two-parameter gamma (location parameter fixed to 0)
        shape, loc, scale = stats.gamma.fit(non_zeros, floc=0)
        return float(shape), float(scale), float(q)

    @classmethod
    def calculate_spi_3(
        cls,
        monthly_series: pd.Series,
        reference_period_slice: Optional[pd.Series] = None
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculates SPI-3 for the latest 3-month period.
        Parameters:
            monthly_series: Monthly rainfall totals in mm. Must have at least 3 months.
            reference_period_slice: Historical baseline monthly series (e.g. 10+ years).
        Returns:
            (spi_value, category_label, metadata_dict)
        """
        if len(monthly_series) < 3:
            return 0.0, "Insufficient Data", {"error": "Need at least 3 consecutive months"}

        # 3-month rolling sum
        rolling_3m = monthly_series.rolling(window=3).sum().dropna()
        if rolling_3m.empty:
            return 0.0, "Insufficient Data", {"error": "Rolling 3-month sums could not be computed"}

        # Use reference series if provided, else use the input series
        fit_data = (
            reference_period_slice.rolling(window=3).sum().dropna().values
            if reference_period_slice is not None and len(reference_period_slice) >= 12
            else rolling_3m.values
        )

        target_val = float(rolling_3m.iloc[-1])

        # Fit gamma
        shape, scale, q = cls.fit_gamma_parameters(fit_data)

        # Compute cumulative probability H(x) = q + (1 - q) * G(x)
        if target_val <= 0:
            h_x = q / 2.0 if q > 0 else 0.001
        else:
            g_x = stats.gamma.cdf(target_val, a=shape, scale=scale)
            h_x = q + (1.0 - q) * g_x

        # Numerical stability bounds for normal inverse
        h_x = max(0.0001, min(0.9999, h_x))

        # Standard normal inverse transformation (Z-score)
        spi_val = float(stats.norm.ppf(h_x))
        spi_val = round(spi_val, 2)
        category = cls.classify_spi(spi_val)

        metadata = {
            "3_month_precipitation_sum_mm": round(target_val, 1),
            "gamma_shape_alpha": round(shape, 3),
            "gamma_scale_beta": round(scale, 3),
            "zero_rain_probability_q": round(q, 3),
            "cumulative_prob_hx": round(h_x, 4),
            "calibration_samples": len(fit_data),
            "limitations": (
                "SPI reflects meteorological precipitation deficit. "
                "It does not directly measure groundwater table depth or soil moisture retention without in-situ telemetry."
            ),
        }

        return spi_val, category, metadata
