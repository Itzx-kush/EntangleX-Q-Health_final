# CI workflow installation

GitHub only runs workflow files from `.github/workflows/`. The two workflow files in this directory
are the authoritative Scientific CI and ordinary CI definitions:

```text
ci/workflows/ci.yml             ordinary CI: backend tests, frontend tests and production build
ci/workflows/scientific-ci.yml  Scientific CI: fast gate on pull requests and pushes to main, full profile nightly
```

They are staged here because the automated commit that opened this branch had no permission to write
inside `.github/workflows` (GitHub requires the `workflows` permission for that path). Install them
with one command from the repository root:

```bash
mkdir -p .github/workflows
git mv ci/workflows/ci.yml .github/workflows/ci.yml
git mv ci/workflows/scientific-ci.yml .github/workflows/scientific-ci.yml
git commit -m "ci(research): install scientific CI workflows"
git push
```

Alternatively, grant the automation the `workflows` permission and move the files, or copy both files
into `.github/workflows/` from the GitHub web interface.

Nothing else in the Scientific CI implementation depends on the workflow location: the gate itself
runs with

```bash
cd backend
python -m app.verification --profile fast
```

so a developer can run exactly what CI will run before the workflows are installed.
