"""Edge agent composition and run loop — TRD 20.2 step 4, dev form.

Wires MOD-1..MOD-4 (frames → detector → evaluator → builder → store), the
publisher, config sync, health reporting and the ADR-009 state machine. All
``*_tick`` methods and ``process_frame`` are pure steps driven by explicit
timestamps — no sleeps, no wall-clock reads — so tests and replays are
deterministic. The only scheduler, and the only ``sleep``, live in ``main``.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import httpx

from guardian_lens_edge.auth import (
    AGENT_CREDENTIAL_ENV,
    AgentAuthenticator,
)
from guardian_lens_edge.config_sync import ConfigSync
from guardian_lens_edge.detector import (
    Detector,
    NullDetector,
    SyntheticDetector,
)
from guardian_lens_edge.events import EventBuilder, iso_utc
from guardian_lens_edge.frames import Frame, FrameSource, SyntheticSource
from guardian_lens_edge.multicamera import (
    DEFAULT_QUEUE_CAPACITY,
    LiveFrameSource,
    MultiCameraSource,
    StreamGapRouter,
)
from guardian_lens_edge.publisher import Publisher, PublishReport
from guardian_lens_edge.rules import RuleEvaluator
from guardian_lens_edge.scenario import Scenario
from guardian_lens_edge.state import AgentStateMachine, GapRecorder
from guardian_lens_edge.store import EdgeStore
from guardian_lens_edge.unsealer import (
    CAMERA_KEY_ENV,
    CAMERA_KEY_ID_ENV,
    CredentialUnsealer,
)
from guardian_lens_edge.uuid7 import generate_uuid7

__all__ = ["EdgeAgent", "main"]

EDGE_VERSION = "0.1.0"

logger = logging.getLogger(__name__)

_SYNTHETIC_REF_PREFIX = "synthetic:"


class EdgeAgent:
    """Composes the edge modules; owns no policy of its own.

    Whether generation may happen is the state machine's decision alone
    (ADR-009); what constitutes a candidate is the evaluator's (D1); what a
    payload contains is the builder's (TRD 10.3). This class only routes
    conditions and data between them.
    """

    def __init__(
        self,
        *,
        store: EdgeStore,
        frame_source: FrameSource,
        detector: Detector,
        evaluator: RuleEvaluator,
        builder: EventBuilder,
        publisher: Publisher,
        config_sync: ConfigSync,
        state: AgentStateMachine,
        agent_id: str,
        site_id: str,
    ) -> None:
        self._store = store
        self._frame_source = frame_source
        self._detector = detector
        self._evaluator = evaluator
        self._builder = builder
        self._publisher = publisher
        self._config_sync = config_sync
        self._state = state
        self._agent_id = agent_id
        self._site_id = site_id

    @property
    def state(self) -> AgentStateMachine:
        return self._state

    @property
    def publisher(self) -> Publisher:
        return self._publisher

    def start(self, now: datetime) -> None:
        """Restore last-known-good configuration and report model readiness.

        The synthetic detector has no artefact to load, so it reports loaded
        immediately; a real MOD-2 would call ``report_model_load_failed``
        here on a missing or hash-mismatched artefact and the agent would
        refuse to start (TRD 5.6).
        """
        config = self._config_sync.load_last_known_good()
        self._evaluator.apply_config(config)
        self._state.set_cameras(config.camera_ids() if config else [])
        self._state.report_model_loaded(now)

    def config_tick(self, now: datetime) -> None:
        before = self._config_sync.applied_version
        config = self._config_sync.tick(now)
        if config is not None and config.config_version != before:
            self._evaluator.apply_config(config)
            self._state.set_cameras(config.camera_ids())

    def process_frame(self, frame: Frame) -> list[str]:
        """One sampled frame through detector → D1 → builder → outbox.

        Returns the event_ids enqueued (empty when nothing was admitted or
        generation is stopped).
        """
        now = frame.captured_at
        self._state.report_outbox_level(self._store.backpressure_level(), now)
        if not self._state.can_generate():
            # Halted (or still starting): emits NO candidate events. The
            # halt itself was loud — gaps open, CRITICAL logged (ADR-009).
            return []
        try:
            detections = self._detector.detect(frame)
        except Exception:  # noqa: BLE001 — MOD-2 failure row: drop frame,
            # count, continue; sustained failure degrades via the machine.
            logger.exception(
                "inference failed on frame: camera=%s seq=%s",
                frame.camera_id,
                frame.sequence,
            )
            self._state.report_inference_failure(now)
            return []
        self._state.report_inference_success(now)
        if not self._state.can_generate():
            return []
        candidates = self._evaluator.evaluate(frame, detections)
        event_ids: list[str] = []
        for candidate in candidates:
            event_ids.append(
                self._builder.build_and_enqueue(
                    candidate,
                    model_version=self._detector.model_version,
                    frame_bytes=self._frame_bytes(frame),
                )
            )
        if event_ids:
            # Re-check immediately so crossing the critical threshold halts
            # before the next frame, not one sample later (RS-2).
            self._state.report_outbox_level(
                self._store.backpressure_level(), now
            )
        return event_ids

    def publisher_tick(self, now: datetime) -> PublishReport:
        report = self._publisher.tick(now)
        # Draining may have brought usage back below the warning level,
        # which closes the outbox_full gap and resumes generation (11.4).
        self._state.report_outbox_level(self._store.backpressure_level(), now)
        return report

    def health_tick(self, now: datetime) -> None:
        """Enqueue a health beat.

        ``sent_at`` is the edge clock at emission: the control plane measures
        skew as ``received_at − sent_at`` (ADR-007). ``applied_config_version``
        is the fact the control plane compares against its intention (RS-4).
        """
        payload = {
            # Exactly the control plane's AgentHealthRequest — it forbids
            # extras, so richer state (halt reason, open gap count, backlog)
            # stays local until TRD 10.3 grows fields for it. sent_at is the
            # ADR-007 skew measurement; applied_config_version is the ADR-008
            # fact that lets BR-001 be observed rather than asserted.
            "sent_at": iso_utc(now),
            "applied_config_version": self._config_sync.applied_version,
            "agent_version": EDGE_VERSION,
        }
        self._store.enqueue_health(
            payload,
            idempotency_key=str(
                generate_uuid7(int(now.timestamp() * 1000))
            ),
            created_at=iso_utc(now),
        )

    def run_scenario(self, *, now: datetime) -> list[str]:
        """Process every frame of the source in order; returns event_ids.

        Steppable equivalent of the live loop for replayed input: ticks are
        interleaved per frame using frame time, so behaviour is identical on
        every run.
        """
        self.start(now)
        self.config_tick(now)
        event_ids: list[str] = []
        last = now
        for frame in self._frame_source.frames():
            event_ids.extend(self.process_frame(frame))
            last = frame.captured_at
        self.publisher_tick(last)
        self.health_tick(last)
        return event_ids

    def run_live(
        self,
        *,
        stop_event: threading.Event,
        publish_interval_seconds: float = 2.0,
        config_interval_seconds: float = 30.0,
        health_interval_seconds: float = 30.0,
        frame_timeout_seconds: float = 0.25,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        """Wall-clock run loop for live (RTSP) input — TRD 20.2 step 5.

        Consumes the frame queue through the existing ``process_frame``
        path and runs ``publisher_tick`` / ``config_tick`` /
        ``health_tick`` on their intervals. The interval defaults are dev
        loop cadences, NOT the `[OPEN]` product thresholds (those remain
        required parameters elsewhere). The loop exits when ``stop_event``
        is set (SIGINT/SIGTERM in ``main``); shutdown closes the sources,
        then makes a final publisher drain attempt — the store is closed
        by the caller that opened it.

        On a configuration change the frame source is rebuilt for added /
        removed / changed cameras via ``apply_config``.
        """
        utc_now = utc_now or _utc_now
        source = self._frame_source
        if not isinstance(source, LiveFrameSource):
            raise TypeError(
                "run_live requires a live frame source with "
                "next_frame/apply_config/close (e.g. MultiCameraSource); "
                f"got {type(source).__name__}"
            )
        now = utc_now()
        self.start(now)
        self.config_tick(now)
        # First composition: cameras from the applied (fetched or
        # last-known-good) configuration; credentials unseal here.
        source.apply_config(self._config_sync.applied, now)
        next_publish_at = now
        next_config_at = now + timedelta(seconds=config_interval_seconds)
        next_health_at = now
        try:
            while not stop_event.is_set():
                frame = source.next_frame(timeout=frame_timeout_seconds)
                if frame is not None:
                    self.process_frame(frame)
                now = utc_now()
                if now >= next_publish_at:
                    self.publisher_tick(now)
                    next_publish_at = now + timedelta(seconds=publish_interval_seconds)
                if now >= next_config_at:
                    version_before = self._config_sync.applied_version
                    self.config_tick(now)
                    if self._config_sync.applied_version != version_before:
                        source.apply_config(self._config_sync.applied, now)
                    next_config_at = now + timedelta(seconds=config_interval_seconds)
                if now >= next_health_at:
                    self.health_tick(now)
                    next_health_at = now + timedelta(seconds=health_interval_seconds)
        finally:
            # Clean shutdown: sources first (stops the camera threads and
            # records any final stream status), then one last drain so a
            # reachable control plane receives everything buffered.
            source.close()
            self.publisher_tick(utc_now())

    def _frame_bytes(self, frame: Frame) -> bytes | None:
        if frame.image_bytes is not None:
            # Live sources carry the sampled JPEG in memory; it reaches
            # disk only here, attached to a candidate (DATABASE.md 11.5).
            return frame.image_bytes
        if frame.image_ref.startswith(_SYNTHETIC_REF_PREFIX):
            return None  # builder writes the placeholder JPEG
        path = Path(frame.image_ref)
        if path.exists():
            return path.read_bytes()
        logger.warning("frame image missing, spooling placeholder: %s",
                       frame.image_ref)
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guardian_lens_edge",
        description=(
            "Guardian Lens edge agent. --source synthetic replays a "
            "scenario file (TRD 13.2 / 20.2 step 4); --source rtsp "
            "ingests the site's configured RTSP cameras (TRD 20.2 step "
            "5). In rtsp mode the detector is a NullDetector — no "
            "detections are produced and no rule can fire; real "
            "detection arrives only through GOVERNANCE.md 9 gate G1 "
            "(model release)."
        ),
    )
    parser.add_argument(
        "--source",
        choices=("synthetic", "rtsp"),
        default=os.environ.get("GL_SOURCE", "synthetic"),
        help="Frame source: 'synthetic' (default) replays --scenario; "
        "'rtsp' ingests the cameras in the agent configuration, with a "
        "NullDetector until gate G1 admits a model (env GL_SOURCE).",
    )
    parser.add_argument(
        "--scenario",
        default=os.environ.get("GL_SCENARIO"),
        help="Path to the scenario JSON; required with --source synthetic "
        "(env GL_SCENARIO).",
    )
    parser.add_argument(
        "--api",
        default=os.environ.get("GL_API_URL"),
        help="Control plane base URL, e.g. http://localhost:8000 "
        "(env GL_API_URL).",
    )
    parser.add_argument(
        "--agent-id",
        default=os.environ.get("GL_AGENT_ID"),
        help="Agent identity registered at the control plane (env GL_AGENT_ID).",
    )
    parser.add_argument(
        "--site",
        default=os.environ.get("GL_SITE_ID"),
        help="Site identity (env GL_SITE_ID).",
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("GL_DATA_DIR", "./edge-data"),
        help="Directory for the SQLite store and evidence spool "
        "(env GL_DATA_DIR).",
    )
    # DATABASE.md 11.4 thresholds are [OPEN — PRD OQ-4]: they must be stated
    # explicitly by the deployment; no default is asserted here.
    parser.add_argument(
        "--outbox-warning-bytes",
        type=int,
        default=_int_env("GL_OUTBOX_WARNING_BYTES"),
        help="Outbox warning threshold in bytes ([OPEN - OQ-4]; required; "
        "env GL_OUTBOX_WARNING_BYTES).",
    )
    parser.add_argument(
        "--outbox-critical-bytes",
        type=int,
        default=_int_env("GL_OUTBOX_CRITICAL_BYTES"),
        help="Outbox critical threshold in bytes ([OPEN - OQ-4]; required; "
        "env GL_OUTBOX_CRITICAL_BYTES).",
    )
    # ADR-009 failure-rate thresholds are [OPEN]: set from pilot data.
    parser.add_argument(
        "--failure-window",
        type=int,
        default=_int_env("GL_FAILURE_WINDOW"),
        help="Inference outcomes per rate window ([OPEN]; required; "
        "env GL_FAILURE_WINDOW).",
    )
    parser.add_argument(
        "--degraded-failure-rate",
        type=float,
        default=_float_env("GL_DEGRADED_FAILURE_RATE"),
        help="Failure rate entering Degraded ([OPEN]; required; "
        "env GL_DEGRADED_FAILURE_RATE).",
    )
    parser.add_argument(
        "--halt-failure-rate",
        type=float,
        default=_float_env("GL_HALT_FAILURE_RATE"),
        help="Failure rate entering Halted ([OPEN]; required; "
        "env GL_HALT_FAILURE_RATE).",
    )
    # rtsp mode. The MOD-1 sustained-decode-failure threshold is [OPEN]
    # like the rates above: required, no default. The tick intervals are
    # loop cadences with dev defaults — not product thresholds.
    parser.add_argument(
        "--decode-failure-threshold",
        type=int,
        default=_int_env("GL_DECODE_FAILURE_THRESHOLD"),
        help="Consecutive frame-decode failures before a camera is "
        "reported degraded ([OPEN] — TRD 4 MOD-1 gives no value; required "
        "with --source rtsp; env GL_DECODE_FAILURE_THRESHOLD).",
    )
    parser.add_argument(
        "--publish-interval",
        type=float,
        default=_float_env("GL_PUBLISH_INTERVAL") or 2.0,
        help="Seconds between publisher ticks in rtsp mode (dev default "
        "2; env GL_PUBLISH_INTERVAL).",
    )
    parser.add_argument(
        "--config-interval",
        type=float,
        default=_float_env("GL_CONFIG_INTERVAL") or 30.0,
        help="Seconds between config sync ticks in rtsp mode (dev "
        "default 30; env GL_CONFIG_INTERVAL).",
    )
    parser.add_argument(
        "--health-interval",
        type=float,
        default=_float_env("GL_HEALTH_INTERVAL") or 30.0,
        help="Seconds between health beats in rtsp mode (dev default 30; "
        "env GL_HEALTH_INTERVAL).",
    )
    parser.add_argument(
        "--queue-capacity",
        type=int,
        default=_int_env("GL_QUEUE_CAPACITY") or DEFAULT_QUEUE_CAPACITY,
        help="Bounded frame-queue capacity across cameras; when full the "
        "newest sample is dropped and counted (default "
        f"{DEFAULT_QUEUE_CAPACITY}; env GL_QUEUE_CAPACITY).",
    )
    return parser


def _int_env(name: str) -> int | None:
    value = os.environ.get(name)
    return int(value) if value else None


def _float_env(name: str) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else None


def _validate_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    required = {
        "--api": args.api,
        "--agent-id": args.agent_id,
        "--site": args.site,
        "--outbox-warning-bytes": args.outbox_warning_bytes,
        "--outbox-critical-bytes": args.outbox_critical_bytes,
        "--failure-window": args.failure_window,
        "--degraded-failure-rate": args.degraded_failure_rate,
        "--halt-failure-rate": args.halt_failure_rate,
    }
    if args.source == "synthetic":
        required["--scenario"] = args.scenario
    else:
        # [OPEN] — required with no default, like the rates above.
        required["--decode-failure-threshold"] = args.decode_failure_threshold
    missing = [flag for flag, value in required.items() if value is None]
    if missing:
        parser.error(f"missing required options: {', '.join(missing)}")


def _build_unsealer(parser: argparse.ArgumentParser) -> CredentialUnsealer:
    """Read camera-key material from the environment, exactly once.

    Key material is never a CLI argument (argv is world-readable). The key
    is injected as bytes; nothing else ever re-reads these variables.
    """
    key_hex = os.environ.get(CAMERA_KEY_ENV)
    key_id = os.environ.get(CAMERA_KEY_ID_ENV)
    if not key_hex or not key_id:
        parser.error(
            f"--source rtsp requires {CAMERA_KEY_ENV} (32-byte hex) and "
            f"{CAMERA_KEY_ID_ENV} in the environment to unseal camera "
            "credentials; they are never CLI arguments."
        )
    try:
        key = bytes.fromhex(key_hex)
    except ValueError:
        parser.error(f"{CAMERA_KEY_ENV} is not valid hex")
    try:
        return CredentialUnsealer(key, key_id)
    except ValueError as exc:
        parser.error(str(exc))
    raise AssertionError("parser.error does not return")  # pragma: no cover


def _run_scenario_mode(
    agent: EdgeAgent, store: EdgeStore, start_at: datetime
) -> int:
    event_ids = agent.run_scenario(now=start_at)
    # Keep draining until the outbox is empty or parked-only; the only
    # sleep in this mode lives in this scheduler.
    while store.pending_count() > 0:
        now = _utc_now()
        next_at = agent.publisher.next_attempt_at
        if next_at is not None and now < next_at:
            time.sleep(min(1.0, (next_at - now).total_seconds()))
            continue
        report = agent.publisher_tick(_utc_now())
        if report.published == 0 and report.retried == 0:
            break
    logger.info(
        "scenario complete: candidates=%d outbox_pending=%d parked=%d",
        len(event_ids),
        store.pending_count(),
        len(store.parked_rows()),
    )
    return 0


def _run_live_mode(agent: EdgeAgent, args: argparse.Namespace) -> int:
    """RTSP mode: run until SIGINT/SIGTERM, then shut down cleanly."""
    stop_event = threading.Event()

    def _request_shutdown(signum: int, _frame: object) -> None:
        logger.info(
            "signal %s received; shutting down",
            signal.Signals(signum).name,
        )
        stop_event.set()

    previous_handlers = {
        handled: signal.signal(handled, _request_shutdown)
        for handled in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        agent.run_live(
            stop_event=stop_event,
            publish_interval_seconds=args.publish_interval,
            config_interval_seconds=args.config_interval,
            health_interval_seconds=args.health_interval,
        )
    finally:
        for handled, handler in previous_handlers.items():
            signal.signal(handled, handler)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = _build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    credential = os.environ.get(AGENT_CREDENTIAL_ENV)
    if not credential:
        parser.error(
            f"{AGENT_CREDENTIAL_ENV} must be set "
            "(format slug:agent_id:secret); it is never a CLI argument."
        )
    unsealer = _build_unsealer(parser) if args.source == "rtsp" else None

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    store = EdgeStore(
        data_dir / "edge.sqlite3",
        warning_bytes=args.outbox_warning_bytes,
        critical_bytes=args.outbox_critical_bytes,
    )
    start_at = _utc_now()
    frame_source: FrameSource
    detector: Detector
    if args.source == "rtsp":
        # Real ingestion, no real detection: the NullDetector counts
        # frames and returns no detections until a model passes gate G1.
        if unsealer is None:  # pragma: no cover - unreachable by parsing
            raise RuntimeError("rtsp mode requires an unsealer")
        frame_source = MultiCameraSource(
            unsealer=unsealer,
            status_listener=StreamGapRouter(GapRecorder(store)),
            decode_failure_threshold=args.decode_failure_threshold,
            queue_capacity=args.queue_capacity,
        )
        detector = NullDetector()
    else:
        scenario = Scenario.load(args.scenario)
        frame_source = SyntheticSource(scenario, start_at=start_at)
        detector = SyntheticDetector(scenario)
    client = httpx.Client(timeout=10.0)
    authenticator = AgentAuthenticator(client, args.api, credential)
    agent = EdgeAgent(
        store=store,
        frame_source=frame_source,
        detector=detector,
        evaluator=RuleEvaluator(store),
        builder=EventBuilder(store, data_dir / "spool", args.agent_id),
        publisher=Publisher(store, client, args.api, authenticator),
        config_sync=ConfigSync(
            store, client, args.api, args.agent_id, authenticator
        ),
        state=AgentStateMachine(
            store,
            failure_window=args.failure_window,
            degraded_failure_rate=args.degraded_failure_rate,
            halt_failure_rate=args.halt_failure_rate,
        ),
        agent_id=args.agent_id,
        site_id=args.site,
    )
    try:
        if args.source == "rtsp":
            return _run_live_mode(agent, args)
        return _run_scenario_mode(agent, store, start_at)
    finally:
        client.close()
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
