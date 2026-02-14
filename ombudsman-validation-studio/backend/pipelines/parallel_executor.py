"""
Parallel Pipeline Step Executor

Executes pipeline validation steps in parallel when they have no dependencies,
significantly reducing total execution time for large pipelines.

Steps can declare dependencies using the 'depends_on' field in the pipeline YAML:

```yaml
steps:
  - name: schema_validation
    validator: validate_schema_columns

  - name: datatype_validation
    validator: validate_schema_datatypes
    depends_on: [schema_validation]  # Waits for schema_validation

  - name: row_counts
    validator: validate_record_counts
    # No dependencies - runs in parallel with schema_validation
```

Steps without dependencies run in parallel. Steps with dependencies wait
for all their dependencies to complete before starting.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepNode:
    """Represents a step in the execution graph."""
    name: str
    step_config: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ParallelStepExecutor:
    """
    Executes pipeline steps in parallel based on dependency graph.

    Uses ThreadPoolExecutor for CPU-bound validation work and
    respects step dependencies for correct ordering.
    """

    def __init__(
        self,
        step_executor,  # StepExecutor instance
        max_workers: int = 4,
        stop_on_error: bool = False
    ):
        """
        Initialize parallel executor.

        Args:
            step_executor: The StepExecutor instance for running individual steps
            max_workers: Maximum concurrent steps (default 4)
            stop_on_error: Stop all execution if any step fails
        """
        self.step_executor = step_executor
        self.max_workers = max_workers
        self.stop_on_error = stop_on_error
        self._cancelled = False

    def build_dependency_graph(self, steps: List[Dict]) -> Dict[str, StepNode]:
        """
        Build a dependency graph from step configurations.

        Args:
            steps: List of step configurations from pipeline YAML

        Returns:
            Dict mapping step names to StepNode objects
        """
        nodes = {}

        # Create nodes for all steps
        for i, step in enumerate(steps):
            name = step.get("name", f"step_{i}")
            depends_on = step.get("depends_on", [])

            # Convert single dependency to list
            if isinstance(depends_on, str):
                depends_on = [depends_on]

            nodes[name] = StepNode(
                name=name,
                step_config=step,
                dependencies=set(depends_on)
            )

        # Validate dependencies exist
        all_names = set(nodes.keys())
        for name, node in nodes.items():
            missing = node.dependencies - all_names
            if missing:
                logger.warning(f"Step '{name}' has unknown dependencies: {missing}")
                node.dependencies -= missing  # Remove invalid dependencies

        return nodes

    def get_ready_steps(self, nodes: Dict[str, StepNode]) -> List[StepNode]:
        """
        Get steps that are ready to execute (all dependencies completed).

        Args:
            nodes: Dependency graph

        Returns:
            List of steps ready to run
        """
        ready = []

        for node in nodes.values():
            if node.status != StepStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_met = all(
                nodes[dep].status == StepStatus.COMPLETED
                for dep in node.dependencies
                if dep in nodes
            )

            # Check if any dependency failed (skip this step)
            deps_failed = any(
                nodes[dep].status == StepStatus.FAILED
                for dep in node.dependencies
                if dep in nodes
            )

            if deps_failed:
                node.status = StepStatus.SKIPPED
                node.error = "Skipped due to failed dependency"
                logger.warning(f"Skipping step '{node.name}' due to failed dependencies")
                continue

            if deps_met:
                ready.append(node)

        return ready

    def execute_step(self, node: StepNode) -> StepNode:
        """
        Execute a single step synchronously.

        Args:
            node: Step to execute

        Returns:
            Updated StepNode with result
        """
        node.status = StepStatus.RUNNING
        node.start_time = time.time()

        try:
            logger.info(f"[PARALLEL] Starting step: {node.name}")
            result = self.step_executor.run_step(node.step_config)

            node.status = StepStatus.COMPLETED
            node.result = result
            node.end_time = time.time()

            duration = node.end_time - node.start_time
            logger.info(f"[PARALLEL] Completed step: {node.name} in {duration:.2f}s")

        except Exception as e:
            node.status = StepStatus.FAILED
            node.error = str(e)
            node.end_time = time.time()
            logger.error(f"[PARALLEL] Failed step: {node.name} - {e}")

        return node

    def execute_parallel(
        self,
        steps: List[Dict],
        on_step_start: Optional[Callable] = None,
        on_step_complete: Optional[Callable] = None,
        on_step_error: Optional[Callable] = None
    ) -> List[Any]:
        """
        Execute steps in parallel respecting dependencies.

        Args:
            steps: List of step configurations
            on_step_start: Callback when step starts (step_name, step_index)
            on_step_complete: Callback when step completes (step_name, step_index, result)
            on_step_error: Callback when step fails (step_name, step_index, error)

        Returns:
            List of results in original step order
        """
        if not steps:
            return []

        # Build dependency graph
        nodes = self.build_dependency_graph(steps)
        step_order = [s.get("name", f"step_{i}") for i, s in enumerate(steps)]

        logger.info(f"[PARALLEL] Executing {len(steps)} steps with max {self.max_workers} workers")

        # Track completed count for progress
        completed_count = 0
        total_steps = len(steps)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                # Check for cancellation
                if self._cancelled:
                    logger.info("[PARALLEL] Execution cancelled")
                    break

                # Get steps ready to run
                ready_steps = self.get_ready_steps(nodes)

                if not ready_steps:
                    # Check if all done or deadlocked
                    pending = [n for n in nodes.values() if n.status == StepStatus.PENDING]
                    if not pending:
                        break  # All done

                    # Deadlock detection
                    logger.error(f"[PARALLEL] Deadlock detected! Pending steps: {[n.name for n in pending]}")
                    for node in pending:
                        node.status = StepStatus.FAILED
                        node.error = "Circular dependency detected"
                    break

                # Submit ready steps
                futures = {}
                for node in ready_steps:
                    node.status = StepStatus.RUNNING

                    # Call start callback
                    if on_step_start:
                        try:
                            step_index = step_order.index(node.name)
                            on_step_start(node.name, step_index)
                        except:
                            pass

                    future = executor.submit(self.execute_step, node)
                    futures[future] = node

                # Wait for this batch to complete
                for future in as_completed(futures):
                    node = futures[future]

                    try:
                        result_node = future.result()
                        completed_count += 1

                        step_index = step_order.index(node.name)

                        if result_node.status == StepStatus.COMPLETED:
                            if on_step_complete:
                                on_step_complete(node.name, step_index, result_node.result)
                        else:
                            if on_step_error:
                                on_step_error(node.name, step_index, result_node.error)

                            if self.stop_on_error:
                                self._cancelled = True
                                logger.info(f"[PARALLEL] Stopping due to error in {node.name}")

                    except Exception as e:
                        logger.error(f"[PARALLEL] Unexpected error executing {node.name}: {e}")
                        node.status = StepStatus.FAILED
                        node.error = str(e)

                        if on_step_error:
                            step_index = step_order.index(node.name)
                            on_step_error(node.name, step_index, str(e))

                logger.debug(f"[PARALLEL] Progress: {completed_count}/{total_steps} steps completed")

        # Collect results in original order
        results = []
        for name in step_order:
            node = nodes.get(name)
            if node and node.result is not None:
                results.append(node.result)
            elif node and node.status == StepStatus.SKIPPED:
                # Create a skipped result
                from ombudsman.core.result import ValidationResult
                results.append(ValidationResult(
                    name=name,
                    status="SKIPPED",
                    severity="NONE",
                    details={"reason": node.error or "Skipped due to dependency failure"}
                ))
            elif node and node.status == StepStatus.FAILED:
                from ombudsman.core.result import ValidationResult
                results.append(ValidationResult(
                    name=name,
                    status="ERROR",
                    severity="HIGH",
                    details={"error": node.error or "Step execution failed"}
                ))

        # Log summary
        completed = sum(1 for n in nodes.values() if n.status == StepStatus.COMPLETED)
        failed = sum(1 for n in nodes.values() if n.status == StepStatus.FAILED)
        skipped = sum(1 for n in nodes.values() if n.status == StepStatus.SKIPPED)

        logger.info(f"[PARALLEL] Execution complete: {completed} passed, {failed} failed, {skipped} skipped")

        return results

    def cancel(self):
        """Cancel ongoing execution."""
        self._cancelled = True


async def execute_steps_parallel_async(
    steps: List[Dict],
    step_executor,
    max_workers: int = 4,
    on_step_start: Optional[Callable] = None,
    on_step_complete: Optional[Callable] = None,
    on_step_error: Optional[Callable] = None
) -> List[Any]:
    """
    Async wrapper for parallel step execution.

    Runs the parallel executor in a thread pool to avoid blocking the event loop.
    """
    parallel_exec = ParallelStepExecutor(
        step_executor=step_executor,
        max_workers=max_workers
    )

    # Run in thread pool
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: parallel_exec.execute_parallel(
            steps,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
            on_step_error=on_step_error
        )
    )

    return results
