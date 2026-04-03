// frontend/src/components/RiskGauge.jsx
import React from 'react';
export default function RiskGauge({ score, level }) {
  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#eab308' : '#22c55e';
  const C = 2 * Math.PI * 48;
  const offset = C - (score / 100) * C;
  return (
    <div className={`bg-icu-card rounded-xl p-5 border border-icu-border h-full ${score >= 70 ? 'pulse-critical' : ''}`}>
      <h3 className="text-xs font-medium text-slate-400 mb-3">Sepsis Risk — TCN Model</h3>
      <div className="flex justify-center">
        <div className="relative w-40 h-40">
          <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
            <circle cx="60" cy="60" r="48" stroke="#334155" strokeWidth="10" fill="none"/>
            <circle cx="60" cy="60" r="48" stroke={color} strokeWidth="10" fill="none"
              strokeLinecap="round" strokeDasharray={C} strokeDashoffset={offset}
              style={{transition:'stroke-dashoffset 0.6s ease, stroke 0.3s ease'}}/>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold" style={{color}}>{score}%</span>
            <span className="text-xs text-slate-400 mt-0.5">{level}</span>
          </div>
        </div>
      </div>
      <div className="mt-4 flex gap-1">
        <div className={`flex-1 h-1.5 rounded-l-full transition-colors ${score>0?'bg-vital-green':'bg-icu-border'}`}/>
        <div className={`flex-1 h-1.5 transition-colors ${score>=40?'bg-vital-yellow':'bg-icu-border'}`}/>
        <div className={`flex-1 h-1.5 rounded-r-full transition-colors ${score>=70?'bg-vital-red':'bg-icu-border'}`}/>
      </div>
      <div className="flex justify-between mt-1 text-xs text-slate-600">
        <span>Low</span><span>Medium</span><span>High</span>
      </div>
    </div>
  );
}
