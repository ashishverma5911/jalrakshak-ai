import React from 'react';
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ComposedChart,
  Bar,
  Line,
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
  barColor = '#0284c7',
  lineColor = '#2563eb',
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
              <stop offset="100%" stopColor={barColor} stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 0, 0, 0.06)" vertical={false} />
          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            stroke="#94a3b8"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10, offset: 10 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              borderColor: '#e2e8f0',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
              color: '#0f172a',
              fontSize: '12px',
              fontWeight: 500,
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
            wrapperStyle={{ paddingBottom: '10px', fontSize: '11px', color: '#475569', fontWeight: 500 }}
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
