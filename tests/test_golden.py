"""Characterisation tests: seeded simulations must reproduce the pre-refactor outputs.

Hashes were captured from the original code (see golden_values.py).  Exact
float64 bit-identity is asserted on the platform the goldens were captured on
(macOS arm64); elsewhere libm differences may legitimately change low-order
bits, so the scenarios still run (smoke) but the hash comparison is skipped
unless ``BMS_GOLDEN_STRICT=1`` is set.  No network, no Kaggle/NASA data.
"""
from __future__ import annotations

import os
import platform
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from golden_utils import collect  # noqa: E402
from golden_values import GOLDEN  # noqa: E402

_DEFAULT_STRICT = sys.platform == "darwin" and platform.machine() == "arm64"
STRICT = os.environ.get("BMS_GOLDEN_STRICT", "1" if _DEFAULT_STRICT else "0") == "1"


@pytest.fixture(scope="module")
def fingerprints() -> dict:
    return collect()


def test_fingerprint_keys_match(fingerprints):
    assert set(fingerprints) == set(GOLDEN)


@pytest.mark.skipif(not STRICT, reason="bit-identity asserted only on the golden-capture platform")
@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_bit_identical_to_pre_refactor(fingerprints, key):
    assert fingerprints[key] == GOLDEN[key]
