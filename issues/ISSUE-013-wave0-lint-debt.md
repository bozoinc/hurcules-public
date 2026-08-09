# Wave 0 — CI lint debt + determinism path note

Parent: HURCULES Update-1 Wave 0 ([19] CI, [12] determinism)
Status: OPEN (tracked debt, not Wave 0 scope)

## Lint debt
Full `ruff check` reports 90 errors across src/ scripts/ tests/
(import sorting I001, unused imports F401, subprocess.run without check
PLW1510, combine-if SIM114, unused vars F841, unused Path import).

CI gates on the fatal set only (E9, F63, F7, F82 — syntax errors, undefined
names, invalid bytecode) which passes 0 errors. The full-style cleanup is
deliberately deferred: it would touch every file and risk the 95 passing
tests. Do it as its own pass with TDD coverage, not mixed into feature work.

## Determinism path note
`mapper.repository` embeds the absolute clone path (an environment artifact,
not repo content). `scripts/check_determinism.py` normalizes it to a fixed
token before hashing; consumers still receive the real path for provenance.
If the mapper ever outputs a *stable* repo id (e.g. origin URL + commit SHA),
this normalization can be dropped and the digest tightened.