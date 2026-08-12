"""Launch Hold Receipt.

A vendor-neutral, deterministic safety hold protocol for mission/vehicle/software
progression. Holds are HMAC-bound to authority, scope, reason, evidence, issue
and expiry times. A progression check remains blocked until the exact hold is
expired or cleared by an independently authorized clearance receipt.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class LaunchHoldReceiptRequest:
    subject_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    budget: float = 1.0
    grant_id: str | None = None
    not_after: float | None = None


@dataclass(frozen=True)
class LaunchHoldReceiptReceipt:
    decision: Decision
    reasons: tuple[str, ...]
    digest: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"decision": self.decision.value, "reasons": list(self.reasons), "digest": self.digest, "metrics": self.metrics}


class HoldError(ValueError):
    pass


class LaunchHoldReceipt:
    MIN_BUDGET = 0.0

    def __init__(self, *, authority_secrets: Mapping[str, bytes] | None = None, authority_scopes: Mapping[str, set[str] | frozenset[str]] | None = None) -> None:
        self._secrets = {str(k): bytes(v) for k, v in (authority_secrets or {}).items()}
        self._scopes = {str(k): frozenset(str(x) for x in v) for k, v in (authority_scopes or {}).items()}

    @staticmethod
    def _num(value: Any, label: str, *, minimum: float | None = None) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HoldError(f"{label}_invalid")
        value = float(value)
        if not math.isfinite(value):
            raise HoldError(f"{label}_not_finite")
        if minimum is not None and value < minimum:
            raise HoldError(f"{label}_below_minimum")
        return value

    @staticmethod
    def _id(value: Any, label: str) -> str:
        value = str(value or "").strip()
        if not value:
            raise HoldError(f"{label}_missing")
        return value

    def _secret(self, authority_id: str) -> bytes:
        secret = self._secrets.get(authority_id)
        if not secret:
            raise HoldError(f"authority_secret_missing:{authority_id}")
        return secret

    def _authorize_scope(self, authority_id: str, scope: str) -> None:
        allowed = self._scopes.get(authority_id, frozenset())
        if scope not in allowed and "*" not in allowed:
            raise HoldError(f"authority_scope_denied:{authority_id}:{scope}")

    def _sign(self, authority_id: str, body: Mapping[str, Any]) -> str:
        return hmac.new(self._secret(authority_id), _canonical(dict(body)), hashlib.sha256).hexdigest()

    def _verify_signed(self, raw: Any, *, kind: str) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise HoldError(f"{kind}_missing")
        signature = str(raw.get("signature", "")).strip()
        if len(signature) != 64:
            raise HoldError(f"{kind}_signature_invalid")
        body = {k: v for k, v in raw.items() if k != "signature"}
        authority_id = self._id(body.get("authority_id"), f"{kind}_authority_id")
        expected = self._sign(authority_id, body)
        if not hmac.compare_digest(signature, expected):
            raise HoldError(f"{kind}_signature_mismatch")
        return dict(raw)

    def _issue(self, payload: dict[str, Any]) -> dict[str, Any]:
        authority_id = self._id(payload.get("authority_id"), "authority_id")
        scope = self._id(payload.get("scope"), "scope")
        self._authorize_scope(authority_id, scope)
        issued_at = self._num(payload.get("issued_at"), "issued_at", minimum=0)
        expires_at = self._num(payload.get("expires_at"), "expires_at", minimum=0)
        if expires_at <= issued_at:
            raise HoldError("expiry_not_after_issue")
        reason_codes = payload.get("reason_codes")
        if not isinstance(reason_codes, list) or not reason_codes or any(not str(v).strip() for v in reason_codes):
            raise HoldError("reason_codes_invalid")
        evidence = payload.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise HoldError("evidence_missing")
        evidence_digest = _digest(evidence)
        body = {
            "schema": "glaciereq.launch-hold.v1",
            "hold_id": self._id(payload.get("hold_id"), "hold_id"),
            "authority_id": authority_id,
            "scope": scope,
            "reason_codes": sorted(set(str(v).strip() for v in reason_codes)),
            "issued_at": issued_at,
            "expires_at": expires_at,
            "evidence_digest": evidence_digest,
        }
        return {**body, "signature": self._sign(authority_id, body)}

    def _clear(self, payload: dict[str, Any]) -> dict[str, Any]:
        hold = self._verify_signed(payload.get("hold"), kind="hold")
        authority_id = self._id(payload.get("authority_id"), "clearance_authority_id")
        scope = str(hold["scope"])
        self._authorize_scope(authority_id, scope)
        cleared_at = self._num(payload.get("cleared_at"), "cleared_at", minimum=0)
        if cleared_at < float(hold["issued_at"]):
            raise HoldError("clearance_before_hold_issue")
        rationale = self._id(payload.get("rationale"), "clearance_rationale")
        evidence = payload.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise HoldError("clearance_evidence_missing")
        body = {
            "schema": "glaciereq.launch-hold-clearance.v1",
            "hold_id": hold["hold_id"],
            "hold_signature": hold["signature"],
            "authority_id": authority_id,
            "scope": scope,
            "cleared_at": cleared_at,
            "rationale": rationale,
            "evidence_digest": _digest(evidence),
        }
        return {**body, "signature": self._sign(authority_id, body)}

    def _check(self, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        hold = self._verify_signed(payload.get("hold"), kind="hold")
        now = self._num(payload.get("now"), "now", minimum=0)
        clearance_raw = payload.get("clearance")
        clearance = None
        reasons: list[str] = []
        state = "BLOCKED"
        if now > float(hold["expires_at"]):
            state = "EXPIRED"
        elif clearance_raw is not None:
            clearance = self._verify_signed(clearance_raw, kind="clearance")
            if clearance.get("hold_id") != hold["hold_id"] or clearance.get("hold_signature") != hold["signature"]:
                reasons.append("clearance_not_bound_to_hold")
            elif clearance.get("scope") != hold["scope"]:
                reasons.append("clearance_scope_mismatch")
            elif float(clearance.get("cleared_at", -1)) > now:
                reasons.append("clearance_from_future")
            else:
                state = "CLEARED"
        if state == "BLOCKED" and not reasons:
            reasons.append("active_hold_blocks_progression")
        result = {
            "state": state,
            "hold_id": hold["hold_id"],
            "scope": hold["scope"],
            "hold_authority": hold["authority_id"],
            "expires_at": hold["expires_at"],
            "clearance_authority": clearance.get("authority_id") if clearance else None,
        }
        return result, reasons

    def evaluate(self, req: LaunchHoldReceiptRequest) -> LaunchHoldReceiptReceipt:
        reasons: list[str] = []
        if not str(req.subject_id or "").strip():
            reasons.append("subject_id_missing")
        if isinstance(req.budget, bool) or not isinstance(req.budget, (int, float)) or not math.isfinite(float(req.budget)) or float(req.budget) <= self.MIN_BUDGET:
            reasons.append("budget_non_positive_or_invalid")
        payload = req.payload if isinstance(req.payload, dict) else {}
        if not isinstance(req.payload, dict):
            reasons.append("payload_not_object")
        result: dict[str, Any] | None = None
        try:
            mode = str(payload.get("mode", "issue")).lower()
            if mode == "issue":
                result = {"hold": self._issue(payload)}
            elif mode == "clear":
                result = {"clearance": self._clear(payload)}
            elif mode == "check":
                result, mode_reasons = self._check(payload)
                reasons.extend(mode_reasons)
            else:
                raise HoldError("mode_invalid")
        except (HoldError, TypeError, ValueError) as exc:
            reasons.append(str(exc))
        decision = Decision.REFUSE if reasons else Decision.ALLOW
        metrics = {"result": result}
        body = {"subject_id": req.subject_id, "decision": decision.value, "reasons": reasons, "metrics": metrics}
        return LaunchHoldReceiptReceipt(decision, tuple(reasons or ["launch_hold_transition_verified"]), _digest(body), metrics)


Mechanism = LaunchHoldReceipt
