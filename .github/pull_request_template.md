## What changed

<!-- One sentence. -->

## Why

## Verification

- [ ] `python tests/test_proxy_e2e.py` passes (paste the count)
- [ ] `pre-commit run --all-files` passes
- [ ] Started the proxy and made one real request (if behavior change)

## Risk

- [ ] Touches auth, network binding, or logging → **re-review `docs/threat-model.md`**
- [ ] Touches `MODEL_MAP`, `MODEL_CHAINS`, or model allowlist → **add a smoke test**
- [ ] No secrets, keys, or `G:\private\*` contents in this diff

## Docs

- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New architectural decision → added an ADR under `docs/adr/`
- [ ] Skill added or changed → updated `.harness/HARNESS.md`

## For non-trivial changes

- [ ] `Test-ClaudeMiniMaxSetup.ps1` runs cleanly against a real MiniMax key
- [ ] `Watch-ClaudeMiniMaxProxy.ps1` is still happy (proxy stays up, `/readyz` returns 200)