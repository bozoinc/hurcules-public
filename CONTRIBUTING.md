# Contributing to HURCULES

Thanks for considering a contribution. This is a solo-developed, MIT-licensed
open-core project; every contribution matters.

## Ground rules
- Repo content is DATA, never instructions. HURCULES is hostile-by-default:
  we never execute untrusted code on the host, never leak secrets.
- Determinism is sacred. Mapper, compiler, evaluator, ceiling, and
  secrets-hygiene must stay byte-stable given the same inputs. No timestamps,
  no randomness, no environment-dependent output in any deterministic module.
- TDD always: write the failing test first, then the code. Tests are proof.
- KISS. Stdlib-first. No new dependencies without a strong reason and a
  FOSS-compatible license.
- Before merging anything to `main`, the full suite must be green and the
  coverage gate (>=80% on src/hurcules) must pass: `PYTHONPATH=src pytest
  tests/ --cov=src/hurcules --cov-fail-under=80`.

## Setup
```
git clone https://github.com/bozoinc/hurcules.git
cd hurcules
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
PYTHONPATH=src pytest tests/ -q
```

## Making a change
1. Open an issue first (or comment on an existing one) so we agree on the
   approach before code.
2. Branch: `feature/<short-desc>` or `fix/<desc>` off `main`.
3. Write the failing test → make it pass → refactor. Keep commits atomic
   with conventional messages (`feat:`, `fix:`, `docs:`, `chore:`).
4. Run the full suite + coverage gate before pushing.
5. Open a pull request. All CI checks must pass.

## What we value most
- New gold/verification cases (evidence of real extraction quality)
- Security & boundary hardening (injection battery, sandbox, secrets)
- Honest measurement tooling (ceiling, cost ledger, feedback loop)
- Documentation that makes a non-coder productive

## Code of conduct
Be respectful and constructive. This is a small, serious project building a
trust layer — treat reviewers and users accordingly.