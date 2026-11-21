# Reviewing the EntangleX frontend

The implementation targets the existing 22 workspace routes. The default branch at the start of the review was `3be3a54`. Screenshots pair that baseline with the isolated production build. Settings uses the baseline production bundle in the same dark theme. All example records used for private-account checks were local fixtures.

## Reviewer walkthrough

1. Open the homepage. Select each research path in the diagram, then try the interactive preview. Switch between 2Q and 4Q and expand the example code.
2. Choose **Open verified SIH demo** and continue as a guest. The address stays on `/demo`. Expand the evidence context to inspect the dataset and experiment.
3. Choose **Explore model evidence**. Filter to the quantum family. Compare Performance, Metric matrix, CV stability and Runtime, then inspect the corresponding numbers.
4. Open **Quantum Lab**. Move through the fitted circuit with the arrow keys. Inspect the selected operation and qubits. The separate simulation control explicitly requests state data.
5. Open **Settings**, change theme and density, reload, then reset appearance. On a phone use **More** to reach the full navigation.

## Browser coverage

| Route or surface | Exercised |
| --- | --- |
| Public entry, preview, methodology, access | Inspected the pathway branches, both register presets, code, calculated outputs, tab keyboard navigation, mobile navigation and guest entry. Tested clipboard failure and success in the component suite. |
| Overview | Opened the registry overview, benchmark navigation and all three research guide tabs. |
| Datasets, Quality | Visited the registry, quality findings and class distributions. Inspected a 20-row CSV successfully and exercised the validation response for a six-row file. Opened the underlying chart values. |
| Preprocessing, Features, PCA | Checked the active-registry and verified-package variants. Opened fitted preprocessing, selection records, explained variance and signed loadings. |
| Training | Checked the active draft and packaged model set. The component suite also exercised model configuration and resource controls. |
| Comparison | Switched all four analysis views, metric and family filters. Checked the seven-model display, family encoding, CV folds, runtime units and numeric alternatives. |
| Robustness, Explainability, Prediction | Opened packaged evidence and active-registry variants. Switched representative prediction cases. Component tests exercised live-request and missing-evidence behavior. |
| Quantum Lab | Opened the fitted demo circuit, inspected gates with the keyboard, zoomed and fitted the diagram. In an empty workspace, requested a structural preview, explicitly ran a local Qiskit simulation and visited every returned state tab. |
| Experiments, experiment detail, SIH Demo Center | Opened the registry and the real bundled experiment, inspected provenance and missing artifacts, and followed the guest judge journey. |
| Account, My Research, saved reports, report detail | Checked guest boundaries and private views. The signed-in browser used an isolated identity, history and saved-report fixture. The unit suite covered save, download and delete behavior. |
| AI Assistant, Redis Lab | Opened the tools in the local environment. Checked the unavailable-service interfaces and keyboard access to the assistant. |
| Settings, navigation and overlays | Checked preference persistence and reset, system theme, command search, quick settings, context inspector, account menu, mobile More sheet and focus restoration. |

Every route opened on a 1440px desktop and a 360px phone. Comparison, Quantum Lab and Settings also ran at 768px. All 22 routes ran again in system dark mode with reduced motion. The desktop and phone route sweeps recorded no page-level JavaScript exceptions or horizontal page overflow. The reflow check also applied 200% CSS zoom. Long hashes have a copy action and a disclosure. Wide tables and circuit canvases scroll inside their panels.

## Verification results

- Node 22.12.0. `cd frontend && npm test -- --maxWorkers 3` passed 213 tests in 40 files, including the API and workflow contracts. `npm run build` passed the TypeScript and Vite production builds.
- `cd backend && python -m pytest -q tests/test_quantum_visualization.py tests/test_verified_demo_evidence_context.py` passed 22 tests against local storage. An explicit browser simulation returned probability, amplitude, phase, Bloch and measurement views.
- The browser kept precomputed comparisons accessible during an injected system-status 503. A missing evidence response showed the recovery view. Clipboard rejection, stale quantum responses, session preferences and OAuth return destinations have focused regression checks.
- Automated axe scans used WCAG A and AA rule tags through 2.2. No violations were reported on the public home, access, comparison, dark Settings, or the seven additional dark screens checked (Datasets, PCA, Quantum Lab, Prediction, Demo, AI and Redis). Coverage is Chromium plus automated and keyboard checks. Full assistive-technology certification and Safari/Firefox testing were outside the completed verification.
- The public JavaScript entry fell from 372.40 kB to 119.55 kB gzip. The public CSS entry fell from 74.18 kB to 20.67 kB gzip. The existing scientific chart dependencies load with the workspace. Vite still reports a workspace chunk just over its 500 kB uncompressed warning threshold.
- Review assets are outside the deployed frontend bundle. The diff contains only frontend changes. The review used the existing API endpoints, scientific fixtures and deployment contract.

## Service-dependent checks

Real OAuth provider login and third-party AI responses were not exercised. The OAuth handoff preserved the original route and query in a local provider stand-in. The saved-report and history views used authenticated fixtures. The local packaged experiment had no separate per-run quantum diagnostic, dataset-quality record or immutable evidence-package record. Its evidence-package preflight endpoint also returned HTTP 500. The frontend displays those states and keeps the packaged comparison and circuit available.
