"""Export capital flow data to JSON for the frontend."""

from __future__ import annotations

import json
import os
from typing import Any, List

import numpy as np

from engine.config import OUTPUT_DIR
from engine.exporters.json_exporter import NumpyEncoder
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _write_json(data: Any, filename: str) -> str:
    """Write data to a JSON file under OUTPUT_DIR."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False,
                  indent=None, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path


def _safe_float(val: Any) -> Any:
    """Convert to float, replacing NaN/Inf with None."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return val


def _clean_phases(phases: List[dict]) -> List[dict]:
    """Clean up floats in phase nodes/flows for JSON export."""
    cleaned = []
    for phase in phases:
        cleaned_nodes = {}
        for node_id, node in phase["nodes"].items():
            cleaned_node = {
                "label_zh": node["label_zh"],
                "label_en": node["label_en"],
                "value": node["value"],
                "net": _safe_float(node["net"]),
                "type": node["type"],
            }
            if "confidence" in node:
                cleaned_node["confidence"] = _safe_float(node["confidence"])
            cleaned_nodes[node_id] = cleaned_node

        cleaned_flows = []
        for flow in phase["flows"]:
            cleaned_flows.append({
                "from": flow["from"],
                "to": flow["to"],
                "amount": _safe_float(flow["amount"]),
                "label": flow["label"],
            })

        entry = {
            "id": phase["id"],
            "date": phase["date"],
            "phase": phase["phase"],
            "label_zh": phase["label_zh"],
            "label_en": phase["label_en"],
            "description_zh": phase["description_zh"],
            "description_en": phase["description_en"],
            "nodes": cleaned_nodes,
            "flows": cleaned_flows,
            "risk_net": _safe_float(phase["risk_net"]),
            "safe_net": _safe_float(phase["safe_net"]),
        }
        if "rfi" in phase:
            rfi_val = phase["rfi"]
            try:
                rfi_f = float(rfi_val)
                entry["rfi"] = None if (np.isnan(rfi_f) or np.isinf(rfi_f)) else round(rfi_f, 4)
            except (TypeError, ValueError):
                entry["rfi"] = _safe_float(rfi_val)
        if "untracked" in phase:
            entry["untracked"] = _safe_float(phase["untracked"])
        cleaned.append(entry)
    return cleaned


def export_capital_flows(
    window_results: dict[str, List[dict]],
    run_date: str,
) -> None:
    """Export capital_flows.json with multi-window data.

    Args:
        window_results: Dict of window_label -> phases list.
            e.g. {"1W": [...], "2W": [...], "1M": [...]}
        run_date: Date string (YYYY-MM-DD).
    """
    if not window_results:
        log.warning("No capital flow data to export")
        return

    windows: dict[str, Any] = {}
    for label, phases in window_results.items():
        cleaned = _clean_phases(phases)
        current_idx = len(cleaned) - 1 if cleaned else 0
        windows[label] = {
            "current_phase_idx": current_idx,
            "phases": cleaned,
        }

    # Default window = first key (typically "1W")
    default_window = next(iter(windows))

    data = {
        "date": run_date,
        "default_window": default_window,
        "signal_method": "Hybrid: ETF shares outstanding (6 ETFs) + volume-price proxy (3 ETFs)",
        "windows": windows,
    }

    _write_json(data, "capital_flows.json")
    total = sum(len(w["phases"]) for w in windows.values())
    log.info(f"Exported {total} phases across {len(windows)} windows")
