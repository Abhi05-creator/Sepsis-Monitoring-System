// frontend/src/components/AlertsPanel.jsx
import React from 'react';
import { Bell } from 'lucide-react';

export default function AlertsPanel({ alerts, onDismiss }) {
  return (
    <div className="bg-icu-card rounded-xl p-5 border border-icu-border h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bell className="w-3.5 h-3.5 text-slate-400" />
          <h3 className="text-xs font-medium text-slate-400">Alerts</h3>
        </div>
        {alerts.length > 0 && (
          <span className="px-2 py-0.5 bg-vital-red rounded-full text-xs text-white font-medium">
            {alerts.length}
          </span>
        )}
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto pr-0.5">
        {alerts.length === 0 ? (
          <div className="text-center py-10">
            <Bell className="w-7 h-7 text-slate-700 mx-auto mb-2" />
            <p className="text-slate-600 text-sm">No active alerts</p>
          </div>
        ) : alerts.map(a => {
          const crit = a.type === 'critical';
          return (
            <div key={a.id}
              className={`p-3 rounded-lg border animate-fade-in ${
                crit ? 'bg-red-500/10 border-red-500/25' : 'bg-yellow-500/10 border-yellow-500/25'
              }`}>
              <div className="flex justify-between gap-2">
                <div className="min-w-0">
                  <p className={`text-xs font-medium truncate ${crit ? 'text-red-400' : 'text-yellow-400'}`}>
                    {a.message}
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">{a.ts}</p>
                </div>
                <button onClick={() => onDismiss(a.id)} className="text-slate-600 hover:text-slate-300 shrink-0 text-sm">
                  ✕
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
