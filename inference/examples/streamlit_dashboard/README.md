# AURA Inference Dashboard

A production Streamlit console for the AURA phishing-detection inference module.
It focuses on five capabilities:

| Page | What it does |
| --- | --- |
| **🔍 Predict** | Score a single email, inspect the 15 engineered features, and view three-zone classification. Defaults to the active model. |
| **📦 Batch Predict** | Score many emails from a CSV/JSON upload (or the built-in demo batches) with charts and CSV export. Defaults to the active model. |
| **🗂️ Model Management** | Full CRUD over registered versions — register, inspect, edit notes/metrics, activate/deactivate, verify integrity, delete. |
| **🧠 Online Learning** | Fine-tune via `partial_fit` from a labelled CSV, compare before/after metrics on a holdout, and promote with an F1-delta guard. |
| **🏁 Benchmarks** | Compare two or more versions on a labelled dataset, ranked oldest → newest with medals and per-metric winners. Every run is saved to JSON. |

## Running

From the `AURA_Model` directory (so the registry can find `models/`):

```bash
pip install -r inference/examples/streamlit_dashboard/requirements.txt
streamlit run inference/examples/streamlit_dashboard/app.py
```

If you launch from elsewhere, point the registry at your models directory:

```bash
export AURA_MODELS_DIR=/path/to/AURA_Model/models    # Windows: $env:AURA_MODELS_DIR
```

## Data formats

**The dashboard never auto-loads datasets from disk.** The only built-in data
is a small set of in-memory sample emails (used by the *Predict* page and the
*Demo batches* option on *Batch Predict*). For everything else you import your
own CSV / JSON files via the upload widget on each page. Every page also offers
a **template download** (generated in-memory) so you can see the exact expected
columns. Uploads are validated and any extra columns are dropped automatically.

- **Predict / Batch Predict** — `sender, subject, body` (a `label` column is
  optional and enables accuracy/confusion metrics).
- **Online Learning** — `sender, subject, body, label` (extra columns such as
  `category` are dropped).
- **Benchmarks** — `sender, subject, body, label`. Include **both** classes
  (1 = phishing, 0 = legitimate) for meaningful ROC-AUC / average precision;
  single-class uploads are accepted with a warning (those rank metrics show as
  `n/a`).

Sample datasets you can import live in `investigation/_datasets/` — e.g.
`demo_10_emails_a.csv`/`.json` (predictions), `train_buffer.csv` (online
learning), and `benchmark_v2.csv` (a balanced both-class benchmark set). These
are ordinary data files you browse to and upload; the app does not depend on
them existing.

## Defaults & behaviour

- **Active model is the default.** Predict and Batch Predict use the active
  model unless you explicitly pick another version. Manage the active pointer
  on **Model Management** (`Set as active` / `Deactivate`). With no active
  model, prediction falls back to the latest version on disk.
- **Online Learning mutates the registry.** Each run writes a new `models/v*`
  directory; the new version is *not* activated until you promote it.
- **Benchmark runs are persisted** to `dashboard_data/benchmarks/benchmark_<ts>.json`
  and can be re-inspected from the page or downloaded.

## Layout

```
streamlit_dashboard/
  app.py                  # home + sidebar
  theme.py                # CSS theme + reusable UI components
  utils.py                # registry/model loaders, upload parsing, persistence
  pages/
    01_Predict.py
    02_Batch_Predict.py
    03_Model_Management.py
    04_Online_Learning.py
    05_Benchmarks.py
```

Runtime artefacts (benchmark JSON) are written under `dashboard_data/` at the
repository root and are safe to delete.
