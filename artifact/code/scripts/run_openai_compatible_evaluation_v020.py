#!/usr/bin/env python3
"""Run compiled SecRegBench requests against an OpenAI-compatible endpoint.

No endpoint or credential is embedded in this file. The API key is read from
an environment variable and is never written. Use ``--mode dry-run`` first.
Raw response text is written only to the user-selected output directory.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ACTIONS = ("ANSWER", "CLARIFY", "REFUSE", "ESCALATE")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_jsonl(path: Path, row: dict[str, Any], lock: threading.Lock) -> None:
    line = canonical_json(row) + "\n"
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def parse_action(content: str) -> tuple[str | None, list[str]]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, [f"json_decode:{exc.msg}"]
    if not isinstance(value, dict):
        return None, ["not_object"]
    errors = [] if set(value) == {"action"} else ["keys_must_equal_action"]
    action = value.get("action")
    if action not in ACTIONS:
        errors.append("invalid_action")
        return None, errors
    return str(action), errors


def response_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message")
    return str(message.get("content") or "") if isinstance(message, dict) else ""


def prepare_payload(
    request_row: dict[str, Any], model: str, profile: str
) -> dict[str, Any]:
    payload = json.loads(json.dumps(request_row["request_payload"]))
    payload["model"] = model
    if profile in {"generic-json", "deepseek-json"}:
        payload.pop("chat_template_kwargs", None)
    if profile == "deepseek-json":
        payload["thinking"] = {"type": "disabled"}
    payload["temperature"] = 0.0
    payload["max_tokens"] = 64
    payload["stream"] = False
    payload["response_format"] = {"type": "json_object"}
    return payload


def post_json(
    endpoint: str, payload: dict[str, Any], api_key: str, timeout: int
) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=canonical_json(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("response_not_object")
    return value


def run_one(
    job: dict[str, Any],
    request_row: dict[str, Any],
    endpoint: str,
    model: str,
    api_key: str,
    profile: str,
    timeout: int,
    max_attempts: int,
    seed: int,
) -> dict[str, Any]:
    payload = prepare_payload(request_row, model, profile)
    response: dict[str, Any] | None = None
    final_error: str | None = None
    attempts = 0
    started = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            response = post_json(endpoint, payload, api_key, timeout)
            final_error = None
            break
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            final_error = f"{type(exc).__name__}:{exc}"
            if attempt < max_attempts:
                jitter = random.Random(f"{seed}|{job['job_id']}|{attempt}").random()
                time.sleep(min(2 ** (attempt - 1), 8) + 0.25 * jitter)

    content = response_content(response or {})
    action, parse_errors = (
        parse_action(content) if response is not None else (None, ["missing_response"])
    )
    return {
        "schema_version": "0.20.0",
        "job_id": job["job_id"],
        "scenario_id": job["scenario_id"],
        "method": job["method"],
        "run_generation": 1,
        "status": (
            "PASS_VALID_ACTION"
            if response is not None and not parse_errors
            else ("COMPLETE_INVALID_ACTION" if response is not None else "FAIL_TRANSPORT")
        ),
        "result": {
            "parsed_action": action,
            "parse_errors": parse_errors,
            "response_content": content,
        },
        "api_error": final_error,
        "attempts": attempts,
        "latency_seconds": time.perf_counter() - started,
        "request_sha256": digest(payload),
        "response_sha256": digest(response) if response is not None else None,
        "response_model_id": (response or {}).get("model"),
        "usage": (response or {}).get("usage"),
        "credential_persisted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", type=Path)
    parser.add_argument("requests", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--mode", choices=("dry-run", "canary", "batch"), required=True)
    parser.add_argument("--endpoint")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env", default="SECREGBENCH_API_KEY")
    parser.add_argument(
        "--profile",
        choices=("as-compiled", "generic-json", "deepseek-json"),
        default="generic-json",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--seed", type=int, default=24072027)
    args = parser.parse_args()

    jobs = {row["job_id"]: row for row in read_jsonl(args.jobs)}
    requests = {row["job_id"]: row for row in read_jsonl(args.requests)}
    if not jobs or set(jobs) != set(requests):
        raise ValueError("job/request identifiers do not match")
    if args.concurrency < 1 or args.max_attempts < 1:
        raise ValueError("concurrency and max-attempts must be positive")

    summary = {
        "schema_version": "0.20.0",
        "status": "PASS_DRY_RUN" if args.mode == "dry-run" else "RUN_PENDING",
        "mode": args.mode,
        "jobs_available": len(jobs),
        "model": args.model,
        "profile": args.profile,
        "endpoint_supplied": bool(args.endpoint),
        "credential_available": bool(os.environ.get(args.api_key_env)),
        "credential_persisted": False,
    }
    if args.mode == "dry-run":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if not args.endpoint:
        raise ValueError("--endpoint is required outside dry-run mode")
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise ValueError(f"missing API key environment variable: {args.api_key_env}")

    selected = sorted(jobs)
    if args.mode == "canary":
        selected = selected[: min(4, len(selected))]
    output_path = args.output_dir / "events_private.jsonl"
    completed = {
        row["job_id"]
        for row in read_jsonl(output_path)
        if row.get("run_generation") == 1
    } if output_path.is_file() else set()
    selected = [job_id for job_id in selected if job_id not in completed]
    lock = threading.Lock()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        future_map = {
            executor.submit(
                run_one,
                jobs[job_id],
                requests[job_id],
                args.endpoint,
                args.model,
                api_key,
                args.profile,
                args.timeout,
                args.max_attempts,
                args.seed,
            ): job_id
            for job_id in selected
        }
        for future in concurrent.futures.as_completed(future_map):
            append_jsonl(output_path, future.result(), lock)

    events = read_jsonl(output_path)
    report = {
        **summary,
        "status": "COMPLETE",
        "events": len(events),
        "valid_actions": sum(
            row.get("status") == "PASS_VALID_ACTION" for row in events
        ),
        "transport_failures": sum(row.get("status") == "FAIL_TRANSPORT" for row in events),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "raw_response_text_is_local_output": True,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
