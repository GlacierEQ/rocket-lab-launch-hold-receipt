# DEV_UP_INSTRUCTIONS — implementation record

**Repository:** `GlacierEQ/rocket-lab-launch-hold-receipt`  
**Independent company lens:** Rocket Lab  
**Innovation:** Launch Hold Receipt

## Implemented

The scaffold has been replaced by a signed hold lifecycle. The mechanism issues authority/scope-bound HMAC hold receipts, requires explicit reason/evidence/expiry, blocks progression while active, accepts only correctly bound clearance receipts, exposes expiry, and fails closed on signature or authority defects.

`src/launch_hold_cli.py` and `scripts/operate.py` execute the real protocol. The project is packaged with `launch-hold-receipt`.

## Verification contract

Behavioral tests cover authorized issue, scope denial, active blocking, expiry, authorized clearance, signature tampering, cross-hold clearance mismatch, and invalid expiry ordering. Existing adversarial coverage remains active.

CI must pass tests, cold-start, wheel build/install and installed CLI execution before any Helix promotion evidence is minted.

## Truth boundary

No Rocket Lab affiliation, proprietary access, production deployment, customer impact, or flight-use claim is made. A permitted release/simulation adapter remains a further deployment depth step.
