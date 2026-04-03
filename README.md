# ICU Sepsis Monitoring System — Setup Guide
**Stack:** PhysioNet PSV dataset → TCN (PyTorch) → FastAPI WebSocket → React + Recharts

---

## Project structure
```
icu-monitoring-system/
├── ml-pipeline/
│   └── sepsis_model_tcn.py       ← train the model here
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── model.pt                  ← copied from ml-pipeline after training
│   ├── scaler.pkl                ← copied from ml-pipeline after training
│   ├── model_config.json         ← copied from ml-pipeline after training
│   └── sample_data.csv           ← copied from ml-pipeline after training
└── frontend/
    └── src/
        ├── App.jsx
        ├── index.css
        ├── main.jsx
        └── components/
            ├── PatientInfo.jsx
            ├── RiskGauge.jsx
            ├── VitalsChart.jsx
            ├── AlertsPanel.jsx
            └── LabValues.jsx
```

---

## STEP 1 — Get the dataset

1. Go to: https://www.kaggle.com/datasets/salikhussaini49/prediction-of-sepsis
2. Download and unzip — you'll get `training_setA/` and `training_setB/` folders of `.psv` files.
3. If running on Kaggle, the path is already `/kaggle/input/prediction-of-sepsis/`.
4. If running locally, set `BASE_PATH` in `sepsis_model_tcn.py` to your local path.

---

## STEP 2 — Train the model

```bash
cd ml-pipeline

# Create virtualenv (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install torch scikit-learn pandas numpy joblib matplotlib seaborn tqdm

# Run training (takes ~10 min on CPU, ~3 min on GPU)
python sepsis_model_tcn.py
```

This produces 4 files in `ml-pipeline/`:
- `model.pt`
- `scaler.pkl`
- `model_config.json`
- `sample_data.csv`

Copy them to the backend:
```bash
cp model.pt scaler.pkl model_config.json sample_data.csv ../backend/
```

---

## STEP 3 — Run the backend

```bash
cd backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Test it:
- http://localhost:8000/          → status
- http://localhost:8000/health    → model loaded check
- http://localhost:8000/docs      → Swagger UI (test /predict manually)

---

## STEP 4 — Run the frontend

```bash
cd frontend

# Scaffold with Vite
npm create vite@latest . -- --template react
# Press Enter to overwrite (or scaffold into a new folder first)

npm install recharts lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Now replace these files with the ones provided:
- `tailwind.config.js`   ← from configs.js comments
- `vite.config.js`       ← from configs.js comments
- `postcss.config.js`    ← from configs.js comments
- `src/index.css`
- `src/main.jsx`         ← standard Vite React boilerplate (unchanged)
- `src/App.jsx`
- `src/components/PatientInfo.jsx`
- `src/components/RiskGauge.jsx`
- `src/components/VitalsChart.jsx`
- `src/components/AlertsPanel.jsx`
- `src/components/LabValues.jsx`

Start:
```bash
npm run dev
```

Open: http://localhost:3000

---

## STEP 5 — Run both together

**Terminal 1 (backend):**
```bash
cd backend && source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (frontend):**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** — you should see the dashboard connect and start streaming real PhysioNet rows with live TCN risk predictions within 2–3 seconds.

---

## What you'll see

| Feature | Description |
|---|---|
| Patient card | Cycles through 10 virtual patients (P000–P009), shows Age/Gender/ICULOS from dataset |
| Risk gauge | TCN model outputs probability; score 0–100% with color coding |
| Sepsis+ badge | Appears when the streamed row has `SepsisLabel = 1` in the real data |
| Vitals charts | HR, SpO₂, Temp, Resp, SBP — last 60 seconds, toggleable |
| Lab values | Lactate, Creatinine, WBC, Glucose, Platelets — color-coded by clinical range |
| Alerts | Auto-generated when thresholds are crossed (HR>100, SpO₂<92, Temp>38, risk>70%) |

---

## Troubleshooting

**Backend won't start:**
- `pip install torch` can be large; on CPU install `torch==2.3.0+cpu` via:
  `pip install torch==2.3.0 --index-url https://download.pytorch.org/whl/cpu`

**"model.pt not found" warning:**
- Backend falls back to random weights automatically — streaming still works, predictions will be random.
- Copy the trained files from `ml-pipeline/` to `backend/`.

**WebSocket disconnects immediately:**
- Check that backend is on port 8000 and CORS is enabled (it is in main.py).
- Look at browser console → Network → WS tab for error details.

**Training OOM on Kaggle/local:**
- Reduce `limit=5000` to `limit=1000` in `load_psv_folders()`.
- Reduce `WINDOW_SIZE = 24` to `12`.
- Reduce channels from `[64,64,64]` to `[32,32,32]`.

---

## Model details

| Parameter | Value |
|---|---|
| Architecture | Temporal Convolutional Network (TCN) |
| Input | 34 clinical features (PhysioNet schema) |
| Window | 24-hour sliding window |
| Channels | [64, 64, 64] with dilated residual blocks |
| Loss | BCEWithLogitsLoss with pos_weight (class imbalance) |
| Output | Probability of sepsis within the window |
| Typical AUROC | 0.82–0.88 on val set |
