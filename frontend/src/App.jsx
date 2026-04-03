// frontend/src/App.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import PatientInfo   from './components/PatientInfo';
import RiskGauge     from './components/RiskGauge';
import VitalsChart   from './components/VitalsChart';
import AlertsPanel   from './components/AlertsPanel';
import LabValues     from './components/LabValues';
import { Activity, Wifi, WifiOff } from 'lucide-react';

const WS_URL        = 'ws://localhost:8000/stream';
const MAX_POINTS    = 60;

export default function App() {
  const [connected,    setConnected]    = useState(false);
  const [patientData,  setPatientData]  = useState(null);
  const [history,      setHistory]      = useState([]);
  const [alerts,       setAlerts]       = useState([]);
  const wsRef          = useRef(null);
  const retryRef       = useRef(null);

  const checkAlerts = useCallback((data) => {
    const ts  = new Date().toLocaleTimeString();
    const add = [];
    const { vitals, risk } = data;

    if (vitals.HR > 100)   add.push({ id: Date.now()+1, type:'warning',  message:`Tachycardia: HR ${vitals.HR} bpm`,           ts });
    if (vitals.HR < 50)    add.push({ id: Date.now()+2, type:'critical', message:`Bradycardia: HR ${vitals.HR} bpm`,           ts });
    if (vitals.O2Sat < 92) add.push({ id: Date.now()+3, type:'critical', message:`Low SpO₂: ${vitals.O2Sat}%`,                ts });
    if (vitals.Temp > 38)  add.push({ id: Date.now()+4, type:'warning',  message:`Fever: Temp ${vitals.Temp}°C`,               ts });
    if (vitals.Resp > 24)  add.push({ id: Date.now()+5, type:'warning',  message:`Tachypnea: Resp ${vitals.Resp}/min`,         ts });
    if (risk.risk_score > 70)
                           add.push({ id: Date.now()+6, type:'critical', message:`High sepsis risk: ${risk.risk_score}%`,      ts });
    if (data.ground_truth === 1)
                           add.push({ id: Date.now()+7, type:'critical', message:`⚕ Dataset flag: Sepsis positive row`,        ts });

    if (add.length) setAlerts(prev => [...add, ...prev].slice(0, 30));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(WS_URL);

    ws.onopen    = () => { setConnected(true); };
    ws.onmessage = ({ data: raw }) => {
      try {
        const data = JSON.parse(raw);
        setPatientData(data);
        setHistory(prev => {
          const pt = {
            time: new Date().toLocaleTimeString('en-US', {
              hour12: false, hour:'2-digit', minute:'2-digit', second:'2-digit'
            }),
            ...data.vitals,
            risk: data.risk.risk_score,
          };
          return [...prev, pt].slice(-MAX_POINTS);
        });
        checkAlerts(data);
      } catch (_) {}
    };
    ws.onclose   = () => {
      setConnected(false);
      retryRef.current = setTimeout(connect, 3000);
    };
    wsRef.current = ws;
  }, [checkAlerts]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return (
    <div className="min-h-screen bg-icu-dark p-4 md:p-6">
      {/* ── Header ── */}
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-7 h-7 text-vital-blue" />
          <h1 className="text-xl font-semibold text-white tracking-tight">ICU Patient Monitor</h1>
          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full ml-1">TCN · PhysioNet</span>
        </div>
        <div className="flex items-center gap-2">
          {connected
            ? <><Wifi      className="w-4 h-4 text-vital-green" /><span className="text-vital-green text-sm font-medium">Live</span></>
            : <><WifiOff   className="w-4 h-4 text-vital-red"   /><span className="text-vital-red   text-sm font-medium">Reconnecting…</span></>}
        </div>
      </header>

      {/* ── Connecting splash ── */}
      {!patientData && (
        <div className="flex items-center justify-center h-[60vh]">
          <div className="text-center">
            <div className="w-14 h-14 border-4 border-vital-blue border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-slate-300 font-medium">Connecting to patient stream…</p>
            <p className="text-slate-500 text-sm mt-1">Backend must be running on <code className="text-slate-400">localhost:8000</code></p>
          </div>
        </div>
      )}

      {/* ── Main grid ── */}
      {patientData && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Row 1 */}
          <div className="lg:col-span-4"><PatientInfo data={patientData} /></div>
          <div className="lg:col-span-4"><RiskGauge   score={patientData.risk.risk_score} level={patientData.risk.risk_level} /></div>
          <div className="lg:col-span-4"><LabValues   labs={patientData.labs} /></div>

          {/* Row 2 */}
          <div className="lg:col-span-8"><VitalsChart data={history} /></div>
          <div className="lg:col-span-4"><AlertsPanel alerts={alerts} onDismiss={id => setAlerts(p => p.filter(a => a.id !== id))} /></div>
        </div>
      )}
    </div>
  );
}
