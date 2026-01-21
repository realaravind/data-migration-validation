"""
Azure DevOps Service

Handles interaction with Azure DevOps REST API for creating work items.
"""

import requests
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import Bug, BugReport, BugSeverity


class AzureDevOpsService:
    """Service for interacting with Azure DevOps REST API"""

    def __init__(self, organization_url: str, project_name: str, pat_token: str):
        """
        Initialize Azure DevOps service.

        Args:
            organization_url: Azure DevOps organization URL (e.g., https://dev.azure.com/myorg)
            project_name: Azure DevOps project name
            pat_token: Personal Access Token
        """
        self.organization_url = organization_url.rstrip('/')
        self.project_name = project_name
        self.pat_token = pat_token
        self.api_version = "7.1"

        # Create base64 encoded auth header
        auth_string = f":{pat_token}"
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode('ascii')

        self.headers = {
            'Authorization': f'Basic {base64_string}',
            'Content-Type': 'application/json-patch+json',
            'Accept': 'application/json'
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Azure DevOps.

        Returns:
            Dict with connection status and details
        """
        try:
            # Try to get project information
            url = f"{self.organization_url}/_apis/projects/{self.project_name}?api-version={self.api_version}"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                project_data = response.json()
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'project_id': project_data.get('id'),
                    'project_name': project_data.get('name'),
                    'organization_name': self.organization_url.split('/')[-1]
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to connect: {response.status_code} - {response.text}',
                    'error_details': response.text
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Connection timeout - please check your network and Azure DevOps URL',
                'error_details': 'Request timed out after 10 seconds'
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'message': 'Connection error - please check your Azure DevOps URL',
                'error_details': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'error_details': str(e)
            }

    def create_bug_work_item(
        self,
        bug: Bug,
        work_item_type: str = "Bug",
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a work item in Azure DevOps from a Bug.

        Args:
            bug: Bug object to create work item from
            work_item_type: Type of work item (Bug, Task, User Story, Issue)
            area_path: Area path for the work item
            iteration_path: Iteration path for the work item
            assigned_to: Email of person to assign to
            tags: Additional tags to add

        Returns:
            Dict with creation status and work item details
        """
        try:
            url = f"{self.organization_url}/{self.project_name}/_apis/wit/workitems/${work_item_type}?api-version={self.api_version}"

            # Build the JSON patch document for creating work item
            operations = []

            # Title
            operations.append({
                "op": "add",
                "path": "/fields/System.Title",
                "value": bug.title
            })

            # Description with rich formatting
            description = self._format_bug_description(bug)
            operations.append({
                "op": "add",
                "path": "/fields/System.Description",
                "value": description
            })

            # Priority based on severity
            priority = self._map_severity_to_priority(bug.severity)
            operations.append({
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.Priority",
                "value": priority
            })

            # Severity
            severity = self._map_severity_to_azure_severity(bug.severity)
            operations.append({
                "op": "add",
                "path": "/fields/Microsoft.VSTS.Common.Severity",
                "value": severity
            })

            # Area path
            if area_path:
                operations.append({
                    "op": "add",
                    "path": "/fields/System.AreaPath",
                    "value": area_path
                })

            # Iteration path
            if iteration_path:
                operations.append({
                    "op": "add",
                    "path": "/fields/System.IterationPath",
                    "value": iteration_path
                })

            # Assigned to
            if assigned_to:
                operations.append({
                    "op": "add",
                    "path": "/fields/System.AssignedTo",
                    "value": assigned_to
                })

            # Tags
            all_tags = bug.tags.copy() if bug.tags else []
            if tags:
                all_tags.extend(tags)
            if all_tags:
                operations.append({
                    "op": "add",
                    "path": "/fields/System.Tags",
                    "value": "; ".join(all_tags)
                })

            # Repro steps (detailed information)
            repro_steps = self._format_repro_steps(bug)
            operations.append({
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.ReproSteps",
                "value": repro_steps
            })

            # Make the API call
            response = requests.post(
                url,
                headers=self.headers,
                json=operations,
                timeout=30
            )

            if response.status_code in [200, 201]:
                work_item = response.json()
                return {
                    'success': True,
                    'work_item_id': work_item['id'],
                    'work_item_url': work_item['_links']['html']['href'],
                    'message': f"Work item #{work_item['id']} created successfully",
                    'response': work_item
                }
            else:
                return {
                    'success': False,
                    'message': f"Failed to create work item: {response.status_code}",
                    'error_details': response.text,
                    'response': response.json() if response.text else None
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Request timeout while creating work item',
                'error_details': 'Request timed out after 30 seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating work item: {str(e)}',
                'error_details': str(e)
            }

    def create_bugs_batch(
        self,
        bugs: List[Bug],
        work_item_type: str = "Bug",
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create multiple bug work items in Azure DevOps.

        Args:
            bugs: List of Bug objects
            work_item_type: Type of work item
            area_path: Area path
            iteration_path: Iteration path
            assigned_to: Email of assignee
            tags: Additional tags

        Returns:
            Dict with batch creation results
        """
        results = {
            'total': len(bugs),
            'created': 0,
            'failed': 0,
            'work_items': [],
            'errors': {}
        }

        for bug in bugs:
            result = self.create_bug_work_item(
                bug=bug,
                work_item_type=work_item_type,
                area_path=area_path,
                iteration_path=iteration_path,
                assigned_to=assigned_to,
                tags=tags
            )

            if result['success']:
                results['created'] += 1
                results['work_items'].append({
                    'bug_id': bug.bug_id,
                    'work_item_id': result['work_item_id'],
                    'work_item_url': result['work_item_url']
                })
            else:
                results['failed'] += 1
                results['errors'][bug.bug_id] = result['message']

        return results

    def _format_bug_description(self, bug: Bug) -> str:
        """Format bug description in HTML for Azure DevOps"""
        html = f"<div><h3>Bug Report</h3>"
        html += f"<p><strong>Severity:</strong> {bug.severity.upper()}</p>"
        html += f"<p><strong>Category:</strong> {bug.category.replace('_', ' ').title()}</p>"

        if bug.table_name:
            html += f"<p><strong>Table:</strong> {bug.table_name}</p>"

        if bug.column_name:
            html += f"<p><strong>Column:</strong> {bug.column_name}</p>"

        html += f"<h4>Description</h4>"
        html += f"<p>{bug.description.replace(chr(10), '<br/>')}</p>"

        if bug.error_message:
            html += f"<h4>Error Message</h4>"
            html += f"<pre>{bug.error_message}</pre>"

        html += "</div>"
        return html

    def _format_repro_steps(self, bug: Bug) -> str:
        """Format reproduction steps in HTML"""
        html = "<div><h3>Reproduction Details</h3>"
        html += f"<p><strong>Batch Job ID:</strong> {bug.batch_job_id}</p>"
        html += f"<p><strong>Step Name:</strong> {bug.step_name}</p>"
        html += f"<p><strong>Validation Type:</strong> {bug.validation_type}</p>"

        if bug.run_id:
            html += f"<p><strong>Run ID:</strong> {bug.run_id}</p>"

        if bug.expected_value or bug.actual_value:
            html += "<h4>Values</h4>"
            if bug.expected_value:
                html += f"<p><strong>Expected:</strong> {bug.expected_value}</p>"
            if bug.actual_value:
                html += f"<p><strong>Actual:</strong> {bug.actual_value}</p>"

        if bug.failure_count is not None:
            html += f"<p><strong>Failure Count:</strong> {bug.failure_count:,}</p>"
            if bug.failure_percentage is not None:
                html += f"<p><strong>Failure Rate:</strong> {bug.failure_percentage:.2f}%</p>"

        if bug.row_count is not None:
            html += f"<p><strong>Total Rows:</strong> {bug.row_count:,}</p>"

        if bug.sample_data and len(bug.sample_data) > 0:
            html += "<h4>Sample Data</h4>"
            html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"

            # Headers
            headers = list(bug.sample_data[0].keys())
            html += "<tr style='background-color: #f0f0f0;'>"
            for header in headers:
                html += f"<th style='padding: 5px;'>{header}</th>"
            html += "</tr>"

            # Rows (limit to 5)
            for row in bug.sample_data[:5]:
                html += "<tr>"
                for header in headers:
                    value = row.get(header, '')
                    html += f"<td style='padding: 5px;'>{value}</td>"
                html += "</tr>"

            html += "</table>"

            if len(bug.sample_data) > 5:
                html += f"<p><em>Showing 5 of {len(bug.sample_data)} sample rows</em></p>"

        html += "</div>"
        return html

    def _map_severity_to_priority(self, severity: BugSeverity) -> int:
        """Map bug severity to Azure DevOps priority (1-4)"""
        mapping = {
            BugSeverity.CRITICAL: 1,
            BugSeverity.HIGH: 1,
            BugSeverity.MEDIUM: 2,
            BugSeverity.LOW: 3,
            BugSeverity.INFO: 4
        }
        return mapping.get(severity, 2)

    def _map_severity_to_azure_severity(self, severity: BugSeverity) -> str:
        """Map bug severity to Azure DevOps severity string"""
        mapping = {
            BugSeverity.CRITICAL: "1 - Critical",
            BugSeverity.HIGH: "2 - High",
            BugSeverity.MEDIUM: "3 - Medium",
            BugSeverity.LOW: "4 - Low",
            BugSeverity.INFO: "4 - Low"
        }
        return mapping.get(severity, "3 - Medium")
