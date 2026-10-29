import { RainfallDataPoint } from '../components/charts/RainfallChart';

export const IS_DEMO_DATA = true;
export const DEMO_DATA_DISCLAIMER =
  'DEMO DATA / PROTOTYPE FIXTURE: Values shown are illustrative development fixtures for interface verification. Connect live backend for verified measurements.';

export interface DistrictGeoData {
  id: string;
  name: string;
  hindiName: string;
  lat: number;
  lng: number;
  elevationM: number;
  riverBasin: string;
  floodRisk: 'high' | 'moderate' | 'low';
  droughtRisk: 'high' | 'moderate' | 'low';
  rainfall7dMm: number;
  rainfall30dMm: number;
  rainfall90dMm: number;
  seasonalDeficitPct: number;
  anomalyPct: number;
  spi3: number;
  lastUpdated: string;
  isPilot: boolean;
}

export const UP_DISTRICTS_DATA: DistrictGeoData[] = [
  {
    id: 'gorakhpur',
    name: 'Gorakhpur',
    hindiName: 'गोरखपुर',
    lat: 26.7606,
    lng: 83.3732,
    elevationM: 84,
    riverBasin: 'Rapti & Rohini Basin',
    floodRisk: 'high',
    droughtRisk: 'low',
    rainfall7dMm: 286,
    rainfall30dMm: 512,
    rainfall90dMm: 1024,
    seasonalDeficitPct: 16,
    anomalyPct: 65,
    spi3: 1.45,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: true,
  },
  {
    id: 'mahoba',
    name: 'Mahoba',
    hindiName: 'महोबा',
    lat: 25.2953,
    lng: 79.8630,
    elevationM: 214,
    riverBasin: 'Ken & Betwa Interfluve (Bundelkhand)',
    floodRisk: 'low',
    droughtRisk: 'moderate',
    rainfall7dMm: 4,
    rainfall30dMm: 18,
    rainfall90dMm: 62,
    seasonalDeficitPct: -72,
    anomalyPct: -58,
    spi3: -1.84,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: true,
  },
  {
    id: 'lucknow',
    name: 'Lucknow',
    hindiName: 'लखनऊ',
    lat: 26.8467,
    lng: 80.9462,
    elevationM: 123,
    riverBasin: 'Gomti River Basin',
    floodRisk: 'low',
    droughtRisk: 'low',
    rainfall7dMm: 42,
    rainfall30dMm: 110,
    rainfall90dMm: 480,
    seasonalDeficitPct: -5,
    anomalyPct: 4,
    spi3: 0.12,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'prayagraj',
    name: 'Prayagraj',
    hindiName: 'प्रयागराज',
    lat: 25.4358,
    lng: 81.8463,
    elevationM: 98,
    riverBasin: 'Ganga & Yamuna Sangam',
    floodRisk: 'moderate',
    droughtRisk: 'low',
    rainfall7dMm: 94,
    rainfall30dMm: 210,
    rainfall90dMm: 640,
    seasonalDeficitPct: 8,
    anomalyPct: 28,
    spi3: 0.65,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'varanasi',
    name: 'Varanasi',
    hindiName: 'वाराणसी',
    lat: 25.3176,
    lng: 82.9739,
    elevationM: 81,
    riverBasin: 'Middle Ganga Basin',
    floodRisk: 'moderate',
    droughtRisk: 'low',
    rainfall7dMm: 105,
    rainfall30dMm: 235,
    rainfall90dMm: 680,
    seasonalDeficitPct: 12,
    anomalyPct: 31,
    spi3: 0.72,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'jhansi',
    name: 'Jhansi',
    hindiName: 'झांसी',
    lat: 25.4484,
    lng: 78.5685,
    elevationM: 284,
    riverBasin: 'Betwa Basin (Bundelkhand)',
    floodRisk: 'low',
    droughtRisk: 'moderate',
    rainfall7dMm: 8,
    rainfall30dMm: 25,
    rainfall90dMm: 85,
    seasonalDeficitPct: -64,
    anomalyPct: -45,
    spi3: -1.62,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'banda',
    name: 'Banda',
    hindiName: 'बांदा',
    lat: 25.4754,
    lng: 80.3346,
    elevationM: 123,
    riverBasin: 'Ken River Basin (Bundelkhand)',
    floodRisk: 'low',
    droughtRisk: 'moderate',
    rainfall7dMm: 12,
    rainfall30dMm: 32,
    rainfall90dMm: 96,
    seasonalDeficitPct: -60,
    anomalyPct: -40,
    spi3: -1.54,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'kushinagar',
    name: 'Kushinagar',
    hindiName: 'कुशीनगर',
    lat: 26.7410,
    lng: 83.8887,
    elevationM: 78,
    riverBasin: 'Gandak & Little Gandak Basin',
    floodRisk: 'high',
    droughtRisk: 'low',
    rainfall7dMm: 245,
    rainfall30dMm: 480,
    rainfall90dMm: 980,
    seasonalDeficitPct: 22,
    anomalyPct: 52,
    spi3: 1.38,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
  {
    id: 'saharanpur',
    name: 'Saharanpur',
    hindiName: 'सहारनपुर',
    lat: 29.9640,
    lng: 77.5460,
    elevationM: 275,
    riverBasin: 'Upper Yamuna & Hindon',
    floodRisk: 'low',
    droughtRisk: 'low',
    rainfall7dMm: 18,
    rainfall30dMm: 45,
    rainfall90dMm: 310,
    seasonalDeficitPct: -10,
    anomalyPct: -6,
    spi3: -0.22,
    lastUpdated: '28 Oct 2026, 10:30 AM',
    isPilot: false,
  },
];

// Dynamically generated rainfall series for Gorakhpur and Mahoba across multiple time windows
export const getFilteredRainfallData = (
  location: 'gorakhpur' | 'mahoba',
  range: '7' | '30' | '90' | '365',
  aggregation: 'daily' | 'weekly' | 'monthly' = 'daily'
): RainfallDataPoint[] => {
  if (range === '365' || aggregation === 'monthly') {
    if (location === 'gorakhpur') {
      return [
        { date: 'Jan', rainfall: 15, historicalAvg: 18 },
        { date: 'Feb', rainfall: 22, historicalAvg: 14 },
        { date: 'Mar', rainfall: 10, historicalAvg: 12 },
        { date: 'Apr', rainfall: 8, historicalAvg: 9 },
        { date: 'May', rainfall: 35, historicalAvg: 28 },
        { date: 'Jun', rainfall: 180, historicalAvg: 145 },
        { date: 'Jul', rainfall: 310, historicalAvg: 290 },
        { date: 'Aug', rainfall: 240, historicalAvg: 250 },
        { date: 'Sep', rainfall: 160, historicalAvg: 180 },
        { date: 'Oct', rainfall: 124, historicalAvg: 40 },
        { date: 'Nov', rainfall: 8, historicalAvg: 6 },
        { date: 'Dec', rainfall: 4, historicalAvg: 5 },
      ];
    } else {
      return [
        { date: 'Jan', rainfall: 6, historicalAvg: 12 },
        { date: 'Feb', rainfall: 4, historicalAvg: 10 },
        { date: 'Mar', rainfall: 2, historicalAvg: 8 },
        { date: 'Apr', rainfall: 0, historicalAvg: 5 },
        { date: 'May', rainfall: 8, historicalAvg: 14 },
        { date: 'Jun', rainfall: 42, historicalAvg: 85 },
        { date: 'Jul', rainfall: 98, historicalAvg: 260 },
        { date: 'Aug', rainfall: 82, historicalAvg: 240 },
        { date: 'Sep', rainfall: 35, historicalAvg: 140 },
        { date: 'Oct', rainfall: 8, historicalAvg: 32 },
        { date: 'Nov', rainfall: 2, historicalAvg: 10 },
        { date: 'Dec', rainfall: 1, historicalAvg: 6 },
      ];
    }
  }

  if (range === '7') {
    if (location === 'gorakhpur') {
      return [
        { date: 'Oct 22', rainfall: 52, historicalAvg: 9 },
        { date: 'Oct 23', rainfall: 38, historicalAvg: 9 },
        { date: 'Oct 24', rainfall: 92, historicalAvg: 8 },
        { date: 'Oct 25', rainfall: 64, historicalAvg: 8 },
        { date: 'Oct 26', rainfall: 124, historicalAvg: 8 },
        { date: 'Oct 27', rainfall: 78, historicalAvg: 7 },
        { date: 'Oct 28', rainfall: 64, historicalAvg: 7 },
      ];
    } else {
      return [
        { date: 'Oct 22', rainfall: 0, historicalAvg: 3 },
        { date: 'Oct 23', rainfall: 0, historicalAvg: 3 },
        { date: 'Oct 24', rainfall: 1, historicalAvg: 3 },
        { date: 'Oct 25', rainfall: 0, historicalAvg: 2 },
        { date: 'Oct 26', rainfall: 0, historicalAvg: 2 },
        { date: 'Oct 27', rainfall: 0, historicalAvg: 2 },
        { date: 'Oct 28', rainfall: 0, historicalAvg: 1 },
      ];
    }
  }

  if (range === '90') {
    if (location === 'gorakhpur') {
      return [
        { date: 'Aug 1-15', rainfall: 140, historicalAvg: 120 },
        { date: 'Aug 16-31', rainfall: 100, historicalAvg: 130 },
        { date: 'Sep 1-15', rainfall: 90, historicalAvg: 95 },
        { date: 'Sep 16-30', rainfall: 70, historicalAvg: 85 },
        { date: 'Oct 1-15', rainfall: 110, historicalAvg: 25 },
        { date: 'Oct 16-28', rainfall: 286, historicalAvg: 15 },
      ];
    } else {
      return [
        { date: 'Aug 1-15', rainfall: 48, historicalAvg: 115 },
        { date: 'Aug 16-31', rainfall: 34, historicalAvg: 125 },
        { date: 'Sep 1-15', rainfall: 22, historicalAvg: 75 },
        { date: 'Sep 16-30', rainfall: 13, historicalAvg: 65 },
        { date: 'Oct 1-15', rainfall: 8, historicalAvg: 20 },
        { date: 'Oct 16-28', rainfall: 0, historicalAvg: 12 },
      ];
    }
  }

  // Default: 30 days
  if (location === 'gorakhpur') {
    return [
      { date: 'Sep 28', rainfall: 32, historicalAvg: 18 },
      { date: 'Sep 30', rainfall: 45, historicalAvg: 17 },
      { date: 'Oct 2', rainfall: 58, historicalAvg: 16 },
      { date: 'Oct 5', rainfall: 110, historicalAvg: 15 },
      { date: 'Oct 8', rainfall: 42, historicalAvg: 14 },
      { date: 'Oct 10', rainfall: 28, historicalAvg: 13 },
      { date: 'Oct 12', rainfall: 64, historicalAvg: 12 },
      { date: 'Oct 15', rainfall: 35, historicalAvg: 11 },
      { date: 'Oct 18', rainfall: 48, historicalAvg: 10 },
      { date: 'Oct 20', rainfall: 68, historicalAvg: 10 },
      { date: 'Oct 22', rainfall: 52, historicalAvg: 9 },
      { date: 'Oct 24', rainfall: 92, historicalAvg: 8 },
      { date: 'Oct 26', rainfall: 124, historicalAvg: 8 },
      { date: 'Oct 28', rainfall: 286, historicalAvg: 7 },
    ];
  } else {
    return [
      { date: 'Sep 28', rainfall: 2, historicalAvg: 14 },
      { date: 'Sep 30', rainfall: 0, historicalAvg: 12 },
      { date: 'Oct 2', rainfall: 5, historicalAvg: 11 },
      { date: 'Oct 5', rainfall: 1, historicalAvg: 10 },
      { date: 'Oct 8', rainfall: 0, historicalAvg: 8 },
      { date: 'Oct 10', rainfall: 4, historicalAvg: 7 },
      { date: 'Oct 12', rainfall: 0, historicalAvg: 6 },
      { date: 'Oct 15', rainfall: 8, historicalAvg: 5 },
      { date: 'Oct 18', rainfall: 0, historicalAvg: 4 },
      { date: 'Oct 20', rainfall: 2, historicalAvg: 4 },
      { date: 'Oct 22', rainfall: 0, historicalAvg: 3 },
      { date: 'Oct 24', rainfall: 1, historicalAvg: 3 },
      { date: 'Oct 26', rainfall: 0, historicalAvg: 2 },
      { date: 'Oct 28', rainfall: 0, historicalAvg: 1 },
    ];
  }
};
