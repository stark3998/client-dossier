// frontend/src/components/dashboard/DashboardCharts.tsx
import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { useTheme } from '@/contexts/ThemeContext';
import type { ClientHealthReport } from '@/types';

interface DashboardChartsProps {
  healthScores: Record<string, ClientHealthReport>;
}

const GRADE_COLORS: Record<string, string> = {
  A: '#86BC25',
  B: '#00A3E0',
  C: '#f59e0b',
  D: '#ef4444',
  F: '#8b5cf6',
};

export function DashboardCharts({ healthScores }: DashboardChartsProps) {
  const { isDark } = useTheme();

  const axisStyle = { fill: isDark ? '#888888' : '#616161', fontSize: 11 };
  const tooltipStyle = {
    contentStyle: {
      backgroundColor: isDark ? '#1a1a1a' : '#ffffff',
      border: `1px solid ${isDark ? '#2a2a2a' : '#e0e0e0'}`,
      borderRadius: 6,
      fontSize: 12,
    },
    labelStyle: { color: isDark ? '#f0f0f0' : '#212121' },
    itemStyle: { color: isDark ? '#f0f0f0' : '#212121' },
  };
  const gridStroke = isDark ? '#2a2a2a' : '#e0e0e0';

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
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip {...tooltipStyle} />
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
            <Tooltip {...tooltipStyle} />
            <Legend
              formatter={(value: string) => <span className="text-text-secondary text-xs">{value}</span>}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
