# ============================================================
# ICU Sepsis Prediction — TCN ML Pipeline
# Run this as a Jupyter notebook or plain Python script.
# Requires: pip install torch scikit-learn pandas numpy joblib matplotlib seaborn tqdm
# Dataset: https://www.kaggle.com/datasets/prediction-of-sepsis
#           Place training_setA/ and training_setB/ under BASE_PATH
# ============================================================

# %% Cell 1 — Imports
import os, joblib
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, roc_curve,
                             precision_recall_curve, auc,
                             accuracy_score, f1_score,
                             confusion_matrix, classification_report)
from torch.utils.data import DataLoader, TensorDataset
import matplotlib.pyplot as plt
import seaborn as sns

# ── Paths ────────────────────────────────────────────────────
# BASE_PATH = 'C:/Users/Abhijit/Desktop/Sepsis/dataset'  # ← change if running locally
BASE_PATH = r'C:\Users\Abhijit\Desktop\Sepsis\dataset'

FEATURE_COLS = [
    'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'EtCO2',
    'BaseExcess', 'HCO3', 'FiO2', 'pH', 'PaCO2', 'SaO2', 'AST',
    'BUN', 'Alkalinephos', 'Calcium', 'Chloride', 'Creatinine',
    'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium',
    'Phosphate', 'Potassium', 'Bilirubin_total', 'TroponinI',
    'Hct', 'Hgb', 'PTT', 'WBC', 'Fibrinogen', 'Platelets'
]
TARGET_COL = 'SepsisLabel'
WINDOW_SIZE = 24   # hours of history per sample
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {DEVICE}")


# %% Cell 2 — Load data from PSV folders
def load_psv_folders(base_path: str, limit: int = 5000) -> pd.DataFrame:
    folders = ['training_setA', 'training_setB']
    dfs = []
    for folder in folders:
        path = os.path.join(base_path, folder)
        if not os.path.isdir(path):
            print(f"⚠  Folder not found: {path} — skipping")
            continue
        files = sorted(f for f in os.listdir(path) if f.endswith('.psv'))[:limit]
        print(f"Loading {len(files)} patients from {folder}…")
        for fname in tqdm(files):
            df = pd.read_csv(os.path.join(path, fname), sep='|')
            df = df.ffill()                        # forward-fill per patient
            dfs.append(df[FEATURE_COLS + [TARGET_COL]])
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.fillna(combined.mean(numeric_only=True))
    return combined


df_raw = load_psv_folders(BASE_PATH, limit=5000)
print(f"Total rows: {df_raw.shape[0]}  |  Sepsis prevalence: {df_raw[TARGET_COL].mean():.2%}")


# %% Cell 3 — Scale features and create sliding windows
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_raw[FEATURE_COLS].values)
y_all    = df_raw[TARGET_COL].values

def create_windows(X, y, window: int = 24):
    Xw, yw = [], []
    for i in tqdm(range(len(X) - window)):
        Xw.append(X[i:i+window])
        yw.append(y[i+window-1])
    return np.array(Xw, dtype=np.float32), np.array(yw, dtype=np.float32)

print("Creating windows…")
X, y = create_windows(X_scaled, y_all, WINDOW_SIZE)
print(f"X: {X.shape}  y: {y.shape}  positives: {y.mean():.2%}")

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2,
                                                   random_state=42, stratify=y)

train_loader = DataLoader(TensorDataset(torch.from_numpy(X_train),
                                        torch.from_numpy(y_train)),
                          batch_size=64, shuffle=True)
val_loader   = DataLoader(TensorDataset(torch.from_numpy(X_val),
                                        torch.from_numpy(y_val)),
                          batch_size=64, shuffle=False)


# %% Cell 4 — TCN model definition
class ResidualBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel, dilation, dropout=0.2):
        super().__init__()
        pad = (kernel - 1) * dilation
        self.conv1 = nn.utils.parametrizations.weight_norm(
            nn.Conv1d(in_ch, out_ch, kernel, padding=pad, dilation=dilation))
        self.conv2 = nn.utils.parametrizations.weight_norm(
            nn.Conv1d(out_ch, out_ch, kernel, padding=pad, dilation=dilation))
        self.chomp = lambda x, p: x[:, :, :-p].contiguous() if p else x
        self.p = pad
        self.drop = nn.Dropout(dropout)
        self.relu = nn.ReLU()
        self.down  = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None
        self.relu2 = nn.ReLU()

    def forward(self, x):
        o = self.chomp(self.conv1(x), self.p)
        o = self.relu(o); o = self.drop(o)
        o = self.chomp(self.conv2(o), self.p)
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

    def forward(self, x):            # x: (B, T, C)
        x = x.transpose(1, 2)       # → (B, C, T)
        return self.linear(self.net(x)[:, :, -1])


model = TCN(n_inputs=len(FEATURE_COLS), channels=[64, 64, 64]).to(DEVICE)
print(model)


# %% Cell 5 — Train
pos_weight = torch.tensor([(y_train == 0).sum() / (y_train == 1).sum()]).to(DEVICE)
criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
optimizer  = torch.optim.Adam(model.parameters(), lr=1e-3)

EPOCHS = 10
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for xb, yb in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS}"):
        xb, yb = xb.to(DEVICE), yb.to(DEVICE).unsqueeze(1)
        optimizer.zero_grad()
        loss = criterion(model(xb), yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for xb, yb in val_loader:
            prob = torch.sigmoid(model(xb.to(DEVICE))).cpu().numpy()
            preds.extend(prob); targets.extend(yb.numpy())
    auc_score = roc_auc_score(targets, preds)
    print(f"  loss={total_loss/len(train_loader):.4f}  val-AUROC={auc_score:.4f}")


# %% Cell 6 — Evaluation plots
val_preds_bin = (np.array(preds) >= 0.5).astype(int)
fpr, tpr, _   = roc_curve(targets, preds)
prec, rec, _  = precision_recall_curve(targets, preds)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].plot(fpr, tpr, color='darkorange', lw=2, label=f"AUROC={auc(fpr,tpr):.3f}")
axes[0].plot([0,1],[0,1],'--',color='navy')
axes[0].set(xlabel='FPR', ylabel='TPR', title='ROC Curve')
axes[0].legend()

axes[1].plot(rec, prec, color='blue', lw=2, label=f"PR-AUC={auc(rec,prec):.3f}")
axes[1].set(xlabel='Recall', ylabel='Precision', title='Precision-Recall')
axes[1].legend()

cm = confusion_matrix(targets, val_preds_bin)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[2],
            xticklabels=['No Sepsis','Sepsis'], yticklabels=['No Sepsis','Sepsis'])
axes[2].set(xlabel='Predicted', ylabel='Actual', title='Confusion Matrix')

plt.tight_layout(); plt.savefig('evaluation.png', dpi=150); plt.show()
print(classification_report(targets, val_preds_bin, target_names=['No Sepsis','Sepsis']))


# %% Cell 7 — Save model artifacts
torch.save(model.state_dict(), 'model.pt')
joblib.dump(scaler, 'scaler.pkl')

# Save model architecture config so backend can reload it
import json
config = {'n_inputs': len(FEATURE_COLS), 'channels': [64,64,64],
          'kernel': 3, 'dropout': 0.2, 'window_size': WINDOW_SIZE,
          'feature_cols': FEATURE_COLS}
with open('model_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Saved: model.pt  scaler.pkl  model_config.json")


# %% Cell 8 — Export streaming CSV (500 real rows)
# We export individual HOURLY readings — NOT windows — so the backend can replay them.
streaming_df = df_raw[FEATURE_COLS + [TARGET_COL]].head(500).copy()

# Add synthetic patient IDs cycling over 10 patients
streaming_df.insert(0, 'patient_id',
    [f"P{(i % 10):03d}" for i in range(len(streaming_df))])

# Add demographics (not in core feature set but shown on UI)
streaming_df['Age']    = np.random.randint(40, 85, len(streaming_df))
streaming_df['Gender'] = np.random.randint(0, 2,  len(streaming_df))
streaming_df['ICULOS'] = np.arange(1, len(streaming_df)+1) % 72 + 1

streaming_df.to_csv('sample_data.csv', index=False)
print(f"Saved sample_data.csv  ({len(streaming_df)} rows)")
print("Copy model.pt, scaler.pkl, model_config.json, sample_data.csv → backend/")