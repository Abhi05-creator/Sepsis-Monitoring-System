# backend/main.py
# ============================================================
# ICU Sepsis Monitoring — FastAPI Backend
# Serves:
#   POST /predict      — single-row sepsis risk score
#   WS   /stream       — streams sample_data.csv row by row, 1 row/sec
# ============================================================

import asyncio, json, os
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── TCN definition (must match training code) ───────────────
class ResidualBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel, dilation, dropout=0.2):
        super().__init__()
        pad = (kernel - 1) * dilation
        self.conv1 = nn.utils.parametrizations.weight_norm(
            nn.Conv1d(in_ch, out_ch, kernel, padding=pad, dilation=dilation))
        self.conv2 = nn.utils.parametrizations.weight_norm(
            nn.Conv1d(out_ch, out_ch, kernel, padding=pad, dilation=dilation))
        self.p    = pad
        self.drop = nn.Dropout(dropout)
        self.relu = nn.ReLU()
        self.down  = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None
        self.relu2 = nn.ReLU()

    def forward(self, x):
        def chomp(t, p): return t[:, :, :-p].contiguous() if p else t
        o = chomp(self.conv1(x), self.p)
        o = self.relu(o); o = self.drop(o)
        o = chomp(self.conv2(o), self.p)
        o = self.relu(o); o = self.drop(o)
        res = x if self.down is None else self.down(x)
        return self.relu2(o + res)

class TCN(nn.Module):
    def __init__(self, n_inputs, channels, kernel=3, dropout=0.2):
        super().__init__()
        layers = []
        for i, out_ch in enumerate(channels):
            in_ch = n_inputs if i == 0 else channels[i-1]
            layers.append(ResidualBlock(in_ch, out_ch, kernel, 2**i, dropout))
        self.net    = nn.Sequential(*layers)
        self.linear = nn.Linear(channels[-1], 1)

    def forward(self, x):
        x = x.transpose(1, 2)
        return self.linear(self.net(x)[:, :, -1])


# ── Globals ──────────────────────────────────────────────────
model          = None
scaler         = None
feature_cols   = None
window_size    = 24
streaming_data = None
# Per-patient rolling buffer: patient_id → deque of scaled rows
patient_windows: dict = {}

# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, scaler, feature_cols, window_size, streaming_data, patient_windows

    # Load model config
    cfg_path = "model_config.json"
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = json.load(f)
        feature_cols = cfg["feature_cols"]
        window_size  = cfg["window_size"]
        n_inputs     = cfg["n_inputs"]
        channels     = cfg["channels"]
    else:
        print("⚠  model_config.json not found — using defaults")
        feature_cols = [
            'HR','O2Sat','Temp','SBP','MAP','DBP','Resp','EtCO2',
            'BaseExcess','HCO3','FiO2','pH','PaCO2','SaO2','AST',
            'BUN','Alkalinephos','Calcium','Chloride','Creatinine',
            'Bilirubin_direct','Glucose','Lactate','Magnesium',
            'Phosphate','Potassium','Bilirubin_total','TroponinI',
            'Hct','Hgb','PTT','WBC','Fibrinogen','Platelets'
        ]
        window_size = 24; n_inputs = 34; channels = [64, 64, 64]

    # Load scaler
    if os.path.exists("scaler.pkl"):
        scaler = joblib.load("scaler.pkl")
        print("✓ scaler.pkl loaded")
    else:
        print("⚠  scaler.pkl not found — using identity scaler")
        from sklearn.preprocessing import StandardScaler as SS
        scaler = SS()
        dummy = np.random.randn(100, len(feature_cols))
        scaler.fit(dummy)

    # Load TCN model
    tcn = TCN(n_inputs=n_inputs, channels=channels)
    if os.path.exists("model.pt"):
        tcn.load_state_dict(torch.load("model.pt", map_location="cpu"))
        print("✓ model.pt loaded")
    else:
        print("⚠  model.pt not found — using random weights (predictions will be random)")
    tcn.eval()
    model = tcn

    # Init patient window buffers
    patient_windows = {}

    # Load streaming CSV
    if os.path.exists("sample_data.csv"):
        streaming_data = pd.read_csv("sample_data.csv")
        # Fill any NaNs with column mean
        for col in feature_cols:
            if col in streaming_data.columns:
                streaming_data[col] = streaming_data[col].fillna(
                    streaming_data[col].mean())
        print(f"✓ sample_data.csv loaded — {len(streaming_data)} rows")
    else:
        print("⚠  sample_data.csv not found — generating synthetic data")
        streaming_data = _synthetic_stream(500)

    yield
    print("Shutdown.")


def _synthetic_stream(n=500) -> pd.DataFrame:
    np.random.seed(42)
    data = {
        'patient_id': [f"P{(i%10):03d}" for i in range(n)],
        'HR':   np.random.normal(80,20,n).clip(50,150).astype(int),
        'O2Sat':np.random.normal(96, 3,n).clip(85,100).astype(int),
        'Temp': np.round(np.random.normal(37,0.8,n).clip(35.5,40),1),
        'SBP':  np.random.normal(120,20,n).clip(80,180).astype(int),
        'MAP':  np.random.normal(85,15,n).clip(55,130).astype(int),
        'DBP':  np.random.normal(75,12,n).clip(50,110).astype(int),
        'Resp': np.random.normal(16, 4,n).clip(10, 35).astype(int),
        'EtCO2':np.random.normal(35, 5,n).clip(20, 50).astype(float),
        'Lactate':np.round(np.random.exponential(2,n).clip(0.5,12),1),
        'Creatinine':np.round(np.random.exponential(1.2,n).clip(0.4,8),1),
        'WBC':  np.round(np.random.normal(9,4,n).clip(2,25),1),
        'Glucose':np.random.normal(110,40,n).clip(60,350).astype(int),
        'Platelets':np.random.normal(220,80,n).clip(50,450).astype(int),
        'Age':  np.random.normal(62,15,n).clip(20,90).astype(int),
        'Gender':np.random.randint(0,2,n),
        'ICULOS':np.arange(1,n+1)%72+1,
        'SepsisLabel': np.zeros(n,dtype=int),
    }
    # fill remaining feature cols with zeros
    for col in [
        'BaseExcess','HCO3','FiO2','pH','PaCO2','SaO2','AST','BUN',
        'Alkalinephos','Calcium','Chloride','Bilirubin_direct','Magnesium',
        'Phosphate','Potassium','Bilirubin_total','TroponinI','Hct','Hgb',
        'PTT','Fibrinogen'
    ]:
        data[col] = np.zeros(n)
    return pd.DataFrame(data)


# ── FastAPI app ───────────────────────────────────────────────
app = FastAPI(title="ICU Sepsis Monitor API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic schemas ─────────────────────────────────────────
class VitalsInput(BaseModel):
    HR: float; O2Sat: float; Temp: float; SBP: float; MAP: float
    DBP: float = 75; Resp: float; Lactate: float; Creatinine: float; WBC: float
    EtCO2: float = 35; BaseExcess: float = 0; HCO3: float = 24
    FiO2: float = 0.21; pH: float = 7.4; PaCO2: float = 40; SaO2: float = 97
    AST: float = 25; BUN: float = 15; Alkalinephos: float = 80
    Calcium: float = 9; Chloride: float = 100; Bilirubin_direct: float = 0.2
    Magnesium: float = 2; Phosphate: float = 3.5; Potassium: float = 4
    Bilirubin_total: float = 0.6; TroponinI: float = 0.01
    Hct: float = 38; Hgb: float = 12; PTT: float = 30
    Fibrinogen: float = 300


# ── Helper: predict from a single row dict ───────────────────
def _predict_row(row_dict: dict) -> dict:
    values = [float(row_dict.get(c, 0) or 0) for c in feature_cols]
    scaled = scaler.transform([values])         # (1, F)

    # Use last window_size rows if buffer available, else repeat the row
    pid = str(row_dict.get("patient_id", "P000"))
    buf = patient_windows.get(pid, [])
    buf = buf + [scaled[0]]
    if len(buf) < window_size:
        # pad left with first available row
        buf = [buf[0]] * (window_size - len(buf)) + buf
    buf = buf[-window_size:]
    patient_windows[pid] = buf[-window_size:]

    x = torch.tensor([buf], dtype=torch.float32)   # (1, T, F)
    with torch.no_grad():
        logit = model(x)
        prob  = torch.sigmoid(logit).item()

    score = int(prob * 100)
    level = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
    return {"risk_score": score, "risk_level": level, "probability": round(prob, 4)}


# ── Endpoints ─────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "model": "TCN (PhysioNet Sepsis)"}

@app.get("/health")
async def health():
    return {
        "model_loaded": model is not None,
        "records": len(streaming_data) if streaming_data is not None else 0,
        "feature_cols": len(feature_cols) if feature_cols else 0,
        "window_size": window_size,
    }

@app.post("/predict")
async def predict(vitals: VitalsInput):
    return _predict_row(vitals.model_dump())


# ── WebSocket streaming ────────────────────────────────────────
@app.websocket("/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    idx = 0
    try:
        while True:
            row = streaming_data.iloc[idx % len(streaming_data)].to_dict()
            pid = str(row.get("patient_id", f"P{(idx%10):03d}"))

            # Add small realistic variation to continuous vitals
            prev = patient_windows.get(pid)
            if prev:
                last_unscaled = scaler.inverse_transform([prev[-1]])[0]
                def jitter(i, std, lo, hi):
                    v = last_unscaled[i] + np.random.normal(0, std)
                    return float(np.clip(v, lo, hi))
                hr_i  = feature_cols.index('HR')
                o2_i  = feature_cols.index('O2Sat')
                tmp_i = feature_cols.index('Temp')
                sbp_i = feature_cols.index('SBP')
                rsp_i = feature_cols.index('Resp')
                row['HR']    = round(jitter(hr_i,  3,  40, 180))
                row['O2Sat'] = round(jitter(o2_i,  1,  70, 100))
                row['Temp']  = round(jitter(tmp_i, .1, 35,  41), 1)
                row['SBP']   = round(jitter(sbp_i, 5,  70, 200))
                row['Resp']  = round(jitter(rsp_i, 1,   8,  40))

            row['patient_id'] = pid
            risk = _predict_row(row)

            payload = {
                "timestamp": pd.Timestamp.now().isoformat(),
                "patient_id": pid,
                "vitals": {
                    "HR":    int(row.get("HR", 80)),
                    "O2Sat": int(row.get("O2Sat", 97)),
                    "Temp":  float(row.get("Temp", 37.0)),
                    "SBP":   int(row.get("SBP", 120)),
                    "MAP":   int(row.get("MAP", 85)),
                    "DBP":   int(row.get("DBP", 75)),
                    "Resp":  int(row.get("Resp", 16)),
                },
                "labs": {
                    "Lactate":    round(float(row.get("Lactate",    1.5) or 0), 1),
                    "Creatinine": round(float(row.get("Creatinine", 1.0) or 0), 1),
                    "WBC":        round(float(row.get("WBC",        8.0) or 0), 1),
                    "Glucose":    int(row.get("Glucose",   100) or 100),
                    "Platelets":  int(row.get("Platelets", 220) or 220),
                },
                "demographics": {
                    "Age":    int(row.get("Age",    65) or 65),
                    "Gender": int(row.get("Gender",  1) or 1),
                    "ICULOS": int(row.get("ICULOS", 24) or 24),
                },
                "risk": risk,
                "ground_truth": int(row.get("SepsisLabel", 0) or 0),
            }
            await ws.send_json(payload)
            idx += 1
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
