import { useState, useEffect } from 'react';
import {
    Box, Typography, Card, CardContent, Grid, CircularProgress,
    Alert, Chip, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, FormControl, InputLabel,
    Select, MenuItem, Button, ToggleButtonGroup, ToggleButton
} from '@mui/material';
import {
    TrendingUp, TrendingDown, TrendingFlat, Compare,
    CheckCircle, Error as ErrorIcon, RemoveCircle,
    FilterList, BatchPrediction, Timeline,
    PictureAsPdf, TableChart, Download
} from '@mui/icons-material';
import ExecutiveSummary from '../components/ExecutiveSummary';
import TrendChart from '../components/TrendChart';
import RootCauseGroups from '../components/RootCauseGroups';
import RecommendationsList from '../components/RecommendationsList';
import FinancialImpact from '../components/FinancialImpact';
import StepDetailModal from '../components/StepDetailModal';
import HistoricalTrends from '../components/HistoricalTrends';

interface PipelineRun {
    run_id: string;
    timestamp: string;
    total_errors: number;
    total_steps: number;
    pipeline_name?: string;
    batch_id?: string;
}

interface BatchInfo {
    batch_name: string;
    timestamp: string;
    pipeline_count: number;
}

interface ComparisonData {
    run1: {
        run_id: string;
        timestamp: string;
        total_errors: number;
        total_steps: number;
    };
    run2: {
        run_id: string;
        timestamp: string;
        total_errors: number;
        total_steps: number;
    };
    comparison_summary: {
        overall_trend: string;
        total_error_delta: number;
        error_delta_percentage: number;
        improved_steps: number;
        degraded_steps: number;
        stable_steps: number;
        new_steps: number;
        removed_steps: number;
    };
    executive_summary?: {
        readiness_score: number;
        overall_status: string;
        total_validations: number;
        passed_validations: number;
        failed_validations: number;
        warnings: number;
        critical_issues: number;
        severity_breakdown: {
            BLOCKER: number;
            HIGH: number;
            MEDIUM: number;
            LOW: number;
        };
    };
    trend_analysis?: {
        error_trend: Array<{
            timestamp: string;
            total_errors: number;
        }>;
        velocity: {
            per_day: number;
            per_week: number;
        };
        projected_zero_date: string | null;
        regression_detected: boolean;
    };
    root_cause_groups?: Array<{
        category: string;
        title: string;
        description: string;
        affected_steps: string[];
        total_affected: number;
        total_errors: number;
        severity: string;
        recommended_action: string;
    }>;
    recommendations?: Array<{
        priority: string;
        title: string;
        description: string;
        action_items: string[];
        commands: string[];
        effort: string;
        impact: string;
        affected_count: number;
        category: string;
    }>;
    financial_impact?: {
        table_criticality: Array<{
            table_name: string;
            criticality_score: number;
            criticality_level: string;
            error_count: number;
            status: string;
            severity: string;
        }>;
        financial_impact: {
            total_estimated_cost: number;
            cost_breakdown: Array<{
                table_name: string;
                error_count: number;
                criticality_score: number;
                unit_cost: number;
                total_cost: number;
            }>;
            average_cost_per_error: number;
            high_cost_tables: number;
        };
        risk_assessment: {
            overall_risk: string;
            risk_score: number;
            risk_factors: Array<{
                factor: string;
                impact: string;
                description: string;
            }>;
            blocker_issues: number;
            high_severity_issues: number;
            critical_tables_at_risk: number;
            migration_readiness: string;
        };
    };
    step_comparisons: Array<{
        step_name: string;
        exists_in_run1: boolean;
        exists_in_run2: boolean;
        run1_status?: string;
        run2_status?: string;
        run1_errors?: number;
        run2_errors?: number;
        error_delta?: number;
        status_changed?: boolean;
        trend?: string;
        change?: string;
        severity?: string;
    }>;
}

export default function RunComparison() {
    const [loading, setLoading] = useState(false);
    const [allIndividualRuns, setAllIndividualRuns] = useState<PipelineRun[]>([]);
    const [allBatchRuns, setAllBatchRuns] = useState<PipelineRun[]>([]);
    const [availableBatches, setAvailableBatches] = useState<BatchInfo[]>([]);
    const [availablePipelines, setAvailablePipelines] = useState<string[]>([]);
    const [filterType, setFilterType] = useState<'batch' | 'pipeline'>('batch');
    const [selectedBatch, setSelectedBatch] = useState('');
    const [selectedPipeline, setSelectedPipeline] = useState('');
    const [baselineRuns, setBaselineRuns] = useState<PipelineRun[]>([]);
    const [comparisonRuns, setComparisonRuns] = useState<PipelineRun[]>([]);
    const [selectedRun1, setSelectedRun1] = useState('');
    const [selectedRun2, setSelectedRun2] = useState('');
    const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Step detail modal state
    const [modalOpen, setModalOpen] = useState(false);
    const [selectedModalRunId, setSelectedModalRunId] = useState('');
    const [selectedStepName, setSelectedStepName] = useState('');
    const [exportingFormat, setExportingFormat] = useState<string | null>(null);

    useEffect(() => {
        fetchAllData();
    }, []);

    useEffect(() => {
        applyFilter();
    }, [filterType, selectedBatch, selectedPipeline, allIndividualRuns, allBatchRuns]);

    useEffect(() => {
        applyBaselineSelection();
    }, [selectedRun1, baselineRuns]);

    // Helper function to extract base pipeline name (remove timestamp suffix)
    const extractBasePipelineName = (fullName: string): string => {
        // Remove timestamp pattern: _YYYYMMDD_HHMMSS
        return fullName.replace(/_\d{8}_\d{6}$/, '');
    };

    const fetchAllData = async () => {
        try {
            // Fetch active project first to filter runs by project
            let activeProjectId: string | null = null;
            try {
                const projectResponse = await fetch(__API_URL__ + '/projects/active');
                const projectData = await projectResponse.json();
                if (projectData.status === 'success' && projectData.active_project) {
                    activeProjectId = projectData.active_project.project_id;
                    console.log('[RunComparison] Active project:', activeProjectId);
                }
            } catch (err) {
                console.warn('[RunComparison] Could not fetch active project:', err);
            }

            // Fetch pipeline runs
            const runsResponse = await fetch(__API_URL__ + '/results');
            const runsData = await runsResponse.json();

            // Fetch batch jobs
            const batchResponse = await fetch(__API_URL__ + '/batch/jobs');
            const batchData = await batchResponse.json();

            // Process pipeline runs
            const individualRuns: PipelineRun[] = [];
            const batchRuns: PipelineRun[] = [];
            const pipelineNames: Set<string> = new Set();
            const batchMap: Map<string, { batch_name: string }> = new Map();

            // Process all results to separate batch runs and individual runs
            runsData.results.forEach((result: any) => {
                const isUnnamed = result.pipeline_name === 'unnamed_pipeline';
                const isBatchRun = result.run_id?.startsWith('batch_');

                // Filter by active project if available
                if (activeProjectId) {
                    // Check if this run belongs to the active project
                    // Batch runs have batch_job_name starting with project_id
                    // Individual runs have pipeline_name starting with project_id
                    const batch_job_name = result.batch_job_name || result.batch_job_id;
                    const pipelineName = result.pipeline_name;

                    const belongsToProject =
                        (isBatchRun && batch_job_name && batch_job_name.startsWith(activeProjectId)) ||
                        (!isBatchRun && pipelineName && pipelineName.startsWith(activeProjectId));

                    if (!belongsToProject) {
                        console.log(`[RunComparison] ⚠️ FILTERED OUT: run_id=${result.run_id}, batch_name=${batch_job_name}, pipeline=${pipelineName} (active project: ${activeProjectId})`);
                        return; // Skip this run
                    } else {
                        console.log(`[RunComparison] ✓ INCLUDED: run_id=${result.run_id}, batch_name=${batch_job_name}, pipeline=${pipelineName} (active project: ${activeProjectId})`);
                    }
                }

                if (isBatchRun) {
                    // This is a batch consolidated run
                    const batch_job_name = result.batch_job_name || result.batch_job_id;

                    // Add to batch runs list
                    const run: PipelineRun = {
                        run_id: result.run_id,
                        timestamp: result.started_at || result.timestamp || result.execution_time,
                        total_errors: 0,
                        total_steps: (result.results || []).length,
                        pipeline_name: batch_job_name,
                        batch_id: batch_job_name
                    };
                    batchRuns.push(run);

                    // Track unique batch names
                    if (!batchMap.has(batch_job_name)) {
                        batchMap.set(batch_job_name, {
                            batch_name: batch_job_name
                        });
                    }
                } else if (!isUnnamed) {
                    // This is an individual pipeline run
                    const run: PipelineRun = {
                        run_id: result.run_id,
                        timestamp: result.started_at || result.timestamp || result.execution_time,
                        total_errors: 0,
                        total_steps: (result.steps || result.results || []).length,
                        pipeline_name: result.pipeline_name,
                        batch_id: undefined
                    };
                    individualRuns.push(run);

                    // Extract base pipeline name for dropdown (without timestamp)
                    if (result.pipeline_name) {
                        const baseName = extractBasePipelineName(result.pipeline_name);
                        pipelineNames.add(baseName);
                    }
                }
            });

            // Sort runs by timestamp (most recent first)
            individualRuns.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
            batchRuns.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

            // Convert batchMap to array for the batch dropdown
            const batchArray: BatchInfo[] = Array.from(batchMap.values()).map(batch => ({
                batch_name: batch.batch_name,
                timestamp: new Date().toISOString(), // We can enhance this later
                pipeline_count: batchRuns.filter(r => r.batch_id === batch.batch_name).length
            }));

            setAllIndividualRuns(individualRuns);
            setAllBatchRuns(batchRuns);
            setAvailableBatches(batchArray);
            setAvailablePipelines(Array.from(pipelineNames).sort());

        } catch (err) {
            console.error('Failed to fetch data:', err);
        }
    };

    const applyFilter = () => {
        let filtered: PipelineRun[] = [];

        if (filterType === 'batch') {
            // Show BATCH CONSOLIDATED RUNS from the selected batch
            if (selectedBatch) {
                filtered = allBatchRuns.filter(run => run.batch_id === selectedBatch);
            } else {
                filtered = [];
            }
        } else if (filterType === 'pipeline') {
            // Show INDIVIDUAL PIPELINE RUNS matching the selected pipeline name
            if (selectedPipeline) {
                filtered = allIndividualRuns.filter(run => {
                    if (!run.pipeline_name) {
                        return false;
                    }
                    const baseName = extractBasePipelineName(run.pipeline_name);
                    return baseName === selectedPipeline;
                });
            } else {
                filtered = [];
            }
        }

        // Sort filtered runs by timestamp DESC (most recent first)
        filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        setBaselineRuns(filtered);
        setSelectedRun1('');
        setSelectedRun2('');
        setComparisonRuns([]);
    };

    const applyBaselineSelection = () => {
        if (!selectedRun1 || baselineRuns.length === 0) {
            setComparisonRuns([]);
            setSelectedRun2('');
            return;
        }

        // Find the selected baseline run
        const baselineRun = baselineRuns.find(r => r.run_id === selectedRun1);
        if (!baselineRun) {
            setComparisonRuns([]);
            setSelectedRun2('');
            return;
        }

        const baselineTimestamp = new Date(baselineRun.timestamp).getTime();
        const baselinePipeline = baselineRun.pipeline_name;

        // Filter runs: same pipeline AND timestamp > baseline timestamp AND exclude selected run
        const filtered = baselineRuns.filter(run => {
            if (run.run_id === selectedRun1) return false;
            if (run.pipeline_name !== baselinePipeline) return false;
            const runTimestamp = new Date(run.timestamp).getTime();
            return runTimestamp > baselineTimestamp;
        });

        setComparisonRuns(filtered);
        setSelectedRun2('');
    };

    const handleCompare = async () => {
        if (!selectedRun1 || !selectedRun2) {
            setError('Please select two runs to compare');
            return;
        }

        if (selectedRun1 === selectedRun2) {
            setError('Please select two different runs');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const response = await fetch(
                `${__API_URL__}/results/compare/${selectedRun1}/vs/${selectedRun2}`
            );
            const data = await response.json();

            if (data.status === 'success') {
                setComparisonData(data);
            } else {
                setError(data.detail || 'Comparison failed');
            }
        } catch (err) {
            setError('Failed to compare runs: ' + (err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format: 'pdf' | 'excel' | 'json') => {
        if (!selectedRun2) return;

        try {
            setExportingFormat(format);

            let dataToExport = comparisonData;

            // If we have both runs selected but no comparison data yet, fetch it first
            if (selectedRun1 && selectedRun2 && !comparisonData) {
                const comparisonResponse = await fetch(
                    `${__API_URL__}/results/compare/${selectedRun1}/vs/${selectedRun2}`
                );
                const comparisonJson = await comparisonResponse.json();
                if (comparisonJson.status === 'success') {
                    dataToExport = comparisonJson;
                }
            }

            let endpoint: string;
            let requestOptions: RequestInit;

            // If we have comparison data with analysis, export that instead
            if (dataToExport && dataToExport.executive_summary) {
                // Export the full comparison data with analysis
                endpoint = `${__API_URL__}/results/export/${format}/comparison`;
                requestOptions = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(dataToExport)
                };
            } else {
                // Fallback to basic export (GET request)
                const isBatch = selectedRun2.startsWith('batch_');
                endpoint = isBatch
                    ? `${__API_URL__}/results/export/${format}/batch/${selectedRun2}`
                    : `${__API_URL__}/results/export/${format}/${selectedRun2}`;
                requestOptions = {
                    method: 'GET'
                };
            }

            const response = await fetch(endpoint, requestOptions);

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Get the blob from the response
            const blob = await response.blob();

            // Create a download link
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            // Set the filename based on format and type
            const extensions = { pdf: 'pdf', excel: 'xlsx', json: 'json' };
            const prefix = dataToExport?.executive_summary ? 'migration_readiness_report' :
                          (selectedRun2.startsWith('batch_') ? 'batch_validation_results' : 'validation_results');
            link.download = `${prefix}_${selectedRun2}.${extensions[format]}`;

            // Trigger download
            document.body.appendChild(link);
            link.click();

            // Cleanup
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (err: any) {
            setError(`Export failed: ${err.message}`);
        } finally {
            setExportingFormat(null);
        }
    };

    const getTrendIcon = (trend: string) => {
        switch (trend) {
            case 'improved':
                return <TrendingDown sx={{ color: 'success.main' }} />;
            case 'degraded':
                return <TrendingUp sx={{ color: 'error.main' }} />;
            default:
                return <TrendingFlat sx={{ color: 'info.main' }} />;
        }
    };

    const getTrendColor = (trend: string) => {
        switch (trend) {
            case 'improved':
            case 'improving':
                return 'success';
            case 'degraded':
            case 'degrading':
                return 'error';
            default:
                return 'info';
        }
    };

    const formatTimestamp = (timestamp: string): string => {
        if (!timestamp) return 'No date';
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return 'Invalid date';
            return date.toLocaleString();
        } catch (e) {
            return 'Invalid date';
        }
    };

    const handleStepClick = (runId: string, stepName: string) => {
        setSelectedModalRunId(runId);
        setSelectedStepName(stepName);
        setModalOpen(true);
    };

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Pipeline Run Comparison
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Compare two pipeline runs to analyze error trends and identify improvements or regressions
            </Typography>

            {/* Filter Selection */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <FilterList /> Filter Runs
                    </Typography>
                    <Grid container spacing={3} alignItems="center">
                        <Grid item xs={12} md={4}>
                            <ToggleButtonGroup
                                value={filterType}
                                exclusive
                                onChange={(e, newValue) => {
                                    if (newValue !== null) {
                                        setFilterType(newValue);
                                        setSelectedBatch('');
                                        setSelectedPipeline('');
                                    }
                                }}
                                fullWidth
                                size="small"
                            >
                                <ToggleButton value="batch">
                                    <BatchPrediction sx={{ mr: 1 }} /> By Batch
                                </ToggleButton>
                                <ToggleButton value="pipeline">
                                    <Timeline sx={{ mr: 1 }} /> By Pipeline
                                </ToggleButton>
                            </ToggleButtonGroup>
                        </Grid>

                        {filterType === 'batch' && (
                            <Grid item xs={12} md={4}>
                                <FormControl fullWidth>
                                    <InputLabel>Select Batch</InputLabel>
                                    <Select
                                        value={selectedBatch}
                                        label="Select Batch"
                                        onChange={(e) => setSelectedBatch(e.target.value)}
                                    >
                                        {availableBatches.map((batch) => (
                                            <MenuItem key={batch.batch_name} value={batch.batch_name}>
                                                {batch.batch_name}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )}

                        {filterType === 'pipeline' && (
                            <Grid item xs={12} md={4}>
                                <FormControl fullWidth>
                                    <InputLabel>Select Pipeline</InputLabel>
                                    <Select
                                        value={selectedPipeline}
                                        label="Select Pipeline"
                                        onChange={(e) => setSelectedPipeline(e.target.value)}
                                    >
                                        {availablePipelines.map((pipeline) => (
                                            <MenuItem key={pipeline} value={pipeline}>
                                                {pipeline}
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Grid>
                        )}

                        <Grid item xs={12} md={4}>
                            <Chip
                                label={`${baselineRuns.length} runs available`}
                                color="primary"
                                variant="outlined"
                            />
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Run Selection */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Select Runs to Compare
                    </Typography>
                    <Grid container spacing={3} alignItems="center">
                        <Grid item xs={12} md={4}>
                            <FormControl fullWidth>
                                <InputLabel>Baseline Run (Older)</InputLabel>
                                <Select
                                    value={selectedRun1}
                                    label="Baseline Run (Older)"
                                    onChange={(e) => setSelectedRun1(e.target.value)}
                                    disabled={baselineRuns.length < 1}
                                >
                                    {baselineRuns.map((run) => (
                                        <MenuItem key={run.run_id} value={run.run_id}>
                                            {run.pipeline_name || run.run_id} - {formatTimestamp(run.timestamp)}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <FormControl fullWidth>
                                <InputLabel>Comparison Run (Newer)</InputLabel>
                                <Select
                                    value={selectedRun2}
                                    label="Comparison Run (Newer)"
                                    onChange={(e) => setSelectedRun2(e.target.value)}
                                    disabled={comparisonRuns.length < 1}
                                >
                                    {comparisonRuns.map((run) => (
                                        <MenuItem key={run.run_id} value={run.run_id}>
                                            {run.pipeline_name || run.run_id} - {formatTimestamp(run.timestamp)}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Button
                                variant="contained"
                                startIcon={<Compare />}
                                onClick={handleCompare}
                                disabled={!selectedRun1 || !selectedRun2 || loading}
                                fullWidth
                                size="large"
                            >
                                Compare Runs
                            </Button>
                        </Grid>

                        {/* Export Buttons */}
                        {selectedRun2 && (
                            <Grid item xs={12}>
                                <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', mt: 2 }}>
                                    <Button
                                        variant="outlined"
                                        startIcon={exportingFormat === 'pdf' ? <CircularProgress size={16} /> : <PictureAsPdf />}
                                        onClick={() => handleExport('pdf')}
                                        disabled={!!exportingFormat}
                                        color="error"
                                        size="small"
                                    >
                                        Export PDF
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        startIcon={exportingFormat === 'excel' ? <CircularProgress size={16} /> : <TableChart />}
                                        onClick={() => handleExport('excel')}
                                        disabled={!!exportingFormat}
                                        color="success"
                                        size="small"
                                    >
                                        Export Excel
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        startIcon={exportingFormat === 'json' ? <CircularProgress size={16} /> : <Download />}
                                        onClick={() => handleExport('json')}
                                        disabled={!!exportingFormat}
                                        color="primary"
                                        size="small"
                                    >
                                        Export JSON
                                    </Button>
                                </Box>
                            </Grid>
                        )}
                    </Grid>
                </CardContent>
            </Card>

            {/* Error Display */}
            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {/* Loading State */}
            {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                    <CircularProgress />
                </Box>
            )}

            {/* Comparison Results */}
            {comparisonData && !loading && (
                <>
                    {/* Executive Summary Dashboard */}
                    {comparisonData.executive_summary && (
                        <ExecutiveSummary data={comparisonData.executive_summary} />
                    )}

                    {/* Trend Analysis Chart */}
                    {comparisonData.trend_analysis && (
                        <TrendChart data={comparisonData.trend_analysis} />
                    )}

                    {/* Root Cause Analysis */}
                    {comparisonData.root_cause_groups && (
                        <RootCauseGroups
                            groups={comparisonData.root_cause_groups}
                            runId={selectedRun2}
                            onStepClick={handleStepClick}
                        />
                    )}

                    {/* Actionable Recommendations */}
                    {comparisonData.recommendations && (
                        <RecommendationsList
                            recommendations={comparisonData.recommendations}
                            runId={selectedRun2}
                            onStepClick={handleStepClick}
                        />
                    )}

                    {/* Financial Impact & Risk Assessment */}
                    {comparisonData.financial_impact && (
                        <FinancialImpact data={comparisonData.financial_impact} />
                    )}

                    {/* Historical Trends */}
                    <HistoricalTrends limit={10} />

                    {/* Summary Card */}
                    <Card sx={{ mb: 3 }}>
                        <CardContent>
                            <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {getTrendIcon(comparisonData.comparison_summary.overall_trend)}
                                Comparison Summary
                            </Typography>

                            <Grid container spacing={3} sx={{ mt: 1 }}>
                                <Grid item xs={12} md={6}>
                                    <Typography variant="subtitle2" color="text.secondary">Baseline Run</Typography>
                                    <Typography variant="body2">
                                        {comparisonData.run1.run_id}
                                    </Typography>
                                    <Typography variant="caption">
                                        {formatTimestamp(comparisonData.run1.timestamp)}
                                    </Typography>
                                </Grid>

                                <Grid item xs={12} md={6}>
                                    <Typography variant="subtitle2" color="text.secondary">Comparison Run</Typography>
                                    <Typography variant="body2">
                                        {comparisonData.run2.run_id}
                                    </Typography>
                                    <Typography variant="caption">
                                        {formatTimestamp(comparisonData.run2.timestamp)}
                                    </Typography>
                                </Grid>

                                <Grid item xs={12} sm={6} md={3}>
                                    <Chip
                                        label={`Overall: ${comparisonData.comparison_summary.overall_trend}`}
                                        color={getTrendColor(comparisonData.comparison_summary.overall_trend) as any}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>

                                <Grid item xs={12} sm={6} md={3}>
                                    <Chip
                                        icon={<TrendingDown />}
                                        label={`Improved: ${comparisonData.comparison_summary.improved_steps}`}
                                        color="success"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>

                                <Grid item xs={12} sm={6} md={3}>
                                    <Chip
                                        icon={<TrendingUp />}
                                        label={`Degraded: ${comparisonData.comparison_summary.degraded_steps}`}
                                        color="error"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>

                                <Grid item xs={12} sm={6} md={3}>
                                    <Chip
                                        icon={<TrendingFlat />}
                                        label={`Stable: ${comparisonData.comparison_summary.stable_steps}`}
                                        color="info"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>

                                <Grid item xs={12}>
                                    <Typography variant="body2">
                                        <strong>Error Delta:</strong> {comparisonData.comparison_summary.total_error_delta}{' '}
                                        ({comparisonData.comparison_summary.error_delta_percentage.toFixed(2)}%)
                                    </Typography>
                                </Grid>
                            </Grid>
                        </CardContent>
                    </Card>

                    {/* Step Comparison Table */}
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Step-by-Step Comparison
                            </Typography>

                            <TableContainer component={Paper}>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell><strong>Step Name</strong></TableCell>
                                            <TableCell align="center"><strong>Trend</strong></TableCell>
                                            <TableCell align="center"><strong>Baseline Status</strong></TableCell>
                                            <TableCell align="center"><strong>Baseline Errors</strong></TableCell>
                                            <TableCell align="center"><strong>Current Status</strong></TableCell>
                                            <TableCell align="center"><strong>Current Errors</strong></TableCell>
                                            <TableCell align="center"><strong>Change</strong></TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {comparisonData.step_comparisons.map((step, index) => (
                                            <TableRow key={index}>
                                                <TableCell>
                                                    <Typography
                                                        component="span"
                                                        sx={{
                                                            cursor: 'pointer',
                                                            color: 'primary.main',
                                                            textDecoration: 'underline',
                                                            '&:hover': {
                                                                color: 'primary.dark',
                                                            }
                                                        }}
                                                        onClick={() => handleStepClick(selectedRun2, step.step_name)}
                                                    >
                                                        {step.step_name}
                                                    </Typography>
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.trend && getTrendIcon(step.trend)}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.exists_in_run1 ? (
                                                        step.run1_status === 'success' ? (
                                                            <CheckCircle color="success" />
                                                        ) : (
                                                            <ErrorIcon color="error" />
                                                        )
                                                    ) : (
                                                        <RemoveCircle color="disabled" />
                                                    )}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.run1_errors !== undefined ? step.run1_errors : '-'}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.exists_in_run2 ? (
                                                        step.run2_status === 'success' ? (
                                                            <CheckCircle color="success" />
                                                        ) : (
                                                            <ErrorIcon color="error" />
                                                        )
                                                    ) : (
                                                        <RemoveCircle color="disabled" />
                                                    )}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.run2_errors !== undefined ? step.run2_errors : '-'}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.change || '-'}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </>
            )}

            {/* Step Detail Modal */}
            <StepDetailModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                runId={selectedModalRunId}
                stepName={selectedStepName}
            />
        </Box>
    );
}
