import React, { useState, useEffect } from 'react';
import {
  Database,
  BookOpen,
  HelpCircle,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  Info,
  Search,
  CheckCircle2,
  RefreshCw,
  Cpu,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { apiService, SourceMetadata } from '../services/api';

const SOURCES_DATA = [
  {
    id: 'nasa_gpm_imerg',
    name: 'NASA GPM IMERG Late Run',
    provider: 'NASA Earth Science Data Systems / GSFC',
    param: 'Precipitation accumulation',
    units: 'mm/hr aggregated to mm/day',
    spatial: '0.1° × 0.1° (~10 km resolution)',
    temporal: 'Daily aggregated series',
    coverage: '2000 – Present (Late Run)',
    retrieval: 'Local reproducible fixture (Simulated Late Run pipeline)',
    operationalStatus: 'Local Prototype Fixture (Not a Live Streaming Feed)',
    access: 'NASA Earthdata Open Access (https://gpm.nasa.gov/data/imerg)',
    limitations:
      'Passive microwave and infrared estimates calibrate well for regional storm systems but smooth localized convective cloudbursts. Ground validation requires physical gauge telemetry.',
    tags: ['Precipitation', 'Satellite', 'NASA', 'Fixture'],
    isDemo: true,
  },
  {
    id: 'chirps_daily',
    name: 'CHIRPS Daily Station-Blended Precipitation',
    provider: 'University of California, Santa Barbara (UCSB) / USGS',
    param: 'Gridded daily precipitation',
    units: 'mm/day',
    spatial: '0.05° × 0.05° (~5 km resolution)',
    temporal: 'Daily time-series',
    coverage: '1981 – 2024 (43-year climatology)',
    retrieval: 'Local cached baseline dataset (1991–2020 reference period)',
    operationalStatus: 'Cached Climatological Reference (Not a Live Daily Feed)',
    access: 'UC Santa Barbara / USGS Open Data (https://www.chc.ucsb.edu/data/chirps)',
    limitations:
      'Station interpolation over sparse ground areas can attenuate extreme single-day rainfall peaks. Optimal for climatological departure and SPI distributions.',
    tags: ['Historical', 'Precipitation', 'Baseline', 'Drought'],
    isDemo: true,
  },
  {
    id: 'srtm_dem_30m',
    name: 'NASA SRTM 30m Digital Elevation Model',
    provider: 'NASA Jet Propulsion Laboratory (JPL) / USGS',
    param: 'Surface elevation above mean sea level',
    units: 'Meters (m MSL, WGS84 vertical datum)',
    spatial: '1 arc-second (~30 meter resolution)',
    temporal: 'Static terrain benchmark (Version 3.0 void-filled)',
    coverage: 'Global landmass (60°N – 56°S)',
    retrieval: 'Static district terrain benchmark in districts_metadata.json',
    operationalStatus: 'Static Verified Elevation Benchmark',
    access: 'USGS EarthExplorer (https://earthexplorer.usgs.gov/)',
    limitations:
      'Represents digital surface model (DSM) capturing canopy or rooftop tops in urban/forested tracts. Does not reflect newly constructed earthen dykes or municipal stormwater drainage ditches.',
    tags: ['Elevation', 'Terrain', 'SRTM', 'Static'],
    isDemo: false,
  },
  {
    id: 'upsdma_imd',
    name: 'UPSDMA & IMD Official Hazard Bulletins',
    provider: 'Government of Uttar Pradesh / Ministry of Earth Sciences',
    param: 'Official alert levels, river stage warnings, SOP guidelines',
    units: 'Categorical alerts (Green/Yellow/Orange/Red), danger-mark meters',
    spatial: 'District administrative units (all 75 UP districts)',
    temporal: 'Periodic mock exercise reports & daily monsoon bulletins',
    coverage: 'Uttar Pradesh statewide (including 2024 Mock Exercise Report)',
    retrieval: 'Verified official reference links & emergency contact registry',
    operationalStatus: 'Authoritative Advisory Reference (Not a Live Alert Ingestion)',
    access: 'Government Public Portals (https://upsdma.up.nic.in)',
    limitations:
      'Authoritative source for official emergency evacuation orders. JalRakshak is a decision-support prototype and does not issue or override official government warnings.',
    tags: ['Official', 'Government', 'Warnings', 'Authority'],
    isDemo: false,
  },
];

export const DataSourcesView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sources' | 'methodology' | 'indicators' | 'limitations'>('sources');
  const [searchFilter, setSearchFilter] = useState('');
  const [liveSources, setLiveSources] = useState<SourceMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    apiService
      .fetchSources()
      .then((sources) => setLiveSources(sources))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filteredSources = SOURCES_DATA.filter(
    (s) =>
      s.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.provider.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.tags.some((t) => t.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800/80">
              Open Science & Provenance
            </span>
            <span className="text-xs text-slate-400 font-mono">Transparency Engine</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-1">
            Data Sources & Methodology
          </h1>
          <p className="text-xs lg:text-sm text-slate-300">
            Complete transparency on geospatial datasets, scientific formulas, indicators, and model limitations.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-navy-800 text-sm">
        {[
          { key: 'sources', label: 'Data Sources & Provenance', icon: Database },
          { key: 'methodology', label: 'Processing Pipeline & Math', icon: BookOpen },
          { key: 'indicators', label: 'Indicator Definitions', icon: HelpCircle },
          { key: 'limitations', label: 'Scientific Boundaries & Limitations', icon: AlertTriangle },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 font-medium border-b-2 transition-all ${
                activeTab === tab.key
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Data Sources & Provenance */}
      {activeTab === 'sources' && (
        <div className="space-y-4">
          {/* Data Honesty Notice */}
          <div className="p-3.5 rounded-2xl bg-navy-900/90 border border-cyan-800/60 text-xs text-slate-300 flex items-start space-x-3">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong className="text-white">Data Provenance Integrity Notice:</strong> Datasets below are either
              locally cached verified climatological baselines (CHIRPS 1981–2024), static terrain benchmarks (SRTM DEM),
              or reproducible prototype fixtures (simulated GPM daily series). No source is falsely claimed as a live,
              uninterrupted streaming network feed.
            </div>
          </div>

          {/* Search bar for sources */}
          <div className="p-3 rounded-2xl bg-navy-900 border border-navy-800 flex items-center space-x-2.5 max-w-md">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter by keyword (e.g. satellite, chirps, elevation)..."
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="space-y-4">
            {filteredSources.map((s, i) => (
              <Card key={i} className="p-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3 border-b border-navy-800">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center space-x-2">
                      <span>{s.name}</span>
                      {s.isDemo ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                          DEMO / LOCAL FIXTURE
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono">
                          AUTHORITATIVE BENCHMARK
                        </span>
                      )}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">{s.provider}</p>
                  </div>
                  <div className="text-xs text-slate-300 font-mono bg-navy-850 px-2.5 py-1 rounded-lg border border-navy-750">
                    Status: <strong className="text-cyan-300">{s.operationalStatus}</strong>
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400 block">Parameter & Units</span>
                    <span className="font-semibold text-white">{s.param} ({s.units})</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Spatial Resolution</span>
                    <span className="font-semibold text-white">{s.spatial}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Temporal Resolution</span>
                    <span className="font-semibold text-white">{s.temporal}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Historical Reference</span>
                    <span className="font-semibold text-white">{s.coverage}</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-navy-850 space-y-2 text-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                    <span className="text-slate-400">Retrieval Provenance:</span>
                    <span className="font-mono text-slate-300">{s.retrieval}</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                    <span className="text-slate-400">Access Protocol:</span>
                    <span className="font-mono text-cyan-300">{s.access}</span>
                  </div>
                  <p className="text-slate-300 text-xs italic pt-1 leading-relaxed">{s.limitations}</p>
                  <div className="flex gap-1.5 pt-1">
                    {s.tags.map((t, ti) => (
                      <span
                        key={ti}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-navy-850 border border-navy-750 text-slate-300 font-mono"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Processing Pipeline & Mathematical Methodology */}
      {activeTab === 'methodology' && (
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-bold text-white pb-3 border-b border-navy-800 flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-cyan-400" />
              <span>Scientific Methodology & Algorithmic Specifications</span>
            </h3>

            <div className="mt-4 space-y-4 text-xs text-slate-300 leading-relaxed">
              {/* Section 1 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-cyan-300 text-sm mb-1">
                  1. Data Pipeline Ingestion
                </h4>
                <p>
                  Precipitation observations enter the system via the <code>DataIngestionService</code> from
                  validated daily time series files (e.g. <code>gorakhpur_chirps_daily.csv</code> and <code>mahoba_chirps_daily.csv</code>).
                  Metadata records are retrieved from <code>districts_metadata.json</code>, providing standardized WGS84
                  centroid coordinates and SRTM 30m digital elevation benchmarks.
                </p>
              </div>

              {/* Section 2 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-cyan-300 text-sm mb-1">
                  2. Validation, Duplicate Handling, Units & Staleness Tracking
                </h4>
                <p>
                  Every inbound record undergoes strict validation via <code>DataValidator</code>:
                </p>
                <ul className="list-disc list-inside mt-1.5 space-y-1 text-slate-400">
                  <li><strong>Duplicate Pruning:</strong> Duplicate observation dates are identified and pruned, retaining the latest record.</li>
                  <li><strong>Unit Standardization:</strong> All precipitation values are normalized to millimeters (<code>mm</code>). Negative values are flagged as invalid.</li>
                  <li><strong>Missing-Data Accounting:</strong> Missing observations are explicitly tracked as <code>is_missing: true</code> and are NEVER silently replaced with 0.0 mm.</li>
                  <li><strong>Staleness Detection:</strong> Records older than 24 hours trigger an explicit stale data warning (<code>DATA_STALENESS_HOURS = 24.0</code>).</li>
                </ul>
              </div>

              {/* Section 3 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-cyan-300 text-sm mb-1">
                  3. Rainfall Accumulation & Percentage Anomaly Formulation
                </h4>
                <p>
                  Rolling accumulation over windows N (7, 30, or 90 days) is calculated by:
                </p>
                <div className="my-2 p-2.5 rounded bg-navy-950 font-mono text-[11px] text-cyan-200">
                  Accumulation_N = Sum(P_t, for t = 0 to N-1)
                </div>
                <p>
                  Rainfall departure (% anomaly) is evaluated against the 30-year climatological baseline mean for that period:
                </p>
                <div className="my-2 p-2.5 rounded bg-navy-950 font-mono text-[11px] text-cyan-200">
                  Anomaly (%) = ((Observed_Accumulation - Baseline_Mean) / Baseline_Mean) * 100
                </div>
              </div>

              {/* Section 4 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-amber-300 text-sm mb-1">
                  4. Standardized Precipitation Index (SPI-3) Mathematical Derivation
                </h4>
                <p>
                  The SPI-3 index quantifies 3-month meteorological precipitation deficit or surplus:
                </p>
                <ul className="list-disc list-inside mt-1.5 space-y-1 text-slate-400">
                  <li>3-month rolling precipitation totals are fitted to a 2-parameter Gamma distribution via Maximum Likelihood Estimation (MLE) using <code>scipy.stats.gamma.fit(floc=0)</code>.</li>
                  <li>Cumulative probability H(x) is adjusted for the probability of zero-precipitation periods q: H(x) = q + (1 - q) * G(x).</li>
                  <li>H(x) is transformed to standard normal quantiles Z via inverse standard normal CDF.</li>
                  <li><strong>Limitations:</strong> SPI-3 is strictly a meteorological drought indicator. It does NOT directly measure soil moisture or groundwater levels.</li>
                </ul>
                <div className="my-2 p-2.5 rounded bg-navy-950 font-mono text-[11px] text-amber-200">
                  SPI Classification: Normal (&gt; -1.0) | Moderately Dry (-1.0 to -1.49) | Severely Dry (-1.5 to -1.99) | Extremely Dry (&lt; -2.0)
                </div>
              </div>

              {/* Section 5 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-rose-300 text-sm mb-1">
                  5. Indicator Boundaries: What Indicators Do & Do Not Measure
                </h4>
                <ul className="list-disc list-inside space-y-1 text-slate-400">
                  <li><strong>What Flood Indicators Measure:</strong> High meteorological water loading, cumulative 7d/30d precipitation, and regional terrain slope susceptibility.</li>
                  <li><strong>What Flood Indicators DO NOT Measure:</strong> Actual Rapti/Rohini river stage heights, upstream dam releases from Nepal, embankment breaches, or street-level storm drain choke points.</li>
                  <li><strong>What Drought Indicators Measure:</strong> 90-day rainfall departures, Kharif seasonal deficits, and consecutive dry spell duration.</li>
                  <li><strong>What Drought Indicators DO NOT Measure:</strong> Groundwater table depletion in crystalline aquifers or root-zone soil moisture without dedicated piezometers.</li>
                </ul>
              </div>

              {/* Section 6 */}
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800">
                <h4 className="font-bold text-emerald-300 text-sm mb-1">
                  6. Legal & Operational Authority
                </h4>
                <p>
                  JalRakshak is an academic decision-support prototype. Its derived indicators do <strong>not</strong> constitute
                  official warnings, evacuation orders, or actionable forecasts. For official life-safety warnings, refer exclusively
                  to the India Meteorological Department (IMD), Central Water Commission (CWC), and Uttar Pradesh State Disaster
                  Management Authority (UPSDMA).
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 3: Indicator Definitions */}
      {activeTab === 'indicators' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              name: 'Rainfall Anomaly (%)',
              def: 'Percentage departure of observed precipitation from the 30-year climatological normal for that exact calendar period: ((Observed - Baseline) / Baseline) * 100.',
              formula: 'ΔR = ((R_obs - R_baseline) / R_baseline) × 100%',
              category: 'Derived Climatological Indicator',
            },
            {
              name: 'IMD Wet Days Count (>= 2.5 mm)',
              def: 'Count of calendar days with recorded daily rainfall >= 2.5 mm within the evaluation period, matching the official India Meteorological Department standard definition.',
              formula: 'Count(Days where Daily Rainfall >= 2.5 mm)',
              category: 'Standard Meteorological Metric',
            },
            {
              name: 'Consecutive Dry Spell Days (< 1.0 mm)',
              def: 'Maximum unbroken consecutive run of days with daily rainfall < 1.0 mm during the monsoon crop cultivation cycle, indicating prolonged agricultural moisture stress.',
              formula: 'Max(Consecutive Days where Daily Rainfall < 1.0 mm)',
              category: 'Agricultural Drought Proxy',
            },
            {
              name: 'Historical Percentile Rank',
              def: 'Empirical cumulative percentile rank of the current rolling accumulation window compared to all historical rolling windows across the full reference period.',
              formula: 'Percentile = (Count(Hist <= Current) / Total_Hist) × 100%',
              category: 'Statistical Historical Context',
            },
          ].map((ind, i) => (
            <Card key={i} className="p-4">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-white text-sm">{ind.name}</h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-navy-850 text-cyan-300 font-mono">
                  {ind.category}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">{ind.def}</p>
              <div className="mt-3 p-2.5 rounded bg-navy-950 font-mono text-[11px] text-cyan-300">
                {ind.formula}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Tab 4: Limitations */}
      {activeTab === 'limitations' && (
        <Card className="p-5 border-amber-500/30">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-navy-800 text-amber-300 font-bold text-base">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <span>Operational & Scientific Disclosures</span>
          </div>

          <div className="mt-4 space-y-3 text-xs text-slate-300 leading-relaxed">
            <div className="p-3.5 rounded-xl bg-navy-900 border border-navy-800">
              <span className="font-bold text-white block mb-0.5">Decision-Support Prototype:</span>
              JalRakshak is a research decision-support prototype. It does not replace the India Meteorological
              Department (IMD), Central Water Commission (CWC), or Uttar Pradesh State Disaster Management Authority (UPSDMA).
            </div>

            <div className="p-3.5 rounded-xl bg-navy-900 border border-navy-800">
              <span className="font-bold text-white block mb-0.5">Spatial Resolution Limits:</span>
              Satellite gridded precipitation operates at ~5–10 km resolution. Local localized cloudbursts or micro-drainage
              blockages may not be captured at street level.
            </div>

            <div className="p-3.5 rounded-xl bg-navy-900 border border-navy-800">
              <span className="font-bold text-white block mb-0.5">Hydrological Inundation vs Rainfall:</span>
              Rainfall observations alone do not determine flood inundation or river gauge danger levels. River embankment
              breaches depend on upstream discharge from Nepal and Rapti gauge crests.
            </div>

            <div className="p-3.5 rounded-xl bg-navy-900 border border-navy-800">
              <span className="font-bold text-white block mb-0.5">No Calibrated Probability Misrepresentation:</span>
              Numerical scores represent derived risk indicator thresholds. They are not claimed to be calibrated Bayesian
              forecast probabilities without longitudinal empirical validation.
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
