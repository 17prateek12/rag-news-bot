import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger("shadow_execution")

T = TypeVar("T")


class ShadowHarness:
    """Shadow-execution harness for comparing new vs baseline implementations.

    Executes the baseline implementation for the caller, and asynchronously runs
    the shadow (candidate) implementation on the same inputs, logging structural diffs
    and timing without risking any failure or regression for the caller.
    """

    @staticmethod
    async def execute_with_shadow(
        *,
        name: str,
        baseline_fn: Callable[[], Coroutine[Any, Any, T]],
        shadow_fn: Callable[[], Coroutine[Any, Any, Any]],
        diff_fn: Callable[[T, Any, float, float], dict[str, Any]] | None = None,
        enabled: bool = True,
    ) -> T:
        # If shadow mode is disabled, simply execute and return baseline
        if not enabled:
            return await baseline_fn()

        t0 = time.perf_counter()
        baseline_result = await baseline_fn()
        baseline_latency = (time.perf_counter() - t0) * 1000

        # Run shadow evaluation in the background so caller is not blocked
        asyncio.create_task(
            ShadowHarness._run_shadow_safe(
                name=name,
                shadow_fn=shadow_fn,
                baseline_result=baseline_result,
                baseline_latency=baseline_latency,
                diff_fn=diff_fn,
            )
        )

        return baseline_result

    @staticmethod
    async def _run_shadow_safe(
        name: str,
        shadow_fn: Callable[[], Coroutine[Any, Any, Any]],
        baseline_result: Any,
        baseline_latency: float,
        diff_fn: Callable[[Any, Any, float, float], dict[str, Any]] | None,
    ) -> None:
        t0 = time.perf_counter()
        try:
            shadow_result = await shadow_fn()
            shadow_latency = (time.perf_counter() - t0) * 1000

            diff_data = (
                diff_fn(baseline_result, shadow_result, baseline_latency, shadow_latency)
                if diff_fn
                else {
                    "baseline_latency_ms": round(baseline_latency, 2),
                    "shadow_latency_ms": round(shadow_latency, 2),
                    "latency_delta_ms": round(shadow_latency - baseline_latency, 2),
                }
            )

            logger.info(
                "SHADOW_DIFF_SUCCESS name=%s diff=%s",
                name,
                diff_data,
            )
        except Exception as exc:
            shadow_latency = (time.perf_counter() - t0) * 1000
            logger.warning(
                "SHADOW_DIFF_FAILURE name=%s shadow_latency_ms=%.2f error=%s",
                name,
                shadow_latency,
                exc,
                exc_info=True,
            )


shadow_harness = ShadowHarness()
