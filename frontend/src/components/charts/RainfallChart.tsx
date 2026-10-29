import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ComposedChart,
} from 'recharts';

export interface RainfallDataPoint {
  date: string;
  rainfall: number | null;
  historicalAvg: number;
}

interface RainfallChartProps {
  data: RainfallDataPoint[];
  barColor?: string;
  lineColor?: string;
  height?: number;
  yAxisLabel?: string;
}

export const RainfallChart: React.FC<RainfallChartProps> = ({
  data,
  barColor = '#00e5ff',
  lineColor = '#38bdf8',
  height = 220,
  yAxisLabel = 'Rainfall (mm)',
}) => {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={barColor} stopOpacity={0.9} />
              <stop offset="100%" stopColor={barColor} stopOpacity={0.3} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.07)" vertical={false} />
          <XAxis
            dataKey="date"
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={false}
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10, offset: 10 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0a1d2c',
              borderColor: 'rgba(56, 120, 165, 0.4)',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
              color: '#f8fafc',
              fontSize: '12px',
            }}
            formatter={(value: any, name: any) => {
              if (name === 'rainfall' || name === 'Daily Rainfall') {
                if (value === null || value === undefined) return ['No Data (Missing)', 'Observed Rainfall'];
                if (value === 0) return ['0.0 mm (Measured Zero Rain)', 'Observed Rainfall'];
                return [`${value} mm`, 'Observed Rainfall'];
              }
              return [`${value} mm`, 'Historical Baseline'];
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            wrapperStyle={{ paddingBottom: '10px', fontSize: '11px', color: '#cbd5e1' }}
          />
          <Bar
            dataKey="rainfall"
            name="Daily Rainfall"
            fill="url(#barGradient)"
            radius={[4, 4, 0, 0]}
            maxBarSize={28}
          />
          <Line
            type="monotone"
            dataKey="historicalAvg"
            name="Historical Average"
            stroke={lineColor}
            strokeDasharray="4 4"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
