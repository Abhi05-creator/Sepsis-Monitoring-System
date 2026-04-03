// frontend/src/components/LabValues.jsx
import React from 'react';

const LAB_META = {
  Lactate:    { unit: 'mmol/L', lo: 0.5, hi: 2.0, danger: 4    },
  Creatinine: { unit: 'mg/dL',  lo: 0.6, hi: 1.2, danger: 2    },
  WBC:        { unit: 'K/µL',   lo: 4,   hi: 11,  danger: 15   },
  Glucose:    { unit: 'mg/dL',  lo: 70,  hi: 140, danger: 200  },
  Platelets:  { unit: 'K/µL',   lo: 150, hi: 400, danger: 80,  invertDanger: true },
};

function getStatus(key, val) {
  const m = LAB_META[key];
  if (!m) return 'ok';
  if (m.invertDanger) return val < m.danger ? 'crit' : val < m.lo ? 'warn' : 'ok';
  return val > m.danger ? 'crit' : (val < m.lo || val > m.hi) ? 'warn' : 'ok';
}

const TEXT = { ok: 'text-vital-green', warn: 'text-vital-yellow', crit: 'text-vital-red' };
const BG   = {
  ok:   'bg-green-500/8  border-green-500/20',
  warn: 'bg-yellow-500/8 border-yellow-500/20',
  crit: 'bg-red-500/8    border-red-500/20',
};

export default function LabValues({ labs }) {
  return (
    <div className="bg-icu-card rounded-xl p-5 border border-icu-border h-full">
      <h3 className="text-xs font-medium text-slate-400 mb-3">Lab Values</h3>
      <div className="space-y-2.5">
        {Object.entries(labs).map(([k, v]) => {
          const m = LAB_META[k];
          if (!m) return null;
          const st = getStatus(k, v);
          return (
            <div key={k} className={`p-2.5 rounded-lg border ${BG[st]}`}>
              <div className="flex justify-between items-baseline">
                <div>
                  <p className="text-xs text-slate-500">{k}</p>
                  <p className={`text-base font-bold ${TEXT[st]}`}>
                    {typeof v === 'number' ? v.toFixed(1) : v}
                    <span className="text-xs font-normal text-slate-500 ml-1">{m.unit}</span>
                  </p>
                </div>
                <p className="text-xs text-slate-600">{m.lo}–{m.hi}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
