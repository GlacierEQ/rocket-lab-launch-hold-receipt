# Launch Hold Receipt

Independent GlacierEQ portfolio implementation aligned to **Rocket Lab** operating themes.

> **Not affiliated.** This repository is not affiliated with, endorsed by, employed by, or deployed at Rocket Lab. No proprietary access, production deployment, customer impact, or company partnership is claimed.

## Purpose

Represent mission/release holds as verifiable state, not chat or checklist folklore. A hold must identify its authority, scope, reasons, evidence, issue time, and expiry; progression remains blocked until the exact hold expires or receives a correctly bound clearance.

## Implemented protocol

`LaunchHoldReceipt` supports three transitions:

- **issue**: authorized authority signs an HMAC-bound hold over scope, reason codes, evidence digest, issue time and expiry;
- **clear**: an authority permitted for that scope signs a clearance bound to the exact hold signature and new evidence;
- **check**: verifies signatures and binding, then returns `BLOCKED`, `CLEARED`, or `EXPIRED`.

It fails closed on unauthorized scope, missing signing authority, invalid signatures, bad expiry ordering, clearance mismatch, future clearance, and malformed evidence.

## Run

```bash
python -m pytest -q
python scripts/operate.py
```

Build/install:

```bash
python -m pip install build
python -m build
python -m pip install dist/*.whl
launch-hold-receipt
```

## Proof surface

- `src/launch_hold_receipt.py` — signed hold/clear/check protocol
- `src/launch_hold_cli.py` — installable demo execution surface
- `tests/test_launch_hold_receipt.py` — authority, block, expiry, clearance and tamper behavior
- `.github/workflows/tests.yml` — tests + cold-start + wheel build/install + installed CLI
- `machine/` — existing Helix control-plane/promotion surfaces remain preserved

## Current boundary

This is a vendor-neutral protocol using injected authority secrets/scopes. It does not control Rocket Lab systems or claim flight use. A further deployment step is a permitted release/simulation orchestrator adapter that refuses stage progression while a verified hold is active.
