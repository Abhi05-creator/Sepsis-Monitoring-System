// frontend/src/components/PatientInfo.jsx
import React from 'react';
import { User, Clock } from 'lucide-react';

export default function PatientInfo({ data }) {
  const { demographics, patient_id, risk, ground_truth } = data;
  const s = risk.risk_score;
  const statusColor = s >= 70 ? 'bg-vital-red' : s >= 40 ? 'bg-vital-yellow' : 'bg-vital-green';
  const statusText  = s >= 70 ? 'Critical'     : s >= 40 ? 'Warning'         : 'Stable';

  return (
    <div className="bg-icu-card rounded-xl p-5 border border-icu-border h-full">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 bg-vital-blue/20 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-vital-blue" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Patient {patient_id}</h2>
            <p className="text-slate-500 text-xs">ICU Monitoring</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold text-white ${statusColor}`}>
            {statusText}
          </span>
          {ground_truth === 1 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/20 text-orange-400 border border-orange-500/30">
              Sepsis+
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2.5">
        <div className="flex items-center justify-between py-1.5 border-b border-icu-border">
          <span className="text-slate-400 text-sm">Age</span>
          <span className="text-white text-sm font-medium">{demographics.Age} yrs</span>
        </div>
        <div className="flex items-center justify-between py-1.5 border-b border-icu-border">
          <span className="text-slate-400 text-sm">Gender</span>
          <span className="text-white text-sm font-medium">{demographics.Gender === 1 ? 'Male' : 'Female'}</span>
        </div>
        <div className="flex items-center justify-between py-1.5">
          <span className="text-slate-400 text-sm flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />ICU Stay
          </span>
          <span className="text-white text-sm font-medium">{demographics.ICULOS} hrs</span>
        </div>
      </div>
    </div>
  );
}
