# Issue contract — Launch Hold Receipt

## Problem
Maintaining one reliable software lifecycle across vehicles, spacecraft, test, simulation, and operations.

## Desired outcome
A bounded, open, testable implementation of **Launch Hold Receipt** that demonstrates Encode hold reasons, authority, and expiry into a signed hold receipt that blocks progression until cleared.

## Non-goals
- Rocket Lab affiliation or proprietary integration
- Portfolio-wide scale/performance claims
- UI marketing site

## Acceptance
1. Mechanism module implements allow + refuse with structured receipts
2. pytest behavioral suite green
3. operate.py cold-start produces JSON receipt
4. Non-affiliation disclaimer preserved
