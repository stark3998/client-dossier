// frontend/src/components/dashboard/DashboardCharts.tsx
import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import type { ClientHealthReport } from '@/types';

interface DashboardChartsProps {
  healthScores: Record<string, ClientHealthReport>;
}

const GRADE_COLORS: Record<string, string> = {
  A: '#86BC25',  // chart-1
  B: '#00A3E0',  // chart-2
  C: '#f59e0b',  // chart-3
  D: '#ef4444',  // chart-4
  F: '#8b5cf6',  // chart-5
};

const AXIS_STYLE = { fill: '#888888', fontSize: 11 };
const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 6, fontSize: 12 },
  labelStyle: { color: '#f0f0f0' },
  itemStyle: { color: '#f0f0f0' },
};

/**
 * Two side-by-side Recharts visualizations:
 * 1. Risk Overview — open vs critical risks per client (BarChart)
 * 2. Health Distribution — grade distribution A-F (PieChart)
 */
export function DashboardCharts({ healthScores }: DashboardChartsProps) {
  const riskData = useMemo(() =>
    Object.entries(healthScores).map(([name, report]) => ({
      name: name.length > 12 ? `${name.slice(0, 11)}...` : name,
      open: report.risk_posture.open_risks,
      critical: report.risk_posture.critical_risks,
    })),
    [healthScores],
  );

  const gradeData = useMemo(() => {
    const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    Object.values(healthScores).forEach((r) => { counts[r.grade] = (counts[r.grade] ?? 0) + 1; });
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([grade, value]) => ({ grade, value }));
  }, [healthScores]);

  if (Object.keys(healthScores).length === 0) {
    return (
      <div className="text-sm text-text-muted text-center py-8">
        No health data available yet.
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row gap-4">
      {/* Risk Overview */}
      <div className="flex-1 bg-bg-panel border border-border-default rounded-md p-4">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
          Risk Overview
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={riskData} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
            <XAxis dataKey="name" tick={AXIS_STYLE} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_STYLE} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Bar dataKey="open" name="Open" fill="#86BC25" radius={[3, 3, 0, 0]} />
            <Bar dataKey="critical" name="Critical" fill="#ef4444" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Health Distribution */}
      <div className="flex-1 bg-bg-panel border border-border-default rounded-md p-4">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
          Health Distribution
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={gradeData}
              dataKey="value"
              nameKey="grade"
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={75}
              paddingAngle={3}
              label={({ grade, value }: { grade: string; value: number }) => `${grade}: ${value}`}
            >
              {gradeData.map((entry) => (
                <Cell key={entry.grade} fill={GRADE_COLORS[entry.grade] ?? '#555555'} />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend
              formatter={(value: string) => <span className="text-text-secondary text-xs">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
