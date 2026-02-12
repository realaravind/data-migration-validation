import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    Paper,
    Typography,
    Tabs,
    Tab,
    Button,
    TextField,
    FormControlLabel,
    Checkbox,
    Slider,
    Chip,
    LinearProgress,
    IconButton,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Alert,
    Snackbar,
    Grid,
    Card,
    CardContent,
    Stack,
    Divider,
    FormGroup,
    ToggleButtonGroup,
    ToggleButton,
    Tooltip
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DownloadIcon from '@mui/icons-material/Download';
import AssessmentIcon from '@mui/icons-material/Assessment';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CancelIcon from '@mui/icons-material/Cancel';
import ViewListIcon from '@mui/icons-material/ViewList';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import { useJobWebSocket } from '../hooks/useJobWebSocket';

interface BatchJob {
    job_id: string;
    job_type: string;
    status: string;
    name: string;
    description?: string;
    operations: BatchOperation[];
    progress?: BatchProgress;
    parallel_execution: boolean;
    max_parallel: number;
    stop_on_error: boolean;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    total_duration_ms?: number;
    success_count: number;
    failure_count: number;
    project_id?: string;
    tags: string[];
}

interface BatchOperation {
    operation_id: string;
    operation_type: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    duration_ms?: number;
    result?: any;
    error?: string;
    metadata?: any;
}

interface BatchProgress {
    total_operations: number;
    completed_operations: number;
    failed_operations: number;
    skipped_operations: number;
    current_operation?: string;
    percent_complete: number;
    estimated_time_remaining_ms?: number;
}

const BatchOperations: React.FC = () => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState(0);
    const [jobs, setJobs] = useState<BatchJob[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedJob, setSelectedJob] = useState<BatchJob | null>(null);
    const [detailsOpen, setDetailsOpen] = useState(false);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'info' });

    // Track previous job statuses for detecting state changes
    const prevJobStatusesRef = useRef<Map<string, string>>(new Map());

    // Active project - loaded from API (moved up for WebSocket)
    const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

    // Track known job IDs to detect new jobs
    const knownJobIdsRef = useRef<Set<string>>(new Set());

    // WebSocket for real-time job updates
    const handleWebSocketUpdate = useCallback((update: any) => {
        if (update.type === 'job_update' && update.data) {
            const jobData = update.data;
            console.log('[WebSocket] Job update received:', jobData.job_id, jobData.status, jobData.progress);

            // Check if this is a new job (not in our known set)
            const isNewJob = !knownJobIdsRef.current.has(jobData.job_id);

            if (isNewJob) {
                console.log('[WebSocket] New job detected:', jobData.job_id);
                knownJobIdsRef.current.add(jobData.job_id);

                // Fetch fresh job list to get full job data
                setTimeout(async () => {
                    console.log('[WebSocket] Fetching jobs after new job detected');
                    try {
                        let url = __API_URL__ + '/batch/jobs?limit=100';
                        if (activeProjectId) {
                            url += `&project_id=${activeProjectId}`;
                        }
                        const response = await fetch(url);
                        const data = await response.json();
                        setJobs(data.jobs || []);
                        // Update known IDs
                        (data.jobs || []).forEach((j: any) => knownJobIdsRef.current.add(j.job_id));
                    } catch (error) {
                        console.error('[WebSocket] Failed to fetch jobs:', error);
                    }
                }, 100);
                return;
            }

            // Update existing job
            setJobs(prevJobs => {
                const jobIndex = prevJobs.findIndex(j => j.job_id === jobData.job_id);
                if (jobIndex === -1) {
                    return prevJobs; // Job not in list yet, will be fetched
                }

                const updatedJobs = [...prevJobs];
                const prevStatus = updatedJobs[jobIndex].status;

                updatedJobs[jobIndex] = {
                    ...updatedJobs[jobIndex],
                    status: jobData.status,
                    progress: jobData.progress || updatedJobs[jobIndex].progress,
                    success_count: jobData.success_count ?? updatedJobs[jobIndex].success_count,
                    failure_count: jobData.failure_count ?? updatedJobs[jobIndex].failure_count,
                    started_at: jobData.started_at || updatedJobs[jobIndex].started_at,
                    completed_at: jobData.completed_at || updatedJobs[jobIndex].completed_at,
                    total_duration_ms: jobData.total_duration_ms ?? updatedJobs[jobIndex].total_duration_ms,
                };

                // Show notification on status change to terminal state
                if (prevStatus !== jobData.status) {
                    if (prevStatus === 'running' || prevStatus === 'queued') {
                        if (jobData.status === 'completed') {
                            setSnackbar({
                                open: true,
                                message: `Job "${jobData.name}" completed successfully`,
                                severity: 'success'
                            });
                        } else if (jobData.status === 'failed') {
                            setSnackbar({
                                open: true,
                                message: `Job "${jobData.name}" failed`,
                                severity: 'error'
                            });
                        } else if (jobData.status === 'partial_success') {
                            setSnackbar({
                                open: true,
                                message: `Job "${jobData.name}" completed with some failures`,
                                severity: 'error'
                            });
                        }
                    }
                }

                return updatedJobs;
            });
        }
    }, [activeProjectId]);

    const { connected: wsConnected, reconnect: wsReconnect } = useJobWebSocket(
        activeProjectId,
        handleWebSocketUpdate
    );

    // Filter state for Batch vs Pipeline view
    const [viewFilter, setViewFilter] = useState<'all' | 'batches' | 'pipelines'>('batches');

    // Bulk Pipeline Execution State
    const [pipelineJobName, setPipelineJobName] = useState('');
    const [selectedPipelines, setSelectedPipelines] = useState<string[]>([]);
    const [pipelineParallel, setPipelineParallel] = useState(false);
    const [pipelineMaxParallel, setPipelineMaxParallel] = useState(3);
    const [pipelineStopOnError, setPipelineStopOnError] = useState(false);

    // Batch Data Generation State
    const [dataGenJobName, setDataGenJobName] = useState('');
    const [dataGenRowCount, setDataGenRowCount] = useState(1000);
    const [dataGenParallel, setDataGenParallel] = useState(true);
    const [dataGenSchemas, setDataGenSchemas] = useState<string[]>([]);

    // Available pipelines - loaded from API
    const [availablePipelines, setAvailablePipelines] = useState<any[]>([]);

    // Memoized toggle handler to prevent recreation on every render
    const handlePipelineToggle = useCallback((filename: string) => {
        setSelectedPipelines(prev => {
            if (prev.includes(filename)) {
                return prev.filter(p => p !== filename);
            } else {
                return [...prev, filename];
            }
        });
    }, []);

    // Load initial data - fetch active project first, then jobs
    useEffect(() => {
        const loadData = async () => {
            await fetchActiveProject();
            fetchAvailablePipelines();
        };
        loadData();
    }, []);

    // Fetch jobs when active project changes
    useEffect(() => {
        if (activeProjectId) {
            fetchJobs();
        }
    }, [activeProjectId]);

    // Track if we have active jobs (use ref to avoid re-creating interval)
    const hasActiveJobsRef = useRef(false);
    hasActiveJobsRef.current = jobs.some(j => j.status === 'running' || j.status === 'queued');

    // Track WebSocket connection state with ref (avoids re-creating interval on connect/disconnect)
    const wsConnectedRef = useRef(wsConnected);
    wsConnectedRef.current = wsConnected;

    // Fallback polling - only when WebSocket is disconnected AND we have active jobs
    const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        // Only poll when: WebSocket is disconnected AND there are active jobs
        const shouldPoll = !wsConnected && hasActiveJobsRef.current && activeProjectId;

        if (shouldPoll && !pollingIntervalRef.current) {
            console.log('[BATCH] Starting fallback polling (WebSocket disconnected, active jobs present)');

            const pollJobs = async () => {
                // Double-check conditions
                if (wsConnectedRef.current || !hasActiveJobsRef.current) {
                    return;
                }

                try {
                    const response = await fetch(__API_URL__ + `/batch/jobs?limit=100&project_id=${activeProjectId}`);
                    const data = await response.json();
                    const newJobs = data.jobs || [];

                    // Check for status changes to terminal states
                    const prevStatuses = prevJobStatusesRef.current;
                    for (const job of newJobs) {
                        const prevStatus = prevStatuses.get(job.job_id);
                        if (prevStatus && (prevStatus === 'running' || prevStatus === 'queued')) {
                            if (job.status === 'completed') {
                                setSnackbar({ open: true, message: `Job "${job.name}" completed successfully`, severity: 'success' });
                            } else if (job.status === 'failed') {
                                setSnackbar({ open: true, message: `Job "${job.name}" failed`, severity: 'error' });
                            } else if (job.status === 'partial_success') {
                                setSnackbar({ open: true, message: `Job "${job.name}" completed with some failures`, severity: 'error' });
                            }
                        }
                    }

                    // Update tracked statuses
                    const newStatuses = new Map<string, string>();
                    for (const job of newJobs) {
                        newStatuses.set(job.job_id, job.status);
                    }
                    prevJobStatusesRef.current = newStatuses;

                    setJobs(newJobs);
                } catch (error) {
                    console.error('Failed to fetch jobs:', error);
                }
            };

            pollingIntervalRef.current = setInterval(pollJobs, 5000);
        } else if (!shouldPoll && pollingIntervalRef.current) {
            console.log('[BATCH] Stopping fallback polling (WebSocket connected or no active jobs)');
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }

        return () => {
            if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
            }
        };
    }, [wsConnected, activeProjectId]); // React to WebSocket connection changes

    const fetchJobs = async () => {
        try {
            // Build URL with optional project filter
            let url = __API_URL__ + '/batch/jobs?limit=100';
            if (activeProjectId) {
                url += `&project_id=${activeProjectId}`;
            }

            const response = await fetch(url);
            const data = await response.json();
            const fetchedJobs = data.jobs || [];

            // Initialize status tracking on first load
            if (prevJobStatusesRef.current.size === 0) {
                const statuses = new Map<string, string>();
                for (const job of fetchedJobs) {
                    statuses.set(job.job_id, job.status);
                }
                prevJobStatusesRef.current = statuses;
            }

            // Track known job IDs for WebSocket new job detection
            for (const job of fetchedJobs) {
                knownJobIdsRef.current.add(job.job_id);
            }

            setJobs(fetchedJobs);
        } catch (error) {
            console.error('Failed to fetch jobs:', error);
        }
    };

    const fetchAvailablePipelines = async () => {
        console.log('[BATCH] Fetching pipelines from: ${__API_URL__}/workload/pipelines/list?active_only=true');
        try {
            // Fetch generated pipelines from workload API (active only)
            const response = await fetch(__API_URL__ + '/workload/pipelines/list?active_only=true');
            const data = await response.json();
            console.log('[BATCH] Response status:', response.status, 'Data:', data);

            if (response.ok && data.pipelines) {
                // Store full pipeline objects for better display
                console.log('[BATCH] Setting', data.pipelines.length, 'pipelines:', data.pipelines);
                setAvailablePipelines(data.pipelines);
            } else {
                console.warn('[BATCH] No active pipelines found. Response:', data);
                setAvailablePipelines([]);
            }
        } catch (error) {
            console.error('[BATCH] Failed to fetch pipelines:', error);
            setAvailablePipelines([]);
        }
    };

    const fetchActiveProject = async () => {
        try {
            const response = await fetch(__API_URL__ + '/projects/active');
            const data = await response.json();
            if (response.ok && data.active_project) {
                setActiveProjectId(data.active_project.project_id);
                console.log('[BATCH] Active project:', data.active_project.project_id);
            }
        } catch (error) {
            console.error('[BATCH] Failed to fetch active project:', error);
        }
    };

    const handleBulkPipelineExecution = async () => {
        if (selectedPipelines.length === 0) {
            setSnackbar({ open: true, message: 'Please select at least one pipeline or batch', severity: 'error' });
            return;
        }

        // Check if we're executing a single batch file
        const selectedItems = availablePipelines.filter(p => selectedPipelines.includes(p.filename));
        const isSingleBatch = selectedItems.length === 1 && selectedItems[0].type === 'batch';

        setLoading(true);
        try {
            const token = localStorage.getItem('auth_token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(__API_URL__ + '/batch/pipelines/bulk-execute', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    job_name: pipelineJobName || (isSingleBatch ? selectedItems[0].name : 'Bulk Pipeline Execution'),
                    pipelines: selectedPipelines.map(id => ({ pipeline_id: id })),
                    parallel_execution: pipelineParallel,
                    max_parallel: pipelineMaxParallel,
                    stop_on_error: pipelineStopOnError,
                    project_id: activeProjectId  // Add project context
                })
            });

            if (response.ok) {
                const data = await response.json();
                setSnackbar({ open: true, message: `Batch job created: ${data.job_id}`, severity: 'success' });
                setPipelineJobName('');
                setSelectedPipelines([]);
                setActiveTab(2); // Switch to Active Jobs tab
                // Single fetch - WebSocket will handle updates
                await fetchJobs();
            } else {
                setSnackbar({ open: true, message: 'Failed to create batch job', severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleBulkDataGeneration = async () => {
        if (!dataGenJobName || dataGenSchemas.length === 0) {
            setSnackbar({ open: true, message: 'Please enter job name and select at least one schema', severity: 'error' });
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(__API_URL__ + '/batch/data/bulk-generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_name: dataGenJobName,
                    items: dataGenSchemas.map(schema => ({
                        schema_type: schema,
                        row_count: dataGenRowCount
                    })),
                    parallel_execution: dataGenParallel,
                    max_parallel: 2
                })
            });

            if (response.ok) {
                const data = await response.json();
                setSnackbar({ open: true, message: `Data generation job created: ${data.job_id}`, severity: 'success' });
                setDataGenJobName('');
                setDataGenSchemas([]);
                setActiveTab(2); // Switch to Active Jobs tab
                fetchJobs();
            } else {
                setSnackbar({ open: true, message: 'Failed to create data generation job', severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleCancelJob = async (jobId: string) => {
        try {
            const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: 'User cancelled from UI' })
            });

            if (response.ok) {
                setSnackbar({ open: true, message: 'Job cancelled successfully', severity: 'success' });
                fetchJobs();
            } else {
                setSnackbar({ open: true, message: 'Failed to cancel job', severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        }
    };

    const handleRetryJob = async (jobId: string) => {
        try {
            const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}/retry`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                setSnackbar({ open: true, message: 'Retrying failed operations', severity: 'success' });
                fetchJobs();
            } else {
                setSnackbar({ open: true, message: 'Failed to retry job', severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        }
    };

    const handleDeleteJob = async (jobId: string) => {
        if (!window.confirm('Are you sure you want to delete this job?')) {
            return;
        }

        try {
            const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                setSnackbar({ open: true, message: 'Job deleted successfully', severity: 'success' });
                fetchJobs();
            } else {
                setSnackbar({ open: true, message: 'Failed to delete job', severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        }
    };

    const handleDeleteBatchOrPipeline = async (pipeline: any) => {
        const itemType = pipeline.type === 'batch' ? 'batch' : 'pipeline';
        const itemName = pipeline.name || pipeline.filename;

        // For batches, ask if they want to delete associated pipelines too
        let deletePipelines = false;
        if (pipeline.type === 'batch') {
            const confirmMessage = `Are you sure you want to delete the batch "${itemName}"?\n\nThis batch contains ${pipeline.pipeline_count || 0} pipeline(s).\n\nClick OK to delete ONLY the batch file.\nClick Cancel to abort.\n\nTo also delete the associated pipeline files, select "Yes" in the next prompt.`;

            if (!window.confirm(confirmMessage)) {
                return;
            }

            deletePipelines = window.confirm('Also delete the pipeline files referenced by this batch?');
        } else {
            if (!window.confirm(`Are you sure you want to delete the pipeline "${itemName}"?`)) {
                return;
            }
        }

        setLoading(true);
        try {
            const token = localStorage.getItem('auth_token');
            const headers: HeadersInit = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            let url: string;
            if (pipeline.type === 'batch') {
                url = `${__API_URL__}/workload/batch/${pipeline.filename}?delete_pipelines=${deletePipelines}`;
                if (activeProjectId) {
                    url += `&project_id=${activeProjectId}`;
                }
            } else {
                url = `${__API_URL__}/workload/pipeline/${pipeline.filename}`;
                if (activeProjectId) {
                    url += `?project_id=${activeProjectId}`;
                }
            }

            const response = await fetch(url, {
                method: 'DELETE',
                headers
            });

            if (response.ok) {
                const data = await response.json();
                const deletedCount = data.total_deleted || 1;
                const message = pipeline.type === 'batch'
                    ? `Batch deleted successfully! ${deletedCount} file(s) removed.`
                    : `Pipeline "${itemName}" deleted successfully!`;
                setSnackbar({ open: true, message, severity: 'success' });

                // Refresh the pipelines list
                fetchAvailablePipelines();

                // Remove from selected pipelines if it was selected
                setSelectedPipelines(prev => prev.filter(p => p !== pipeline.filename));
            } else {
                const errorData = await response.json();
                setSnackbar({ open: true, message: errorData.detail || `Failed to delete ${itemType}`, severity: 'error' });
            }
        } catch (error) {
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleViewDetails = async (jobId: string) => {
        try {
            const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}`);
            const data = await response.json();
            setSelectedJob(data.job);
            setDetailsOpen(true);
        } catch (error) {
            setSnackbar({ open: true, message: `Error fetching job details: ${error}`, severity: 'error' });
        }
    };

    const handleExportResults = (job: BatchJob) => {
        const dataStr = JSON.stringify(job, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
        const exportFileDefaultName = `batch_job_${job.job_id}.json`;

        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
    };

    const handleViewReport = (job: BatchJob) => {
        if (job.job_type !== 'bulk_pipeline_execution') {
            setSnackbar({ open: true, message: 'Consolidated reports are only available for pipeline execution jobs', severity: 'info' });
            return;
        }

        if (!['completed', 'partial_success'].includes(job.status)) {
            setSnackbar({ open: true, message: 'Report can only be generated for completed jobs', severity: 'info' });
            return;
        }

        // Navigate to the report viewer page
        window.location.href = `/batch-report/${job.job_id}`;
    };

    const handleDownloadReport = async (job: BatchJob) => {
        if (job.job_type !== 'bulk_pipeline_execution') {
            setSnackbar({ open: true, message: 'Consolidated reports are only available for pipeline execution jobs', severity: 'info' });
            return;
        }

        if (!['completed', 'partial_success'].includes(job.status)) {
            setSnackbar({ open: true, message: 'Report can only be generated for completed jobs', severity: 'info' });
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${__API_URL__}/batch/jobs/${job.job_id}/report`);

            if (!response.ok) {
                const error = await response.json();
                setSnackbar({ open: true, message: error.detail || 'Failed to generate report', severity: 'error' });
                return;
            }

            const data = await response.json();
            const report = data.report;

            // Download as JSON
            const dataStr = JSON.stringify(report, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
            const exportFileDefaultName = `consolidated_report_${job.job_id}_${new Date().toISOString().split('T')[0]}.json`;

            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();

            setSnackbar({ open: true, message: 'Consolidated report downloaded successfully!', severity: 'success' });
        } catch (error) {
            console.error('Error downloading report:', error);
            setSnackbar({ open: true, message: `Error: ${error}`, severity: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const getStatusChip = (status: string) => {
        const statusConfig: Record<string, { color: any; icon: React.ReactElement }> = {
            running: { color: 'primary', icon: <HourglassEmptyIcon fontSize="small" /> },
            completed: { color: 'success', icon: <CheckCircleIcon fontSize="small" /> },
            failed: { color: 'error', icon: <ErrorIcon fontSize="small" /> },
            cancelled: { color: 'default', icon: <CancelIcon fontSize="small" /> },
            pending: { color: 'default', icon: <HourglassEmptyIcon fontSize="small" /> },
            queued: { color: 'info', icon: <HourglassEmptyIcon fontSize="small" /> },
            partial_success: { color: 'warning', icon: <ErrorIcon fontSize="small" /> }
        };

        const config = statusConfig[status] || { color: 'default', icon: <HourglassEmptyIcon fontSize="small" /> };
        return <Chip label={status.replace('_', ' ').toUpperCase()} color={config.color} size="small" icon={config.icon} />;
    };

    const formatDuration = (ms?: number) => {
        if (!ms) return 'N/A';
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) return `${hours}h ${minutes % 60}m`;
        if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
        return `${seconds}s`;
    };

    const formatDateTime = (dateStr?: string) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    };

    const jobColumns: GridColDef[] = [
        {
            field: 'name',
            headerName: 'Job Name',
            width: 280,
            renderCell: (params: any) => {
                const job = params.row;
                const shortId = job.job_id?.substring(0, 8) || '';
                return (
                    <Typography variant="body2" title={job.job_id}>
                        {job.name} <span style={{ color: '#888', fontSize: '0.85em' }}>({shortId})</span>
                    </Typography>
                );
            }
        },
        { field: 'job_type', headerName: 'Type', width: 150 },
        {
            field: 'status',
            headerName: 'Status',
            width: 150,
            renderCell: (params: any) => getStatusChip(params.value)
        },
        {
            field: 'progress',
            headerName: 'Progress',
            width: 200,
            renderCell: (params: any) => {
                const progress = params.row.progress;
                if (!progress) return 'N/A';
                return (
                    <Box sx={{ width: '100%' }}>
                        <LinearProgress variant="determinate" value={progress.percent_complete} />
                        <Typography variant="caption">{progress.percent_complete.toFixed(1)}%</Typography>
                    </Box>
                );
            }
        },
        {
            field: 'operations_summary',
            headerName: 'Operations',
            width: 150,
            renderCell: (params: any) => {
                const job = params.row;
                // Use progress.total_operations (from WebSocket) or operations.length (from API)
                const totalOps = job.progress?.total_operations || job.operations?.length || 0;
                const completedOps = job.progress?.completed_operations || job.success_count || 0;
                return (
                    <Typography variant="body2">
                        {completedOps} / {totalOps}
                        {job.failure_count > 0 && ` (${job.failure_count} failed)`}
                    </Typography>
                );
            }
        },
        {
            field: 'started_at',
            headerName: 'Started',
            width: 140,
            renderCell: (params: any) => formatDateTime(params.value)
        },
        {
            field: 'completed_at',
            headerName: 'Ended',
            width: 140,
            renderCell: (params: any) => formatDateTime(params.value)
        },
        {
            field: 'total_duration_ms',
            headerName: 'Duration',
            width: 90,
            renderCell: (params: any) => {
                const job = params.row;
                // For running jobs, calculate elapsed time from started_at
                if ((job.status === 'running' || job.status === 'queued') && job.started_at) {
                    const startedAt = new Date(job.started_at).getTime();
                    const elapsed = Date.now() - startedAt;
                    return formatDuration(elapsed);
                }
                return formatDuration(params.value);
            }
        },
        {
            field: 'actions',
            headerName: 'Actions',
            width: 200,
            renderCell: (params: any) => {
                const job = params.row;
                return (
                    <Box>
                        <IconButton size="small" onClick={() => handleViewDetails(job.job_id)} title="View Details">
                            <VisibilityIcon fontSize="small" />
                        </IconButton>
                        {(job.status === 'running' || job.status === 'queued') && (
                            <IconButton size="small" onClick={() => handleCancelJob(job.job_id)} title="Cancel">
                                <StopIcon fontSize="small" />
                            </IconButton>
                        )}
                        {(job.status === 'failed' || job.status === 'partial_success') && (
                            <IconButton size="small" onClick={() => handleRetryJob(job.job_id)} title="Retry Failed">
                                <RefreshIcon fontSize="small" />
                            </IconButton>
                        )}
                        {job.status !== 'running' && (
                            <IconButton size="small" onClick={() => handleDeleteJob(job.job_id)} title="Delete">
                                <DeleteIcon fontSize="small" />
                            </IconButton>
                        )}
                        {job.job_type === 'bulk_pipeline_execution' && ['completed', 'partial_success'].includes(job.status) && (
                            <>
                                <IconButton size="small" onClick={() => handleViewReport(job)} title="View Consolidated Report">
                                    <AssessmentIcon fontSize="small" color="primary" />
                                </IconButton>
                                <IconButton size="small" onClick={() => handleDownloadReport(job)} title="Download Report JSON">
                                    <DownloadIcon fontSize="small" color="action" />
                                </IconButton>
                            </>
                        )}
                        <IconButton size="small" onClick={() => handleExportResults(job)} title="Export Job Data">
                            <DownloadIcon fontSize="small" />
                        </IconButton>
                    </Box>
                );
            }
        }
    ];

    const activeJobs = jobs.filter(j => ['running', 'queued', 'pending'].includes(j.status));
    const completedJobs = jobs.filter(j => !['running', 'queued', 'pending'].includes(j.status));

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="h4">
                        Batch Operations
                    </Typography>
                    <Tooltip title={wsConnected ? 'Real-time updates active' : 'WebSocket disconnected - using polling fallback'}>
                        <Chip
                            icon={wsConnected ? <WifiIcon /> : <WifiOffIcon />}
                            label={wsConnected ? 'Live' : 'Polling'}
                            color={wsConnected ? 'success' : 'warning'}
                            size="small"
                            onClick={wsConnected ? undefined : wsReconnect}
                            sx={{ cursor: wsConnected ? 'default' : 'pointer' }}
                        />
                    </Tooltip>
                </Box>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => navigate('/batch-builder')}
                >
                    Create New Batch
                </Button>
            </Box>

            <Paper sx={{ width: '100%', mb: 2 }}>
                <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                    <Tab label="Bulk Pipeline Execution" />
                    <Tab label="Batch Data Generation" />
                    <Tab label={`Active Jobs (${activeJobs.length})`} />
                    <Tab label="Job History" />
                </Tabs>

                {/* Tab 0: Bulk Pipeline Execution */}
                {activeTab === 0 && (
                    <Box sx={{ p: 3 }}>
                        <Stack spacing={3}>
                            <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="subtitle2">
                                        Select Pipelines/Batches ({availablePipelines.filter(p =>
                                            viewFilter === 'all' ||
                                            (viewFilter === 'batches' && p.type === 'batch') ||
                                            (viewFilter === 'pipelines' && p.type === 'pipeline')
                                        ).length})
                                    </Typography>
                                    <ToggleButtonGroup
                                        value={viewFilter}
                                        exclusive
                                        onChange={(_, newFilter) => {
                                            if (newFilter !== null) {
                                                setViewFilter(newFilter);
                                            }
                                        }}
                                        size="small"
                                    >
                                        <ToggleButton value="all">
                                            <ViewListIcon fontSize="small" sx={{ mr: 0.5 }} />
                                            All
                                        </ToggleButton>
                                        <ToggleButton value="batches">
                                            <FolderIcon fontSize="small" sx={{ mr: 0.5 }} />
                                            Batches Only
                                        </ToggleButton>
                                        <ToggleButton value="pipelines">
                                            <DescriptionIcon fontSize="small" sx={{ mr: 0.5 }} />
                                            Pipelines Only
                                        </ToggleButton>
                                    </ToggleButtonGroup>
                                </Box>
                                {availablePipelines.length === 0 ? (
                                    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', my: 2 }}>
                                        No active pipelines found. Please generate pipelines from the Workload Analysis page first.
                                    </Typography>
                                ) : (
                                    <FormGroup>
                                        {availablePipelines
                                            .filter(pipeline =>
                                                viewFilter === 'all' ||
                                                (viewFilter === 'batches' && pipeline.type === 'batch') ||
                                                (viewFilter === 'pipelines' && pipeline.type === 'pipeline')
                                            )
                                            .map((pipeline) => (
                                                    <Box
                                                        key={pipeline.filename}
                                                        sx={{ display: 'flex', alignItems: 'center', mb: 1 }}
                                                    >
                                                        <Checkbox
                                                            checked={selectedPipelines.includes(pipeline.filename)}
                                                            onChange={() => handlePipelineToggle(pipeline.filename)}
                                                        />
                                                        <Box sx={{ flex: 1 }}>
                                                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                                                                <Box>
                                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                                        {pipeline.type === 'batch' ? (
                                                                            <FolderIcon fontSize="small" color="primary" />
                                                                        ) : (
                                                                            <DescriptionIcon fontSize="small" color="action" />
                                                                        )}
                                                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                                                            {pipeline.name || pipeline.filename || 'Unknown Pipeline'}
                                                                        </Typography>
                                                                        <Chip
                                                                            label={pipeline.type === 'batch' ? 'BATCH' : 'PIPELINE'}
                                                                            size="small"
                                                                            color={pipeline.type === 'batch' ? 'primary' : 'default'}
                                                                            sx={{ ml: 1, height: 20 }}
                                                                        />
                                                                    </Box>
                                                                    <Typography variant="caption" color="text.secondary">
                                                                        {pipeline.type === 'batch' ? (
                                                                            `${pipeline.pipeline_count || 0} pipelines • ${pipeline.batch_type || 'sequential'} execution`
                                                                        ) : (
                                                                            `Table: ${pipeline.table || 'Not specified'} • ${pipeline.validation_count || 0} validations`
                                                                        )}
                                                                    </Typography>
                                                                </Box>
                                                                <Box sx={{ display: 'flex', gap: 0.5 }}>
                                                                    {pipeline.type === 'batch' && (
                                                                        <IconButton
                                                                            size="small"
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                e.preventDefault();
                                                                                navigate(`/batch-builder?edit=${pipeline.filename.replace('.yaml', '')}`);
                                                                            }}
                                                                            title="Edit Batch"
                                                                        >
                                                                            <EditIcon fontSize="small" />
                                                                        </IconButton>
                                                                    )}
                                                                    <IconButton
                                                                        size="small"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            e.preventDefault();
                                                                            handleDeleteBatchOrPipeline(pipeline);
                                                                        }}
                                                                        title={`Delete ${pipeline.type === 'batch' ? 'Batch' : 'Pipeline'}`}
                                                                        color="error"
                                                                    >
                                                                        <DeleteIcon fontSize="small" />
                                                                    </IconButton>
                                                                </Box>
                                                            </Box>
                                                        </Box>
                                                    </Box>
                                                ))
                                        }
                                    </FormGroup>
                                )}
                            </Box>

                            <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={pipelineParallel}
                                            onChange={(e) => setPipelineParallel(e.target.checked)}
                                        />
                                    }
                                    label="Execute in Parallel"
                                />
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={pipelineStopOnError}
                                            onChange={(e) => setPipelineStopOnError(e.target.checked)}
                                        />
                                    }
                                    label="Stop on First Error"
                                />
                            </Box>

                            {pipelineParallel && (
                                <Box>
                                    <Typography gutterBottom>
                                        Max Parallel: {pipelineMaxParallel}
                                    </Typography>
                                    <Slider
                                        value={pipelineMaxParallel}
                                        onChange={(_, value) => setPipelineMaxParallel(value as number)}
                                        min={1}
                                        max={10}
                                        marks
                                        valueLabelDisplay="auto"
                                    />
                                </Box>
                            )}

                            <Button
                                variant="contained"
                                startIcon={<PlayArrowIcon />}
                                onClick={handleBulkPipelineExecution}
                                disabled={loading || selectedPipelines.length === 0}
                            >
                                Execute
                            </Button>
                        </Stack>
                    </Box>
                )}

                {/* Tab 1: Batch Data Generation */}
                {activeTab === 1 && (
                    <Box sx={{ p: 3 }}>
                        <Typography variant="h6" gutterBottom>
                            Generate Sample Data in Bulk
                        </Typography>

                        <Stack spacing={3}>
                            <TextField
                                label="Job Name"
                                value={dataGenJobName}
                                onChange={(e) => setDataGenJobName(e.target.value)}
                                fullWidth
                                placeholder="e.g., Generate Test Data"
                            />

                            <Box>
                                <Typography variant="subtitle2" gutterBottom>
                                    Select Schemas
                                </Typography>
                                <FormGroup>
                                    {['Retail', 'Finance', 'Healthcare'].map((schema) => (
                                        <FormControlLabel
                                            key={schema}
                                            control={
                                                <Checkbox
                                                    checked={dataGenSchemas.includes(schema)}
                                                    onChange={(e) => {
                                                        const isChecked = e.target.checked;
                                                        setDataGenSchemas(prev => {
                                                            if (isChecked) {
                                                                return [...prev, schema];
                                                            } else {
                                                                return prev.filter(s => s !== schema);
                                                            }
                                                        });
                                                    }}
                                                />
                                            }
                                            label={schema}
                                        />
                                    ))}
                                </FormGroup>
                            </Box>

                            <TextField
                                label="Row Count per Schema"
                                type="number"
                                value={dataGenRowCount}
                                onChange={(e) => setDataGenRowCount(parseInt(e.target.value) || 1000)}
                                fullWidth
                            />

                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={dataGenParallel}
                                        onChange={(e) => setDataGenParallel(e.target.checked)}
                                    />
                                }
                                label="Generate in Parallel"
                            />

                            <Button
                                variant="contained"
                                startIcon={<PlayArrowIcon />}
                                onClick={handleBulkDataGeneration}
                                disabled={loading || !dataGenJobName || dataGenSchemas.length === 0}
                            >
                                Generate Data
                            </Button>
                        </Stack>
                    </Box>
                )}

                {/* Tab 2: Active Jobs */}
                {activeTab === 2 && (
                    <Box sx={{ p: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                            <Typography variant="h6">
                                Active Jobs
                            </Typography>
                            <Button startIcon={<RefreshIcon />} onClick={fetchJobs}>
                                Refresh
                            </Button>
                        </Box>

                        <DataGrid
                            rows={activeJobs}
                            columns={jobColumns}
                            getRowId={(row: any) => row.job_id}
                            autoHeight
                            disableRowSelectionOnClick
                            initialState={{
                                pagination: { paginationModel: { pageSize: 10 } }
                            }}
                            pageSizeOptions={[10, 25, 50]}
                        />
                    </Box>
                )}

                {/* Tab 3: Job History */}
                {activeTab === 3 && (
                    <Box sx={{ p: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                            <Typography variant="h6">
                                Job History
                            </Typography>
                            <Button startIcon={<RefreshIcon />} onClick={fetchJobs}>
                                Refresh
                            </Button>
                        </Box>

                        <DataGrid
                            rows={completedJobs}
                            columns={jobColumns}
                            getRowId={(row: any) => row.job_id}
                            autoHeight
                            disableRowSelectionOnClick
                            initialState={{
                                pagination: { paginationModel: { pageSize: 25 } }
                            }}
                            pageSizeOptions={[25, 50, 100]}
                        />
                    </Box>
                )}
            </Paper>

            {/* Job Details Dialog */}
            <Dialog open={detailsOpen} onClose={() => setDetailsOpen(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Job Details
                    {selectedJob && getStatusChip(selectedJob.status)}
                </DialogTitle>
                <DialogContent>
                    {selectedJob && (
                        <Stack spacing={2}>
                            <Typography><strong>Job ID:</strong> {selectedJob.job_id}</Typography>
                            <Typography><strong>Name:</strong> {selectedJob.name}</Typography>
                            <Typography><strong>Type:</strong> {selectedJob.job_type}</Typography>
                            <Typography><strong>Description:</strong> {selectedJob.description || 'N/A'}</Typography>

                            {selectedJob.progress && (
                                <Box>
                                    <Typography variant="subtitle2" gutterBottom>Progress</Typography>
                                    <LinearProgress variant="determinate" value={selectedJob.progress.percent_complete} />
                                    <Grid container spacing={2} sx={{ mt: 1 }}>
                                        <Grid item xs={3}>
                                            <Typography variant="body2">Total: {selectedJob.progress.total_operations}</Typography>
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Typography variant="body2" color="success.main">
                                                Completed: {selectedJob.progress.completed_operations}
                                            </Typography>
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Typography variant="body2" color="error.main">
                                                Failed: {selectedJob.progress.failed_operations}
                                            </Typography>
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Typography variant="body2">
                                                Skipped: {selectedJob.progress.skipped_operations}
                                            </Typography>
                                        </Grid>
                                    </Grid>
                                </Box>
                            )}

                            <Divider />

                            <Typography variant="subtitle2">Operations ({selectedJob.operations?.length || 0})</Typography>
                            {selectedJob.operations?.map((op, idx) => {
                                // Extract user-friendly name from operation_id
                                const getFriendlyName = (operationId: string) => {
                                    // Remove common prefixes and suffixes
                                    let name = operationId
                                        .replace(/^pipeline_\d+_/, '')  // Remove "pipeline_0_"
                                        .replace(/\.yaml$/, '')          // Remove ".yaml"
                                        .replace(/_\d{8}_\d{6}/, '');    // Remove timestamps like "_20251218_185458"

                                    // Convert comparative_fact_sales -> FACT_SALES Comparative Validation
                                    if (name.startsWith('comparative_')) {
                                        name = name.replace('comparative_', '').replace(/_/g, '_').toUpperCase() + ' (Comparative)';
                                    }

                                    return name || operationId;
                                };

                                return (
                                <Card key={idx} variant="outlined">
                                    <CardContent>
                                        <Stack spacing={1}>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <Typography variant="body2"><strong>{getFriendlyName(op.operation_id)}</strong></Typography>
                                                {getStatusChip(op.status)}
                                            </Box>
                                            <Typography variant="caption">Type: {op.operation_type}</Typography>
                                            {op.duration_ms && (
                                                <Typography variant="caption">Duration: {formatDuration(op.duration_ms)}</Typography>
                                            )}
                                            {op.error && (
                                                <Alert severity="error" sx={{ mt: 1 }}>
                                                    {op.error}
                                                </Alert>
                                            )}
                                            {op.result && (
                                                <>
                                                    {/* Check if this is a batch execution result with nested pipelines */}
                                                    {op.result.batch_name && op.result.results && Array.isArray(op.result.results) ? (
                                                        <Box sx={{ mt: 2 }}>
                                                            <Typography variant="body2" gutterBottom>
                                                                <strong>Batch Summary:</strong>
                                                            </Typography>
                                                            <Typography variant="caption" component="div">
                                                                Total Pipelines: {op.result.total_pipelines || op.result.results.length}
                                                            </Typography>
                                                            <Typography variant="caption" component="div" color="success.main">
                                                                Successful: {op.result.successful || 0}
                                                            </Typography>
                                                            {op.result.failed > 0 && (
                                                                <Typography variant="caption" component="div" color="error.main">
                                                                    Failed: {op.result.failed}
                                                                </Typography>
                                                            )}

                                                            <Divider sx={{ my: 1 }} />

                                                            <Typography variant="body2" gutterBottom sx={{ mt: 2 }}>
                                                                <strong>Pipeline Results:</strong>
                                                            </Typography>
                                                            <Stack spacing={1}>
                                                                {op.result.results.map((pipelineResult: any, idx: number) => (
                                                                    <Card key={idx} variant="outlined" sx={{ bgcolor: 'background.default' }}>
                                                                        <CardContent sx={{ py: 1, px: 2, '&:last-child': { pb: 1 } }}>
                                                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                                <Box>
                                                                                    <Typography variant="caption" display="block">
                                                                                        {idx + 1}. {pipelineResult.pipeline_id || `Pipeline ${idx + 1}`}
                                                                                    </Typography>
                                                                                    {pipelineResult.error && (
                                                                                        <Typography variant="caption" color="error.main" display="block">
                                                                                            Error: {pipelineResult.error}
                                                                                        </Typography>
                                                                                    )}
                                                                                </Box>
                                                                                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                                                                    {pipelineResult.run_id && (
                                                                                        <Button
                                                                                            size="small"
                                                                                            variant="outlined"
                                                                                            onClick={() => {
                                                                                                window.location.href = `/pipeline-execution?run_id=${pipelineResult.run_id}`;
                                                                                            }}
                                                                                        >
                                                                                            View Results
                                                                                        </Button>
                                                                                    )}
                                                                                    {pipelineResult.status === 'failed' ? (
                                                                                        <Chip label="Failed" color="error" size="small" />
                                                                                    ) : (
                                                                                        <Chip label="Completed" color="success" size="small" />
                                                                                    )}
                                                                                </Box>
                                                                            </Box>
                                                                        </CardContent>
                                                                    </Card>
                                                                ))}
                                                            </Stack>
                                                        </Box>
                                                    ) : op.result.run_id ? (
                                                        /* Single pipeline execution result */
                                                        <Box sx={{ mt: 1 }}>
                                                            {/* Show results summary if available */}
                                                            {op.result.results_summary && (
                                                                <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                                                    <Chip
                                                                        size="small"
                                                                        label={`${op.result.results_summary.total_steps || 0} steps`}
                                                                        variant="outlined"
                                                                    />
                                                                    {op.result.results_summary.passed > 0 && (
                                                                        <Chip
                                                                            size="small"
                                                                            label={`${op.result.results_summary.passed} passed`}
                                                                            color="success"
                                                                        />
                                                                    )}
                                                                    {op.result.results_summary.failed > 0 && (
                                                                        <Chip
                                                                            size="small"
                                                                            label={`${op.result.results_summary.failed} failed`}
                                                                            color="error"
                                                                        />
                                                                    )}
                                                                </Box>
                                                            )}
                                                            <Button
                                                                size="small"
                                                                variant="outlined"
                                                                fullWidth
                                                                onClick={() => {
                                                                    window.location.href = `/pipeline-execution?run_id=${op.result.run_id}`;
                                                                }}
                                                            >
                                                                View Pipeline Results
                                                            </Button>
                                                        </Box>
                                                    ) : (
                                                        /* Fallback: show raw JSON for other result types */
                                                        <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                                                            {JSON.stringify(op.result, null, 2)}
                                                        </Typography>
                                                    )}
                                                </>
                                            )}
                                        </Stack>
                                    </CardContent>
                                </Card>
                                );
                            })}
                        </Stack>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDetailsOpen(false)}>Close</Button>
                </DialogActions>
            </Dialog>

            {/* Snackbar for notifications - positioned top-right */}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={() => setSnackbar({ ...snackbar, open: false })}
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
                <Alert
                    severity={snackbar.severity}
                    onClose={() => setSnackbar({ ...snackbar, open: false })}
                    sx={{ width: '100%', minWidth: 300 }}
                    variant="filled"
                >
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
};

export default BatchOperations;
