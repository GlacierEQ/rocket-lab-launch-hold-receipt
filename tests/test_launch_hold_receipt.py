from __future__ import annotations

from launch_hold_receipt import Decision, LaunchHoldReceipt, LaunchHoldReceiptRequest


SECRETS = {"flight-safety": b"flight-secret", "mission-director": b"mission-secret", "observer": b"observer-secret"}
SCOPES = {"flight-safety": {"launch"}, "mission-director": {"launch", "test"}, "observer": {"read"}}


def mech() -> LaunchHoldReceipt:
    return LaunchHoldReceipt(authority_secrets=SECRETS, authority_scopes=SCOPES)


def issue(authority="flight-safety", **overrides):
    payload = {"mode": "issue", "hold_id": "hold-1", "authority_id": authority, "scope": "launch", "reason_codes": ["telemetry_anomaly"], "issued_at": 100.0, "expires_at": 200.0, "evidence": [{"sensor": "pressure", "digest": "e1"}]}
    payload.update(overrides)
    return mech().evaluate(LaunchHoldReceiptRequest("mission-a", payload, 1.0))


def test_authorized_hold_is_signed_and_content_bound() -> None:
    receipt = issue()
    assert receipt.decision is Decision.ALLOW
    hold = receipt.metrics["result"]["hold"]
    assert hold["authority_id"] == "flight-safety"
    assert hold["scope"] == "launch"
    assert len(hold["signature"]) == 64
    assert len(hold["evidence_digest"]) == 64


def test_unauthorized_authority_cannot_issue_launch_hold() -> None:
    receipt = issue(authority="observer")
    assert receipt.decision is Decision.REFUSE
    assert "authority_scope_denied:observer:launch" in receipt.reasons


def test_active_valid_hold_blocks_progression() -> None:
    hold = issue().metrics["result"]["hold"]
    checked = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "check", "hold": hold, "now": 150.0}, 1.0))
    assert checked.decision is Decision.REFUSE
    assert "active_hold_blocks_progression" in checked.reasons
    assert checked.metrics["result"]["state"] == "BLOCKED"


def test_expired_hold_no_longer_blocks_progression() -> None:
    hold = issue().metrics["result"]["hold"]
    checked = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "check", "hold": hold, "now": 201.0}, 1.0))
    assert checked.decision is Decision.ALLOW
    assert checked.metrics["result"]["state"] == "EXPIRED"


def test_authorized_clearance_unblocks_exact_hold() -> None:
    hold = issue().metrics["result"]["hold"]
    cleared = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "clear", "hold": hold, "authority_id": "mission-director", "cleared_at": 160.0, "rationale": "telemetry recovered", "evidence": [{"check": "green"}]}, 1.0))
    assert cleared.decision is Decision.ALLOW
    clearance = cleared.metrics["result"]["clearance"]
    checked = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "check", "hold": hold, "clearance": clearance, "now": 170.0}, 1.0))
    assert checked.decision is Decision.ALLOW
    assert checked.metrics["result"]["state"] == "CLEARED"


def test_tampered_hold_signature_fails_closed() -> None:
    hold = issue().metrics["result"]["hold"]
    tampered = dict(hold)
    tampered["reason_codes"] = ["different_reason"]
    checked = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "check", "hold": tampered, "now": 150.0}, 1.0))
    assert checked.decision is Decision.REFUSE
    assert "hold_signature_mismatch" in checked.reasons


def test_clearance_must_be_bound_to_exact_hold() -> None:
    hold = issue().metrics["result"]["hold"]
    other = issue(hold_id="hold-2").metrics["result"]["hold"]
    cleared = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "clear", "hold": other, "authority_id": "mission-director", "cleared_at": 160.0, "rationale": "other cleared", "evidence": [{"check": "green"}]}, 1.0))
    checked = mech().evaluate(LaunchHoldReceiptRequest("mission-a", {"mode": "check", "hold": hold, "clearance": cleared.metrics["result"]["clearance"], "now": 170.0}, 1.0))
    assert checked.decision is Decision.REFUSE
    assert "clearance_not_bound_to_hold" in checked.reasons


def test_expiry_must_follow_issue_time() -> None:
    receipt = issue(expires_at=100.0)
    assert receipt.decision is Decision.REFUSE
    assert "expiry_not_after_issue" in receipt.reasons
