// frontend/src/components/VitalsChart.jsx
import React, { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const CONFIGS = {
  HR:    { color: '#ef4444', label: 'HR',   unit: 'bpm'  },
  O2Sat: { color: '#3b82f6', label: 'SpO₂', unit: '%'    },
  Temp:  { color: '#f59e0b', label: 'Temp', unit: '°C'   },
  Resp:  { color: '#22c55e', label: 'Resp', unit: '/min' },
  SBP:   { color: '#a855f7', label: 'SBP',  unit: 'mmHg' },
};

export default function VitalsChart({ data }) {
  const [active, setActive] = useState(['HR', 'O2Sat', 'Resp']);
  const latest = data[data.length - 1] || {};
  const toggle = k => setActive(p => p.includes(k) ? p.filter(x => x !== k) : [...p, k]);

  const CustomTip = ({ active: a, payload, label }) => {
    if (!a || !payload?.length) return null;
    return (
      <div className="bg-icu-card border border-icu-border rounded-lg p-2 text-xs shadow-xl">
        <p className="text-slate-400 mb-1">{label}</p>
        {payload.map((e, i) => (
          <p key={i} style={{ color: e.color }}>
            {CONFIGS[e.dataKey]?.label}: {e.value} {CONFIGS[e.dataKey]?.unit}
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-icu-card rounded-xl p-5 border border-icu-border">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-slate-400">Real-Time Vitals (last 60 sec)</h3>
        <div className="flex gap-1.5 flex-wrap">
          {Object.entries(CONFIGS).map(([k, v]) => (
            <button key={k} onClick={() => toggle(k)}
              className="px-2.5 py-0.5 rounded-full text-xs font-medium transition-all"
              style={{
                backgroundColor: active.includes(k) ? v.color : '#1e293b',
                color: active.includes(k) ? '#fff' : '#64748b'
              }}>
              {k}
            </button>
          ))}
        </div>
      </div>

      {/* Live value tiles */}
      <div className="grid grid-cols-5 gap-2 mb-4">
        {Object.entries(CONFIGS).map(([k, v]) => (
          <div key={k} onClick={() => toggle(k)}
            className={`p-2.5 rounded-lg border cursor-pointer transition-opacity ${active.includes(k) ? 'opacity-100' : 'opacity-35'}`}
            style={{ borderColor: v.color + '44' }}>
            <p className="text-xs text-slate-400 truncate">{v.label}</p>
            <p className="text-lg font-bold mt-0.5" style={{ color: v.color }}>
              {latest[k] ?? '—'}
              <span className="text-xs font-normal text-slate-500 ml-0.5">{v.unit}</span>
            </p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top:4, right:4, left:-22, bottom:4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a4a" />
            <XAxis dataKey="time" stroke="#475569" tick={{ fill:'#475569', fontSize:10 }}
              interval="preserveStartEnd" />
            <YAxis stroke="#475569" tick={{ fill:'#475569', fontSize:10 }} domain={['auto','auto']} />
            <Tooltip content={<CustomTip />} />
            {active.map(k => (
              <Line key={k} type="monotone" dataKey={k}
                stroke={CONFIGS[k].color} strokeWidth={2}
                dot={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
