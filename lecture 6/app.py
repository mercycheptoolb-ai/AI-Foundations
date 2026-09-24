"""Dash desk for dunk / foul video judging.

Run:  python app.py
Open: http://127.0.0.1:8050
"""

from __future__ import annotations

import threading
import traceback
import uuid
from pathlib import Path
from typing import Any

from dash import Dash, Input, Output, State, dcc, html, no_update
from flask import send_from_directory

from agent import run_agent
from models import DunkVerdict, FoulVerdict

HERE = Path(__file__).resolve().parent
VIDEOS = HERE / "videos"
DUNKS = VIDEOS / "dunks"
FOULS = VIDEOS / "fouls"
FRAMES = HERE / "frames"

# Live job state (agent runs in a background thread; Dash Interval polls this).
_JOB_LOCK = threading.Lock()
_JOB: dict[str, Any] | None = None

app = Dash(__name__)
server = app.server

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            @keyframes desk-spin {
                to { transform: rotate(360deg); }
            }
            .desk-spinner {
                width: 36px;
                height: 36px;
                border: 3px solid #ddd;
                border-top-color: #ff2d95;
                border-radius: 50%;
                animation: desk-spin 0.75s linear infinite;
                flex-shrink: 0;
            }
            .desk-thinking {
                display: flex;
                align-items: flex-start;
                gap: 14px;
                padding: 16px;
                border: 1px solid #ccc;
                border-radius: 12px;
                background: #fafafa;
            }
            .desk-tool-steps {
                color: #555;
                font-size: 0.9rem;
                margin: 8px 0 0 0;
                padding-left: 1.1rem;
            }
            .desk-tool-steps li { margin: 4px 0; }
            .desk-tool-steps li.live { color: #e01870; font-weight: 600; }
            .desk-call-badge {
                display: inline-block;
                font-weight: 700;
                font-size: 1.1rem;
                padding: 6px 12px;
                border-radius: 8px;
                background: #1a1a2e;
                color: #fff;
            }
            .judge-btn {
                appearance: none;
                border: none;
                cursor: pointer;
                font-family: inherit;
                font-size: 0.95rem;
                font-weight: 650;
                letter-spacing: 0.02em;
                color: #fff;
                background: linear-gradient(135deg, #ff2d95 0%, #e01870 100%);
                padding: 12px 28px;
                border-radius: 999px;
                box-shadow: 0 8px 20px rgba(255, 45, 149, 0.28);
                transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
            }
            .judge-btn:hover {
                filter: brightness(1.06);
                transform: translateY(-1px);
                box-shadow: 0 10px 24px rgba(255, 45, 149, 0.36);
            }
            .judge-btn:active {
                transform: translateY(1px);
                box-shadow: 0 4px 12px rgba(255, 45, 149, 0.22);
            }
            .judge-btn:focus-visible {
                outline: 2px solid #ff2d95;
                outline-offset: 3px;
            }
            .judge-row {
                display: flex;
                align-items: center;
                gap: 14px;
                margin-top: 14px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""


@server.route("/media/<path:filename>")
def serve_media(filename: str):
    return send_from_directory(HERE, filename)


def list_clips(tab: str) -> list[dict]:
    """Return dropdown options. value is path relative to videos/ (e.g. dunks/howard_1.mp4)."""
    folder = DUNKS if tab == "dunk" else FOULS
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.mp4"), key=lambda p: p.name)
    opts = []
    for p in files:
        rel = p.relative_to(VIDEOS).as_posix()  # dunks/howard_1.mp4
        opts.append({"label": p.name, "value": rel})
    return opts


def foul_call_label(raw: str) -> str:
    key = (raw or "").strip().lower()
    return {
        "foul": "Foul",
        "flop": "Flop",
        "no_call": "No Foul",
    }.get(key, "No Foul")


def _tool_steps_list(
    tool_events: list[dict[str, Any]] | list[str] | None,
    *,
    live: bool = False,
) -> html.Ul | None:
    if not tool_events:
        return None
    items = []
    for i, t in enumerate(tool_events):
        name = t.get("name", "?") if isinstance(t, dict) else str(t)
        is_latest = live and i == len(tool_events) - 1
        label = f"Using: {name}…" if is_latest else f"Used: {name}"
        items.append(html.Li(label, className="live" if is_latest else None))
    return html.Ul(items, className="desk-tool-steps")


def _thumb_row(frame_paths: list[str], n: int = 4) -> html.Div | None:
    if not frame_paths:
        return None
    imgs = []
    for fp in frame_paths[:n]:
        rel = str(fp).replace("\\", "/")
        if not rel.startswith("frames/"):
            p = Path(fp)
            try:
                rel = str(p.relative_to(HERE)).replace("\\", "/")
            except ValueError:
                rel = p.name
        imgs.append(
            html.Img(
                src=f"/media/{rel}",
                style={"width": "22%", "margin": "1%", "borderRadius": "6px"},
            )
        )
    return html.Div(imgs, style={"marginTop": "12px"})


def render_thinking(tools: list[str] | None = None) -> html.Div:
    tools = tools or []
    steps = _tool_steps_list(tools, live=True)
    body: list[Any] = [
        html.P("Judging…", style={"margin": "0 0 4px 0", "fontWeight": "600"}),
        html.P(
            "Tool calls show up here as the agent runs."
            if not tools
            else "Still working…",
            style={"margin": 0, "color": "#666", "fontSize": "0.9rem"},
        ),
    ]
    if steps:
        body.append(steps)
    return html.Div(
        [
            html.Div(className="desk-spinner", role="status", **{"aria-label": "Judging"}),
            html.Div(body),
        ],
        className="desk-thinking",
    )


def render_verdict(payload: dict[str, Any] | None) -> html.Div | html.P:
    if not payload:
        return html.P("No verdict yet.")
    if payload.get("error"):
        return html.P(payload["error"])

    tool_block = _tool_steps_list(payload.get("tool_events"))
    verdict_raw = payload.get("verdict")
    if verdict_raw is None:
        return html.P("No verdict yet.")

    if isinstance(verdict_raw, dict):
        data = verdict_raw
    elif hasattr(verdict_raw, "model_dump"):
        data = verdict_raw.model_dump()
    else:
        data = dict(verdict_raw)

    card_style = {
        "border": "1px solid #ccc",
        "borderRadius": "12px",
        "padding": "16px",
        "background": "#fafafa",
    }
    kind = data.get("kind")
    thumbs = _thumb_row(list(data.get("frame_paths") or []))

    if kind == "dunk":
        scores = data.get("scores") or {}
        children: list[Any] = [html.H3("Dunk verdict")]
        if tool_block:
            children.append(tool_block)
        children.extend(
            [
                html.P(data.get("play_by_play", "")),
                html.Ul([html.Li(f"{k}: {v}") for k, v in scores.items()]),
                html.P([html.Strong("Total: "), str(data.get("total"))]),
                html.P(data.get("rationale", "")),
            ]
        )
        if thumbs:
            children.append(thumbs)
        return html.Div(children, style=card_style)

    call_label = foul_call_label(str(data.get("call", "")))
    conf = data.get("confidence")
    children = [html.H3("Foul / flop verdict")]
    if tool_block:
        children.append(tool_block)
    children.extend(
        [
            html.P(
                [
                    html.Strong("Call: "),
                    html.Span(call_label, className="desk-call-badge"),
                    html.Span(f"  (confidence {conf})" if conf is not None else ""),
                ]
            ),
            html.P(data.get("play_by_play", "")),
            html.P(data.get("rationale", "")),
        ]
    )
    if thumbs:
        children.append(thumbs)
    return html.Div(children, style=card_style)


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    verdict = result.get("verdict")
    if isinstance(verdict, (DunkVerdict, FoulVerdict)):
        verdict = verdict.model_dump()
    elif hasattr(verdict, "model_dump"):
        verdict = verdict.model_dump()
    return {
        "verdict": verdict,
        "tool_events": result.get("tool_events") or [],
        "error": result.get("error"),
    }


def _snapshot_job() -> dict[str, Any] | None:
    with _JOB_LOCK:
        if _JOB is None:
            return None
        return {
            "id": _JOB["id"],
            "status": _JOB["status"],
            "tools": list(_JOB["tools"]),
            "result": _JOB.get("result"),
            "error": _JOB.get("error"),
        }


def _start_job(clip_rel: str) -> str:
    global _JOB
    job_id = uuid.uuid4().hex[:8]
    # clip_rel is like dunks/howard_1.mp4 or fouls/ronaldo-1.mp4
    path = VIDEOS / clip_rel

    with _JOB_LOCK:
        _JOB = {
            "id": job_id,
            "status": "running",
            "tools": [],
            "result": None,
            "error": None,
        }

    def on_tool(name: str) -> None:
        with _JOB_LOCK:
            if _JOB is not None and _JOB["id"] == job_id:
                _JOB["tools"].append(name)

    def worker() -> None:
        global _JOB
        try:
            if not path.is_file():
                raise FileNotFoundError(f"Missing clip file: {clip_rel}")
            result = run_agent(str(path), on_tool=on_tool)
            payload = _serialize_result(result)
            with _JOB_LOCK:
                if _JOB is not None and _JOB["id"] == job_id:
                    _JOB["result"] = payload
                    _JOB["status"] = "done"
        except Exception as exc:
            traceback.print_exc()
            with _JOB_LOCK:
                if _JOB is not None and _JOB["id"] == job_id:
                    _JOB["error"] = str(exc) or "Something went wrong — check .env / Portkey."
                    _JOB["status"] = "error"

    threading.Thread(target=worker, daemon=True).start()
    return job_id


app.layout = html.Div(
    [
        html.H2("Sports video desk"),
        dcc.Store(id="judge-job-id", data=None),
        dcc.Store(id="judge-result", data=None),
        dcc.Interval(id="judge-poll", interval=400, n_intervals=0, disabled=True),
        dcc.Tabs(
            id="sport-tabs",
            value="dunk",
            children=[
                dcc.Tab(label="Dunks", value="dunk"),
                dcc.Tab(label="Fouls / Flops", value="foul"),
            ],
        ),
        html.Label("Clip"),
        dcc.Dropdown(id="clip-dropdown", clearable=False),
        html.Video(
            id="clip-player",
            controls=True,
            style={"width": "100%", "maxWidth": "720px", "marginTop": "12px"},
        ),
        html.Div(
            [
                html.Button("Judge", id="judge-btn", n_clicks=0, className="judge-btn"),
                html.Span(id="judge-status", style={"color": "#666", "fontSize": "0.95rem"}),
            ],
            className="judge-row",
        ),
        html.Div(id="verdict-card", style={"marginTop": "20px"}),
    ],
    style={
        "maxWidth": "800px",
        "margin": "24px auto",
        "fontFamily": "sans-serif",
        "padding": "0 16px",
    },
)


@app.callback(
    Output("clip-dropdown", "options"),
    Output("clip-dropdown", "value"),
    Input("sport-tabs", "value"),
)
def fill_dropdown(tab):
    opts = list_clips(tab)
    value = opts[0]["value"] if opts else None
    return opts, value


@app.callback(
    Output("judge-result", "data", allow_duplicate=True),
    Output("judge-job-id", "data", allow_duplicate=True),
    Output("judge-poll", "disabled", allow_duplicate=True),
    Output("verdict-card", "children", allow_duplicate=True),
    Output("judge-status", "children", allow_duplicate=True),
    Input("sport-tabs", "value"),
    prevent_initial_call=True,
)
def clear_card_on_tab(_tab):
    return None, None, True, [], ""


@app.callback(Output("clip-player", "src"), Input("clip-dropdown", "value"))
def set_video(rel):
    if not rel:
        return None
    # rel is dunks/howard_1.mp4 → /media/videos/dunks/howard_1.mp4
    return f"/media/videos/{rel}"


@app.callback(
    Output("judge-job-id", "data"),
    Output("judge-result", "data"),
    Output("judge-poll", "disabled"),
    Output("judge-poll", "n_intervals"),
    Input("judge-btn", "n_clicks"),
    State("clip-dropdown", "value"),
    State("judge-job-id", "data"),
    prevent_initial_call=True,
)
def start_judge(_, name, job_id):
    snap = _snapshot_job()
    if job_id and snap and snap["id"] == job_id and snap["status"] == "running":
        return no_update, no_update, no_update, no_update
    if not name:
        return None, {"error": "Pick a clip first."}, True, 0
    new_id = _start_job(name)
    return new_id, None, False, 0


@app.callback(
    Output("verdict-card", "children"),
    Output("judge-status", "children"),
    Output("judge-result", "data", allow_duplicate=True),
    Output("judge-job-id", "data", allow_duplicate=True),
    Output("judge-poll", "disabled", allow_duplicate=True),
    Input("judge-poll", "n_intervals"),
    Input("judge-job-id", "data"),
    Input("judge-result", "data"),
    prevent_initial_call=True,
)
def poll_and_render(_, job_id, stored_result):
    if job_id:
        snap = _snapshot_job()
        if snap and snap["id"] == job_id:
            if snap["status"] == "running":
                return render_thinking(snap["tools"]), "Judging…", no_update, no_update, False
            if snap["status"] == "done":
                payload = snap["result"] or {"error": "Empty result."}
                return render_verdict(payload), "Done", payload, None, True
            if snap["status"] == "error":
                payload = {"error": snap.get("error") or "Something went wrong."}
                return render_verdict(payload), "Error", payload, None, True
        # job id set but not found yet — show empty spinner
        return render_thinking([]), "Judging…", no_update, no_update, False

    if stored_result:
        return render_verdict(stored_result), "Done", no_update, no_update, True
    return [], "", no_update, no_update, True


if __name__ == "__main__":
    FRAMES.mkdir(exist_ok=True)
    app.run(host="127.0.0.1", port=8050, debug=False, use_reloader=False)
