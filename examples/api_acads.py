# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
examples/api_acads.py
---------------------
The operations layer (``ogr_api``) end to end, on a published problem:
ACADS 1(a), Giam & Donald (1989), whose 33 programs average FoS = 0.991.

It is exactly what an AI agent does through the MCP server, minus the
protocol: build the model from a spec, check it, configure the search, run
it as a background job, read the summary and draw it.

Run from the repository root:

    python -m examples.api_acads

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    from ogr_api import Workspace, call

    ws = Workspace(workdir=Path.cwd())
    try:
        pid = call(ws, "project_new", name="ACADS 1(a)")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0, "strength": {
                "model": "mohr_coulomb",
                "params": {"cohesion": 3.0, "friction_angle": 19.6}}}],
        })
        status = call(ws, "project_validate", project_id=pid)
        print("can run:", status["can_run"], status["blockers"])

        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified", "spencer"],
             grid={"x_min": 22.8, "x_max": 43.7, "y_min": 42.3,
                   "y_max": 62.6, "nx": 20, "ny": 20},
             radius_increment=10)

        run = call(ws, "analysis_run", project_id=pid, wait_seconds=300)
        if run["state"] != "done":
            print("still running:", run)
            return
        for m in run["summary"]["methods"]:
            print(f"{m['method_id']:>20s}: {m['caption']} = {m['value']}"
                  f"  ({m['counts']['valid']} valid surfaces)")

        out = call(ws, "model_render", project_id=pid,
                   result_id=run["result_id"], save_path="acads_1a.png",
                   overwrite=True)
        print("picture:", out["saved_to"])
        call(ws, "project_save", project_id=pid, path="acads_1a.ogr",
             overwrite=True)
    finally:
        ws.shutdown()


if __name__ == "__main__":
    main()
