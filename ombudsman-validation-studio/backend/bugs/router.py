"""
Bug Reporting API Router

Provides HTTP endpoints for bug report generation, review, and export.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional, List
from pathlib import Path
import json

from .models import (
    GenerateBugReportRequest,
    BugReportGenerateResponse,
    BugReviewRequest,
    BugReport,
    BugReportListResponse,
    BugReportDownloadFormat,
    SubmitToAzureDevOpsRequest,
    Bug,
    BugStatus
)
from .bug_report_service import BugReportService
from .azure_devops_service import AzureDevOpsService
from .excel_export import excel_exporter

router = APIRouter(prefix="/bug-reports", tags=["Bug Reports"])

# Initialize service
bug_service = BugReportService()


@router.post("/generate", response_model=BugReportGenerateResponse)
async def generate_bug_report(
    request: GenerateBugReportRequest,
    project_id: Optional[str] = None,  # From query or active project
    user: Optional[str] = None  # From auth context
):
    """
    Generate a bug report from batch execution results.

    This analyzes all failures and errors from a batch job execution,
    creating structured bug entries with severity, category, and details.

    Args:
        request: Bug report generation parameters
        project_id: Project ID (optional, will use active project if not provided)
        user: Current user (from auth context)

    Returns:
        BugReportGenerateResponse with report ID and summary

    Raises:
        404: Batch results not found
        400: Invalid request or batch results
    """
    try:
        # Get active project if not provided
        if not project_id:
            # Read active project from file
            active_project_file = Path("data/active_project.txt")
            if active_project_file.exists():
                project_id = active_project_file.read_text().strip()
            else:
                project_id = "default"  # Fallback

        # Get project name
        project_data_dir = Path("data/projects") / project_id
        project_file = project_data_dir / "metadata.json"
        if not project_file.exists():
            project_file = project_data_dir / "project.json"

        if project_file.exists():
            import json as json_module
            with open(project_file, 'r') as f:
                project_data = json_module.load(f)
                project_name = project_data.get('name', project_id)
        else:
            project_name = project_id

        # Generate report
        report = bug_service.generate_bug_report(
            request=request,
            project_id=project_id,
            project_name=project_name,
            user=user
        )

        return BugReportGenerateResponse(
            report_id=report.report_id,
            total_bugs=len(report.bugs),
            summary=report.summary,
            message=f"Successfully generated bug report with {len(report.bugs)} bugs"
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate bug report: {str(e)}")


@router.get("/{report_id}", response_model=BugReport)
async def get_bug_report(report_id: str):
    """
    Retrieve a bug report by ID.

    Args:
        report_id: Bug report ID

    Returns:
        Complete BugReport object

    Raises:
        404: Report not found
    """
    report = bug_service.load_report(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Bug report {report_id} not found")

    return report


@router.post("/{report_id}/review", response_model=BugReport)
async def review_bugs(
    report_id: str,
    request: BugReviewRequest
):
    """
    Review bugs in a report (approve/reject).

    This updates the status of selected bugs to APPROVED or REJECTED.
    Only approved bugs can be submitted to Azure DevOps.

    Args:
        report_id: Bug report ID
        request: Review request with bug IDs to approve/reject

    Returns:
        Updated BugReport

    Raises:
        404: Report not found
    """
    try:
        report = bug_service.update_bug_statuses(
            report_id=report_id,
            approved_bug_ids=request.approved_bug_ids,
            rejected_bug_ids=request.rejected_bug_ids
        )

        return report

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review bugs: {str(e)}")


@router.get("/{report_id}/download/{format}")
async def download_bug_report(
    report_id: str,
    format: BugReportDownloadFormat
):
    """
    Download bug report in specified format.

    Supports: PDF, JSON, Excel, CSV

    Args:
        report_id: Bug report ID
        format: Download format (pdf, json, excel, csv)

    Returns:
        File download response

    Raises:
        404: Report not found
        400: Invalid format
    """
    report = bug_service.load_report(report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Bug report {report_id} not found")

    try:
        if format == BugReportDownloadFormat.JSON:
            # Return JSON directly
            return JSONResponse(
                content=json.loads(report.json()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.json"
                }
            )

        elif format == BugReportDownloadFormat.EXCEL:
            # Generate Excel file
            excel_path = excel_exporter.generate_excel_report(report)

            if not excel_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate Excel file"
                )

            # Return file
            return FileResponse(
                path=str(excel_path),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"{report.batch_job_name}_bug_report_{report_id}.xlsx",
                headers={
                    "Content-Disposition": f"attachment; filename={report.batch_job_name}_bug_report_{report_id}.xlsx"
                }
            )

        elif format == BugReportDownloadFormat.CSV:
            # Generate CSV (basic implementation)
            import csv
            import io

            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)

            # Headers
            writer.writerow([
                'Bug ID', 'Title', 'Severity', 'Category', 'Status',
                'Step Name', 'Validation Type', 'Table', 'Column',
                'Expected Value', 'Actual Value', 'Failure Count',
                'Error Message', 'Work Item ID'
            ])

            # Data rows
            for bug in report.bugs:
                writer.writerow([
                    bug.bug_id,
                    bug.title,
                    bug.severity.upper(),
                    bug.category.replace('_', ' ').title(),
                    bug.status.replace('_', ' ').title(),
                    bug.step_name,
                    bug.validation_type,
                    bug.table_name or '',
                    bug.column_name or '',
                    bug.expected_value or '',
                    bug.actual_value or '',
                    bug.failure_count or '',
                    bug.error_message or '',
                    bug.work_item_id or ''
                ])

            # Return CSV
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.csv"
                }
            )

        elif format == BugReportDownloadFormat.PDF:
            # PDF not implemented - suggest Excel instead
            raise HTTPException(
                status_code=501,
                detail="PDF generation not implemented. Please use Excel format for a comprehensive report with formatting and sample data."
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download: {str(e)}")


@router.get("/", response_model=BugReportListResponse)
async def list_bug_reports(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of reports to return"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    List bug reports with optional filtering.

    Args:
        project_id: Filter by project (optional)
        limit: Max reports per page
        page: Page number (1-indexed)

    Returns:
        BugReportListResponse with paginated reports
    """
    try:
        # Get all reports
        all_reports = bug_service.list_reports(project_id=project_id, limit=limit * page)

        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_reports = all_reports[start_idx:end_idx]

        return BugReportListResponse(
            reports=page_reports,
            total=len(all_reports),
            page=page,
            page_size=len(page_reports)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.delete("/{report_id}")
async def delete_bug_report(report_id: str):
    """
    Delete a bug report.

    Args:
        report_id: Bug report ID

    Returns:
        Success message

    Raises:
        404: Report not found
    """
    report_file = bug_service.reports_dir / f"{report_id}.json"

    if not report_file.exists():
        raise HTTPException(status_code=404, detail=f"Bug report {report_id} not found")

    try:
        report_file.unlink()
        return {"message": f"Bug report {report_id} deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


@router.post("/{report_id}/submit-to-azure")
async def submit_bugs_to_azure_devops(
    report_id: str,
    request: Optional[SubmitToAzureDevOpsRequest] = None
):
    """
    Submit approved bugs to Azure DevOps.

    This endpoint will:
    1. Load the bug report
    2. Get the project's Azure DevOps configuration
    3. Validate configuration exists (per user requirement)
    4. Initialize Azure DevOps service
    5. Submit only APPROVED bugs to Azure DevOps
    6. Update bug report with work item IDs and URLs

    Args:
        report_id: Bug report ID
        request: Optional submission request with specific bug IDs and overrides

    Returns:
        Submission results with work item details

    Raises:
        404: Report not found
        400: Azure DevOps not configured or no approved bugs
        500: Submission failed
    """
    try:
        # 1. Load bug report
        report = bug_service.load_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Bug report {report_id} not found")

        # 2. Load project's Azure DevOps configuration
        project_id = report.project_id
        project_data_dir = Path("data/projects") / project_id

        # Try both metadata.json and project.json for backward compatibility
        project_file = project_data_dir / "metadata.json"
        if not project_file.exists():
            project_file = project_data_dir / "project.json"

        if not project_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found. Cannot retrieve Azure DevOps configuration."
            )

        with open(project_file, 'r') as f:
            project_data = json.load(f)

        # 3. Validate Azure DevOps configuration exists
        azure_config = project_data.get('azure_devops')
        if not azure_config or not azure_config.get('enabled'):
            raise HTTPException(
                status_code=400,
                detail="Azure DevOps is not configured for this project. Please configure Azure DevOps in project settings before creating bugs."
            )

        # 4. Get bugs to submit
        if request and request.bug_ids:
            # Submit specific bugs requested
            bugs_to_submit = [bug for bug in report.bugs if bug.bug_id in request.bug_ids and bug.status == BugStatus.APPROVED]
        else:
            # Submit all approved bugs
            bugs_to_submit = [bug for bug in report.bugs if bug.status == BugStatus.APPROVED]

        if not bugs_to_submit:
            raise HTTPException(
                status_code=400,
                detail="No approved bugs found to submit. Please review and approve bugs before submitting to Azure DevOps."
            )

        # 5. Initialize Azure DevOps service
        azure_service = AzureDevOpsService(
            organization_url=azure_config['organization_url'],
            project_name=azure_config['project_name'],
            pat_token=azure_config['pat_token']
        )

        # 6. Test connection first
        connection_test = azure_service.test_connection()
        if not connection_test['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Azure DevOps connection failed: {connection_test['message']}"
            )

        # 7. Determine work item settings (request overrides > config defaults)
        work_item_type = (request.work_item_type if request and request.work_item_type
                         else azure_config.get('work_item_type', 'Bug'))
        area_path = (request.area_path if request and request.area_path
                    else azure_config.get('area_path'))
        iteration_path = (request.iteration_path if request and request.iteration_path
                         else azure_config.get('iteration_path'))
        assigned_to = (request.assigned_to if request and request.assigned_to
                      else azure_config.get('assigned_to'))

        # Combine auto-tags with additional tags
        auto_tags = azure_config.get('auto_tags', [])
        additional_tags = request.additional_tags if request and request.additional_tags else []
        all_tags = list(set(auto_tags + additional_tags))  # Remove duplicates

        # 8. Submit bugs in batch
        submission_results = azure_service.create_bugs_batch(
            bugs=bugs_to_submit,
            work_item_type=work_item_type,
            area_path=area_path,
            iteration_path=iteration_path,
            assigned_to=assigned_to,
            tags=all_tags
        )

        # 9. Update bug report with work item IDs
        for work_item_info in submission_results['work_items']:
            bug_id = work_item_info['bug_id']
            for bug in report.bugs:
                if bug.bug_id == bug_id:
                    bug.work_item_id = work_item_info['work_item_id']
                    bug.work_item_url = work_item_info['work_item_url']
                    bug.status = BugStatus.CREATED_IN_AZURE
                    from datetime import datetime
                    bug.created_in_azure_at = datetime.utcnow()
                    break

        # Mark failed bugs
        for bug_id, error_msg in submission_results.get('errors', {}).items():
            for bug in report.bugs:
                if bug.bug_id == bug_id:
                    bug.status = BugStatus.FAILED_TO_CREATE
                    bug.error_message = error_msg
                    break

        # Update submission tracking
        report.submitted_to_azure = True
        report.approved_count = len([b for b in report.bugs if b.status == BugStatus.APPROVED])

        # Save updated report
        bug_service._save_report(report)

        # 10. Return results
        return {
            "success": True,
            "message": f"Submitted {submission_results['created']} bugs to Azure DevOps",
            "total_bugs": submission_results['total'],
            "created": submission_results['created'],
            "failed": submission_results['failed'],
            "work_items": submission_results['work_items'],
            "errors": submission_results.get('errors', {}),
            "report_id": report_id,
            "project_id": project_id
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Azure DevOps configuration: missing field {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit bugs to Azure DevOps: {str(e)}"
        )
