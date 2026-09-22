# EntangleX Q-Health — Technical Approach

The SIH 2026 architecture slide is available at [`technical_approach.html`](./technical_approach.html). Open the HTML directly in a browser for the 16:9 presentation view.

The diagram follows the repository architecture: React/TypeScript/Vite → same-origin `/api` → FastAPI routers and strict Pydantic schemas → services/repositories → SQLite registries → single-process bounded worker → shared fold-local pipelines → classical or quantum estimators → measured evaluation, explanations, research predictions, and HTML/JSON reports.

## Run frontend and backend together on Windows PowerShell

From the repository root:

```powershell
.\scripts\run_qhealth.ps1
```

Or run the two commands manually in separate PowerShell windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

```powershell
Set-Location .\frontend; npm run dev -- --host 127.0.0.1
```

Frontend: `http://127.0.0.1:5173`  
Backend health: `http://127.0.0.1:8000/api/health`

The WDBC dataset is presented as a research benchmark, not evidence of prospective early detection. Quantum execution is local simulation; the slide does not claim quantum advantage, real-hardware execution, or clinical validation.
