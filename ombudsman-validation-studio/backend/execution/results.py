from fastapi import APIRouter, HTTPException
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

router = APIRouter()

RESULTS_DIR = "results"

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

@router.get("")
def fetch_results():
    """Fetch all validation results from the results directory."""
    entries = []
    if os.path.exists(RESULTS_DIR):
        for file in os.listdir(RESULTS_DIR):
            if file.endswith(".json"):
                try:
                    with open(os.path.join(RESULTS_DIR, file)) as f:
                        entries.append(json.load(f))
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    return {"results": entries}


@router.get("/{run_id}/step/{step_name}/comparison")
def get_comparison_details(run_id: str, step_name: str):
    """
    Get detailed comparison data for a specific validation step.

    This endpoint returns the full side-by-side comparison data that can be
    used to render a detailed comparison view in the UI.

    Args:
        run_id: The pipeline run ID
        step_name: The validation step name

    Returns:
        Comparison details including:
        - columns: List of column names
        - rows: Array of row comparisons with sql_values, snowflake_values, and differing_columns
        - summary: High-level statistics about the comparison
    """
    # Find the result file for this run_id
    if not os.path.exists(RESULTS_DIR):
        return {"error": "Results directory not found"}

    result_file = None
    for file in os.listdir(RESULTS_DIR):
        if file.endswith(".json") and run_id in file:
            result_file = os.path.join(RESULTS_DIR, file)
            break

    if not result_file:
        return {"error": f"No results found for run_id: {run_id}"}

    try:
        with open(result_file) as f:
            result_data = json.load(f)

        # Find the specific step (try both "steps" and "results" keys)
        steps = result_data.get("steps", result_data.get("results", []))
        target_step = None

        for step in steps:
            # Check both "step_name" and "name" keys
            step_id = step.get("step_name", step.get("name"))
            if step_id == step_name:
                target_step = step
                break

        if not target_step:
            return {"error": f"Step '{step_name}' not found in run {run_id}"}

        # Check if comparison_details exists (check both at top level and in details)
        details = target_step.get("details", {})
        if "comparison_details" not in target_step and "comparison_details" not in details:
            return {
                "error": "No comparison details available for this step",
                "message": target_step.get("message", details.get("message", "No detailed comparison data"))
            }

        # Return the comparison details with summary (check both locations)
        comparison_details = target_step.get("comparison_details", details.get("comparison_details"))

        return {
            "run_id": run_id,
            "step_name": step_name,
            "status": target_step.get("status"),
            "difference_type": target_step.get("difference_type", details.get("difference_type", "unknown")),
            "summary": {
                "total_rows": target_step.get("sql_row_count", details.get("sql_row_count", 0)),
                "differing_rows": target_step.get("differing_rows_count", details.get("differing_rows_count", 0)),
                "affected_columns": target_step.get("affected_columns", details.get("affected_columns", [])),
                "message": target_step.get("message", details.get("message", ""))
            },
            "comparison": comparison_details
        }

    except Exception as e:
        return {"error": f"Failed to load comparison details: {str(e)}"}


@router.get("/compare/{run_id_1}/vs/{run_id_2}")
def compare_pipeline_runs(run_id_1: str, run_id_2: str):
    """
    Compare two pipeline runs to show improvements and regressions.

    Returns a comprehensive comparison showing:
    - Step-by-step comparison
    - Error count changes (increased/decreased)
    - New errors introduced
    - Fixed errors
    - Overall trend (improving/degrading/stable)
    """
    try:
        # Load both run results
        run1_data = _load_run_data(run_id_1)
        run2_data = _load_run_data(run_id_2)

        if "error" in run1_data:
            raise HTTPException(status_code=404, detail=f"Run 1 not found: {run1_data['error']}")
        if "error" in run2_data:
            raise HTTPException(status_code=404, detail=f"Run 2 not found: {run2_data['error']}")

        # Extract steps from both runs
        steps1 = run1_data.get("steps", run1_data.get("results", []))
        steps2 = run2_data.get("steps", run2_data.get("results", []))

        # Create step lookup by name
        steps1_map = {step.get("step_name", step.get("name")): step for step in steps1}
        steps2_map = {step.get("step_name", step.get("name")): step for step in steps2}

        # Compare each step
        step_comparisons = []
        all_step_names = set(steps1_map.keys()) | set(steps2_map.keys())

        total_errors_run1 = 0
        total_errors_run2 = 0
        improved_steps = 0
        degraded_steps = 0
        stable_steps = 0
        new_errors = []
        fixed_errors = []

        for step_name in sorted(all_step_names):
            step1 = steps1_map.get(step_name)
            step2 = steps2_map.get(step_name)

            comparison = {
                "step_name": step_name,
                "exists_in_run1": step1 is not None,
                "exists_in_run2": step2 is not None
            }

            if step1 and step2:
                # Both steps exist - compare them
                status1 = step1.get("status", "unknown")
                status2 = step2.get("status", "unknown")

                # Count errors
                errors1 = _count_errors_in_step(step1)
                errors2 = _count_errors_in_step(step2)

                total_errors_run1 += errors1
                total_errors_run2 += errors2

                error_delta = errors2 - errors1

                comparison.update({
                    "run1_status": status1,
                    "run2_status": status2,
                    "run1_errors": errors1,
                    "run2_errors": errors2,
                    "error_delta": error_delta,
                    "status_changed": status1 != status2,
                    "trend": "improved" if error_delta < 0 else ("degraded" if error_delta > 0 else "stable")
                })

                if error_delta < 0:
                    improved_steps += 1
                elif error_delta > 0:
                    degraded_steps += 1
                else:
                    stable_steps += 1

            elif step1 and not step2:
                # Step removed in run2
                comparison["change"] = "removed"
                errors1 = _count_errors_in_step(step1)
                total_errors_run1 += errors1
                comparison["run1_errors"] = errors1

            elif not step1 and step2:
                # New step in run2
                comparison["change"] = "added"
                errors2 = _count_errors_in_step(step2)
                total_errors_run2 += errors2
                comparison["run2_errors"] = errors2
                new_errors.append(step_name)

            step_comparisons.append(comparison)

        # Overall trend
        overall_error_delta = total_errors_run2 - total_errors_run1
        if overall_error_delta < 0:
            overall_trend = "improving"
        elif overall_error_delta > 0:
            overall_trend = "degrading"
        else:
            overall_trend = "stable"

        return {
            "status": "success",
            "run1": {
                "run_id": run_id_1,
                "timestamp": run1_data.get("timestamp", run1_data.get("execution_time")),
                "total_errors": total_errors_run1,
                "total_steps": len(steps1_map)
            },
            "run2": {
                "run_id": run_id_2,
                "timestamp": run2_data.get("timestamp", run2_data.get("execution_time")),
                "total_errors": total_errors_run2,
                "total_steps": len(steps2_map)
            },
            "comparison_summary": {
                "overall_trend": overall_trend,
                "total_error_delta": overall_error_delta,
                "error_delta_percentage": round((overall_error_delta / max(total_errors_run1, 1)) * 100, 2),
                "improved_steps": improved_steps,
                "degraded_steps": degraded_steps,
                "stable_steps": stable_steps,
                "new_steps": len([c for c in step_comparisons if c.get("change") == "added"]),
                "removed_steps": len([c for c in step_comparisons if c.get("change") == "removed"])
            },
            "step_comparisons": step_comparisons
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/project-summary")
def get_project_summary():
    """
    Generate a comprehensive project summary for Tech Lead view.

    Analyzes all pipeline runs to provide:
    - Error trends over time
    - Most problematic validation steps
    - Success rate trends
    - Overall project health score
    - Recommendations
    """
    try:
        # Load all results
        all_results = []
        if os.path.exists(RESULTS_DIR):
            for file in os.listdir(RESULTS_DIR):
                if file.endswith(".json"):
                    try:
                        with open(os.path.join(RESULTS_DIR, file)) as f:
                            all_results.append(json.load(f))
                    except Exception as e:
                        print(f"Error reading {file}: {e}")

        if not all_results:
            return {
                "status": "no_data",
                "message": "No pipeline runs found"
            }

        # Sort by timestamp
        all_results.sort(key=lambda x: x.get("timestamp", x.get("execution_time", "")))

        # Analyze trends
        error_trend_data = []
        step_error_counts = defaultdict(int)
        step_failure_counts = defaultdict(int)
        step_total_runs = defaultdict(int)
        total_runs = len(all_results)
        total_errors_all_runs = 0

        for result in all_results:
            steps = result.get("steps", result.get("results", []))
            run_errors = 0

            for step in steps:
                step_name = step.get("step_name", step.get("name"))
                step_total_runs[step_name] += 1

                errors = _count_errors_in_step(step)
                run_errors += errors

                if errors > 0:
                    step_error_counts[step_name] += errors
                    step_failure_counts[step_name] += 1

            total_errors_all_runs += run_errors

            error_trend_data.append({
                "run_id": result.get("run_id"),
                "timestamp": result.get("timestamp", result.get("execution_time")),
                "total_errors": run_errors,
                "total_steps": len(steps),
                "failed_steps": sum(1 for step in steps if step.get("status") == "failed")
            })

        # Calculate most problematic steps
        problematic_steps = []
        for step_name in step_error_counts.keys():
            failure_rate = (step_failure_counts[step_name] / step_total_runs[step_name]) * 100
            problematic_steps.append({
                "step_name": step_name,
                "total_errors": step_error_counts[step_name],
                "failure_count": step_failure_counts[step_name],
                "total_runs": step_total_runs[step_name],
                "failure_rate": round(failure_rate, 2)
            })

        # Sort by total errors descending
        problematic_steps.sort(key=lambda x: x["total_errors"], reverse=True)

        # Calculate trend (last 5 runs vs previous runs)
        recent_runs = error_trend_data[-5:] if len(error_trend_data) >= 5 else error_trend_data
        older_runs = error_trend_data[:-5] if len(error_trend_data) > 5 else []

        recent_avg_errors = sum(r["total_errors"] for r in recent_runs) / len(recent_runs) if recent_runs else 0
        older_avg_errors = sum(r["total_errors"] for r in older_runs) / len(older_runs) if older_runs else recent_avg_errors

        if recent_avg_errors < older_avg_errors * 0.9:
            trend_direction = "improving"
        elif recent_avg_errors > older_avg_errors * 1.1:
            trend_direction = "degrading"
        else:
            trend_direction = "stable"

        # Calculate health score (0-100)
        # Lower errors = higher score
        avg_errors_per_run = total_errors_all_runs / total_runs if total_runs > 0 else 0
        health_score = max(0, min(100, 100 - (avg_errors_per_run * 2)))  # Rough calculation

        # Generate recommendations
        recommendations = _generate_recommendations(
            problematic_steps,
            trend_direction,
            health_score,
            error_trend_data
        )

        return {
            "status": "success",
            "summary": {
                "total_runs": total_runs,
                "total_errors_all_time": total_errors_all_runs,
                "average_errors_per_run": round(avg_errors_per_run, 2),
                "health_score": round(health_score, 2),
                "trend_direction": trend_direction,
                "recent_avg_errors": round(recent_avg_errors, 2),
                "older_avg_errors": round(older_avg_errors, 2)
            },
            "error_trend": error_trend_data,
            "problematic_steps": problematic_steps[:10],  # Top 10
            "recommendations": recommendations,
            "latest_run": error_trend_data[-1] if error_trend_data else None,
            "oldest_run": error_trend_data[0] if error_trend_data else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate project summary: {str(e)}")


def _load_run_data(run_id: str) -> Dict:
    """Load run data from results directory"""
    if not os.path.exists(RESULTS_DIR):
        return {"error": "Results directory not found"}

    for file in os.listdir(RESULTS_DIR):
        if file.endswith(".json") and run_id in file:
            try:
                with open(os.path.join(RESULTS_DIR, file)) as f:
                    return json.load(f)
            except Exception as e:
                return {"error": f"Failed to load run data: {str(e)}"}

    return {"error": f"Run {run_id} not found"}


def _count_errors_in_step(step: Dict) -> int:
    """Count total errors in a validation step"""
    # Try different possible error count keys
    error_count = 0

    # Direct error count
    if "error_count" in step:
        error_count = step["error_count"]
    elif "differing_rows_count" in step:
        error_count = step["differing_rows_count"]

    # Check details
    details = step.get("details", {})
    if "differing_rows_count" in details:
        error_count = max(error_count, details["differing_rows_count"])

    # Check if step failed
    if step.get("status") == "failed" and error_count == 0:
        error_count = 1  # At least count as 1 error if failed

    return error_count


def _generate_recommendations(problematic_steps: List[Dict], trend: str, health_score: float, error_trend: List[Dict]) -> List[str]:
    """Generate actionable recommendations based on analysis"""
    recommendations = []

    # Health-based recommendations
    if health_score < 50:
        recommendations.append("CRITICAL: Project health is low. Immediate attention required on failing validations.")
    elif health_score < 70:
        recommendations.append("WARNING: Project health is below target. Focus on reducing error rates.")
    else:
        recommendations.append("GOOD: Project health is acceptable. Continue monitoring trends.")

    # Trend-based recommendations
    if trend == "degrading":
        recommendations.append("ALERT: Error trend is degrading. Recent runs show more errors than previous runs.")
        recommendations.append("ACTION: Review recent code/data changes that may have introduced regressions.")
    elif trend == "improving":
        recommendations.append("POSITIVE: Error trend is improving. Recent fixes are having positive impact.")

    # Step-specific recommendations
    if problematic_steps:
        top_problem = problematic_steps[0]
        if top_problem["failure_rate"] > 80:
            recommendations.append(f"PRIORITY: Step '{top_problem['step_name']}' fails {top_problem['failure_rate']}% of the time. Requires immediate investigation.")
        elif top_problem["failure_rate"] > 50:
            recommendations.append(f"FOCUS: Step '{top_problem['step_name']}' has high failure rate ({top_problem['failure_rate']}%). Review validation logic or data quality.")

    # Stability recommendations
    if len(error_trend) >= 5:
        last_5_errors = [r["total_errors"] for r in error_trend[-5:]]
        if len(set(last_5_errors)) == 1:
            recommendations.append("INFO: Error count is stable across recent runs. No significant changes detected.")
        else:
            variance = max(last_5_errors) - min(last_5_errors)
            if variance > 10:
                recommendations.append("NOTE: High variance in error counts across recent runs. Investigate data consistency.")

    return recommendations