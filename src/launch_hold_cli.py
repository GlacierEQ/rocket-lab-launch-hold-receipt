from __future__ import annotations

import argparse
import json
from pathlib import Path

from launch_hold_receipt import Decision, LaunchHoldReceipt, LaunchHoldReceiptRequest


def demo_payload() -> dict:
    return {"mode":"issue","hold_id":"hold-demo","authority_id":"flight-safety","scope":"launch","reason_codes":["telemetry_anomaly"],"issued_at":100.0,"expires_at":200.0,"evidence":[{"sensor":"pressure","state":"investigating"}]}


def main() -> int:
    p=argparse.ArgumentParser(description="Issue, clear, or verify a signed launch hold")
    p.add_argument("--input",type=Path)
    p.add_argument("--subject",default="mission-demo")
    args=p.parse_args()
    payload=json.loads(args.input.read_text()) if args.input else demo_payload()
    mech=LaunchHoldReceipt(authority_secrets={"flight-safety":b"demo-flight-secret","mission-director":b"demo-mission-secret"},authority_scopes={"flight-safety":{"launch"},"mission-director":{"launch","test"}})
    receipt=mech.evaluate(LaunchHoldReceiptRequest(args.subject,payload,1.0))
    print(json.dumps(receipt.as_dict(),indent=2,sort_keys=True))
    return 0 if receipt.decision is Decision.ALLOW else 2

if __name__=="__main__":
    raise SystemExit(main())
