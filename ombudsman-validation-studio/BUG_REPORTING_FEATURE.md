# Bug Reporting & Azure DevOps Integration Feature

## Overview
Complete bug reporting and Azure DevOps integration feature for batch validation results. This allows users to generate bug reports from failed validations and optionally submit them to Azure DevOps as work items.

## Features Implemented

### 1. Bug Report Generation
- **Automatic Analysis**: Analyzes batch job validation results and creates structured bug entries
- **Severity Classification**: Intelligently determines bug severity (Critical, High, Medium, Low, Info)
- **Category Classification**: Groups bugs by validation category (schema, data_quality, referential_integrity, etc.)
- **Sample Data Collection**: Includes up to 10 sample rows for each bug to aid debugging
- **Comprehensive Details**: Captures all relevant context (table, column, expected/actual values, failure count)

### 2. Bug Review Workflow
- **Status Lifecycle**: PENDING_REVIEW → APPROVED/REJECTED → CREATED_IN_AZURE/FAILED_TO_CREATE
- **Selective Approval**: Users can review and approve/reject individual bugs
- **Bulk Actions**: Support for approving or rejecting multiple bugs at once
- **Visual Review UI**: Interactive interface with filtering, sorting, and detailed bug views

### 3. Azure DevOps Integration
- **Project-Level Configuration**: Configure Azure DevOps settings when creating a project
- **Connection Testing**: Validate credentials before submitting bugs
- **Work Item Creation**: Create bugs, tasks, user stories, or issues in Azure DevOps
- **Custom Fields**: Support for area path, iteration path, assigned to, and tags
- **Batch Submission**: Submit multiple approved bugs in a single operation
- **Tracking**: Automatically link created work items back to bug report

### 4. Excel Export
- **Professional Formatting**: Color-coded severity and status indicators
- **Multiple Sheets**:
  - Summary: Executive overview with statistics
  - Bugs: Detailed filterable bug listing
  - Sample Data: Up to 5 sheets with sample data for bugs (100 rows each)
- **Auto-sized Columns**: Smart column width adjustment
- **Auto-filters**: Freeze panes and filterable headers
- **Rich Formatting**: Professional styling with color schemes

### 5. Additional Export Formats
- **JSON**: Complete bug report data structure
- **CSV**: Simple tabular format for basic analysis
- **PDF**: Not implemented (use Excel instead)

## Architecture

### Backend Components

#### `/backend/bugs/models.py`
Pydantic models defining the data structures:
- `Bug`: Individual bug entry with all details
- `BugReport`: Complete bug report with summary and bugs
- `BugSeverity`: Enum for severity levels
- `BugStatus`: Enum for status lifecycle
- `ValidationCategory`: Enum for bug categories
- `AzureDevOpsConfig`: Azure DevOps configuration model

#### `/backend/bugs/bug_report_service.py`
Core business logic service:
- `generate_bug_report()`: Analyzes batch results and creates bug report
- `_determine_severity()`: Intelligent severity classification
- `_determine_category()`: Categorization logic
- `_extract_sample_data()`: Sample data extraction
- `update_bug_statuses()`: Review workflow management
- `save_report()` / `load_report()`: Persistence

#### `/backend/bugs/azure_devops_service.py`
Azure DevOps REST API integration:
- `test_connection()`: Validate credentials
- `create_bug_work_item()`: Create single work item
- `create_bugs_batch()`: Batch work item creation
- `_format_bug_description()`: HTML description formatting
- `_format_repro_steps()`: HTML reproduction steps with sample data

#### `/backend/bugs/excel_export.py`
Excel report generation:
- `generate_excel_report()`: Main entry point
- `_create_summary_sheet()`: Executive summary
- `_create_bugs_sheet()`: Bug listing with formatting
- `_create_sample_data_sheet()`: Sample data sheets

#### `/backend/bugs/router.py`
FastAPI HTTP endpoints:
- `POST /bug-reports/generate`: Generate bug report from batch results
- `GET /bug-reports/{report_id}`: Retrieve bug report
- `POST /bug-reports/{report_id}/review`: Approve/reject bugs
- `GET /bug-reports/{report_id}/download/{format}`: Download in various formats
- `GET /bug-reports/`: List all bug reports
- `DELETE /bug-reports/{report_id}`: Delete bug report
- `POST /bug-reports/{report_id}/submit-to-azure`: Submit approved bugs to Azure DevOps

### Frontend Components

#### `/frontend/src/pages/BugReportPreview.tsx`
Complete React component for bug report viewing and review:
- Interactive bug listing with filtering (severity, category, status)
- Detailed bug view with all context and sample data
- Bulk approve/reject functionality
- Export options (Excel, JSON, CSV)
- Submit to Azure DevOps with status tracking
- Summary statistics and charts

#### `/frontend/src/pages/BatchReportViewerSimple.tsx`
Updated to include "Generate Bug Report" button:
- Button in header next to "Download JSON"
- Calls `/bug-reports/generate` API
- Navigates to bug report preview page on success

#### `/frontend/src/App.tsx`
Updated routing:
- `/bug-report/:reportId` - Bug report preview and review page

## Usage Guide

### Step 1: Configure Azure DevOps (Optional)

When creating a project, configure Azure DevOps settings:

```json
{
  "azure_devops": {
    "enabled": true,
    "organization_url": "https://dev.azure.com/your-org",
    "project_name": "YourProject",
    "pat_token": "your-personal-access-token",
    "work_item_type": "Bug",
    "area_path": "YourProject\\Data Migration",
    "iteration_path": "YourProject\\Sprint 1",
    "assigned_to": "user@example.com",
    "auto_tags": ["ombudsman", "data-validation"],
    "tag_prefix": "OVS-"
  }
}
```

### Step 2: Run a Batch Job

Execute a batch job with multiple pipeline validations.

### Step 3: Generate Bug Report

1. Navigate to Batch Operations (`/batch`)
2. Click "View Report" for your completed batch job
3. Click the red "Generate Bug Report" button in the header
4. Wait for analysis to complete (automatic redirect)

### Step 4: Review Bugs

In the Bug Report Preview page:
1. Review the summary statistics
2. Use filters to focus on specific bugs:
   - Filter by severity (Critical, High, Medium, Low, Info)
   - Filter by category (Schema, Data Quality, Referential Integrity, etc.)
   - Filter by status (Pending Review, Approved, Rejected, etc.)
3. Select bugs to approve or reject
4. Click "Approve Selected" or "Reject Selected"

### Step 5: Export or Submit

**Export Options:**
- Click "Download Excel" for a professional formatted report
- Click "Download JSON" for raw data
- Click "Download CSV" for simple tabular format

**Submit to Azure DevOps:**
1. Click "Submit to Azure DevOps" (only if configured)
2. Only approved bugs will be submitted
3. Work item IDs and URLs will be linked back to bug report
4. Status will update to CREATED_IN_AZURE or FAILED_TO_CREATE

## API Examples

### Generate Bug Report
```bash
curl -X POST http://localhost:8000/bug-reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "batch_job_id": "job_123",
    "batch_job_name": "Daily Validation Run",
    "include_sample_data": true,
    "max_samples_per_bug": 10
  }'
```

### Review Bugs
```bash
curl -X POST http://localhost:8000/bug-reports/{report_id}/review \
  -H "Content-Type: application/json" \
  -d '{
    "approved_bug_ids": ["bug_1", "bug_2"],
    "rejected_bug_ids": ["bug_3"]
  }'
```

### Submit to Azure DevOps
```bash
curl -X POST http://localhost:8000/bug-reports/{report_id}/submit-to-azure \
  -H "Content-Type: application/json" \
  -d '{
    "bug_ids": ["bug_1", "bug_2"],
    "work_item_type": "Bug",
    "area_path": "MyProject\\DataMigration",
    "iteration_path": "MyProject\\Sprint1",
    "assigned_to": "user@example.com",
    "additional_tags": ["urgent", "migration"]
  }'
```

### Download Excel Report
```bash
curl -o report.xlsx \
  http://localhost:8000/bug-reports/{report_id}/download/excel
```

## File Locations

### Bug Reports Storage
Bug reports are stored as JSON files in:
```
/backend/bug_reports/{report_id}.json
```

### Excel Exports
Excel files are generated in:
```
/backend/bug_reports/exports/{report_id}.xlsx
```

## Security Considerations

1. **PAT Token Security**: Azure DevOps PAT tokens are masked in API responses
2. **Input Validation**: All inputs are validated using Pydantic models
3. **Error Handling**: Comprehensive error handling with appropriate HTTP status codes
4. **File Permissions**: Bug reports are stored with appropriate file permissions

## Validation Requirements

### For Bug Creation (No Azure DevOps)
- No specific requirements
- Bug reports can always be generated and exported

### For Azure DevOps Submission
- Azure DevOps must be configured for the project
- Configuration must include:
  - organization_url
  - project_name
  - pat_token
  - enabled = true
- Connection must be testable
- Only APPROVED bugs can be submitted

## Troubleshooting

### "Azure DevOps is not configured for this project"
- Configure Azure DevOps settings in project metadata
- Ensure `enabled: true` in azure_devops configuration

### "No approved bugs found to submit"
- Review and approve bugs before submitting
- Check that bugs have status = APPROVED

### "Azure DevOps connection failed"
- Verify organization_url is correct
- Verify PAT token has appropriate permissions
- Check network connectivity to Azure DevOps

### Excel download fails
- Verify openpyxl is installed: `pip install openpyxl==3.1.2`
- Check file permissions in bug_reports/exports/
- Ensure sufficient disk space

## Future Enhancements

Potential improvements:
1. PDF export with professional formatting
2. Automated bug deduplication
3. Machine learning for severity classification
4. Integration with other ticketing systems (Jira, ServiceNow)
5. Scheduled bug report generation
6. Email notifications for new bug reports
7. Bug report templates
8. Custom validation rules for bug classification

## Contact

For questions or issues with this feature, please refer to the main project documentation or contact the development team.

---

**Implementation Date**: January 2026
**Version**: 1.0
**Status**: Production Ready
