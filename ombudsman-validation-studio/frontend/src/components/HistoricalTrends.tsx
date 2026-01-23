import { useState, useEffect } from 'react';
import {
    Box, Card, CardContent, Typography, Grid, Chip, Alert, CircularProgress,
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    Button, IconButton, Tooltip
} from '@mui/material';
import {
    TrendingUp, TrendingDown, TrendingFlat, Speed, Assessment,
    CheckCircle, Error as ErrorIcon, Timeline, Bookmark, BookmarkBorder, Close
} from '@mui/icons-material';

interface HistoricalRun {
    run_id: string;
    pipeline_name: string;
    timestamp: string;
    metrics: {
        total_steps: number;
        passed_steps: number;
        failed_steps: number;
        success_rate: number;
        total_errors: number;
        blocker_issues: number;
        high_severity_issues: number;
        medium_severity_issues: number;
    };
}

interface Trend {
    trend: string;
    change_percent: number;
    direction: string;
}

interface Velocity {
    average_improvement_rate: number;
    velocity_indicator: string;
    estimated_runs_to_100_percent: number | null;
    current_success_rate: number;
}

interface Summary {
    total_runs: number;
    best_run: {
        run_id: string;
        success_rate: number;
        timestamp: string;
    };
    worst_run: {
        run_id: string;
        success_rate: number;
        timestamp: string;
    };
    average_success_rate: number;
    total_issues_resolved: number;
}

interface Baseline {
    run_id: string;
    pipeline_name: string;
    timestamp: string;
    set_at: string;
    metrics: {
        total_steps: number;
        passed_steps: number;
        failed_steps: number;
        success_rate: number;
        total_errors: number;
        blocker_issues: number;
        high_severity_issues: number;
    };
}

interface HistoricalTrendsProps {
    pipelineName?: string;
    limit?: number;
}

export default function HistoricalTrends({ pipelineName, limit = 10 }: HistoricalTrendsProps) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [runs, setRuns] = useState<HistoricalRun[]>([]);
    const [trends, setTrends] = useState<Record<string, Trend>>({});
    const [velocity, setVelocity] = useState<Velocity | null>(null);
    const [summary, setSummary] = useState<Summary | null>(null);
    const [baseline, setBaseline] = useState<Baseline | null>(null);

    useEffect(() => {
        fetchHistoricalData();
        fetchBaseline();
    }, [pipelineName, limit]);

    const fetchHistoricalData = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            if (pipelineName) params.append('pipeline_name', pipelineName);
            params.append('limit', limit.toString());

            const response = await fetch(`http://localhost:8000/results/history?${params.toString()}`);

            if (!response.ok) {
                throw new Error(`Failed to fetch historical data: ${response.statusText}`);
            }

            const data = await response.json();
            setRuns(data.runs || []);
            setTrends(data.trends || {});
            setVelocity(data.velocity || null);
            setSummary(data.summary || null);
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const fetchBaseline = async () => {
        try {
            const response = await fetch(__API_URL__ + '/results/baseline');
            if (!response.ok) {
                console.warn('Failed to fetch baseline');
                return;
            }
            const data = await response.json();
            setBaseline(data.baseline || null);
        } catch (err) {
            console.warn('Error fetching baseline:', err);
        }
    };

    const handleSetBaseline = async (runId: string) => {
        try {
            const response = await fetch(__API_URL__ + '/results/baseline/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run_id: runId })
            });

            if (!response.ok) {
                throw new Error('Failed to set baseline');
            }

            await fetchBaseline();
        } catch (err) {
            console.error('Error setting baseline:', err);
            alert('Failed to set baseline. Please try again.');
        }
    };

    const handleClearBaseline = async () => {
        try {
            const response = await fetch(__API_URL__ + '/results/baseline', {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to clear baseline');
            }

            setBaseline(null);
        } catch (err) {
            console.error('Error clearing baseline:', err);
            alert('Failed to clear baseline. Please try again.');
        }
    };

    const getTrendIcon = (direction: string) => {
        switch (direction) {
            case 'up':
                return <TrendingUp sx={{ color: '#4caf50' }} />;
            case 'down':
                return <TrendingDown sx={{ color: '#d32f2f' }} />;
            default:
                return <TrendingFlat sx={{ color: '#9e9e9e' }} />;
        }
    };

    const getTrendColor = (trend: string) => {
        switch (trend) {
            case 'improving':
                return '#4caf50';
            case 'degrading':
                return '#d32f2f';
            default:
                return '#9e9e9e';
        }
    };

    const getVelocityColor = (indicator: string) => {
        switch (indicator) {
            case 'accelerating':
                return '#4caf50';
            case 'steady':
                return '#2196f3';
            case 'slow':
                return '#ff9800';
            case 'degrading':
                return '#d32f2f';
            default:
                return '#9e9e9e';
        }
    };

    const formatDate = (timestamp: string) => {
        return new Date(timestamp).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                        <CircularProgress />
                    </Box>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Alert severity="error">{error}</Alert>
                </CardContent>
            </Card>
        );
    }

    if (!runs || runs.length === 0) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Historical Trends
                    </Typography>
                    <Alert severity="info">
                        No historical data available. Execute more pipeline runs to see trends.
                    </Alert>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card sx={{ mb: 3 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Timeline />
                    Historical Trends
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
                    Track validation performance over the last {runs.length} runs
                </Typography>

                {/* Baseline Indicator */}
                {baseline && (
                    <Alert
                        severity="info"
                        sx={{ mb: 3 }}
                        action={
                            <IconButton
                                aria-label="clear baseline"
                                color="inherit"
                                size="small"
                                onClick={handleClearBaseline}
                            >
                                <Close fontSize="inherit" />
                            </IconButton>
                        }
                    >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Bookmark sx={{ color: '#1976d2' }} />
                            <Typography variant="body2">
                                <strong>Baseline Set:</strong> {baseline.run_id} •
                                {formatDate(baseline.timestamp)} •
                                Success Rate: {baseline.metrics.success_rate.toFixed(1)}%
                            </Typography>
                        </Box>
                    </Alert>
                )}

                {/* Summary Statistics */}
                {summary && (
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ p: 2, backgroundColor: '#e3f2fd', borderRadius: 2, textAlign: 'center' }}>
                                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                                    {summary.total_runs}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Total Runs
                                </Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ p: 2, backgroundColor: '#e8f5e9', borderRadius: 2, textAlign: 'center' }}>
                                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#4caf50' }}>
                                    {summary.average_success_rate.toFixed(1)}%
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Average Success Rate
                                </Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 2, textAlign: 'center' }}>
                                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                                    {summary.total_issues_resolved}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Issues Resolved
                                </Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                            <Box sx={{ p: 2, backgroundColor: '#fce4ec', borderRadius: 2, textAlign: 'center' }}>
                                <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#c2185b' }}>
                                    {summary.best_run.success_rate.toFixed(1)}%
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Best Run
                                </Typography>
                            </Box>
                        </Grid>
                    </Grid>
                )}

                {/* Trend Indicators */}
                {trends && Object.keys(trends).length > 0 && (
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                        <Grid item xs={12} md={4}>
                            <Paper sx={{ p: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    {getTrendIcon(trends.success_rate?.direction)}
                                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                        Success Rate Trend
                                    </Typography>
                                </Box>
                                <Chip
                                    label={trends.success_rate?.trend || 'stable'}
                                    size="small"
                                    sx={{
                                        backgroundColor: getTrendColor(trends.success_rate?.trend),
                                        color: 'white',
                                        mb: 1
                                    }}
                                />
                                <Typography variant="h6" sx={{ color: getTrendColor(trends.success_rate?.trend) }}>
                                    {trends.success_rate?.change_percent > 0 ? '+' : ''}
                                    {trends.success_rate?.change_percent.toFixed(1)}%
                                </Typography>
                            </Paper>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Paper sx={{ p: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    {getTrendIcon(trends.total_errors?.direction === 'down' ? 'up' : trends.total_errors?.direction === 'up' ? 'down' : 'neutral')}
                                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                        Error Count Trend
                                    </Typography>
                                </Box>
                                <Chip
                                    label={trends.total_errors?.trend || 'stable'}
                                    size="small"
                                    sx={{
                                        backgroundColor: getTrendColor(trends.total_errors?.trend),
                                        color: 'white',
                                        mb: 1
                                    }}
                                />
                                <Typography variant="h6" sx={{ color: getTrendColor(trends.total_errors?.trend) }}>
                                    {trends.total_errors?.change_percent > 0 ? '+' : ''}
                                    {trends.total_errors?.change_percent.toFixed(1)}%
                                </Typography>
                            </Paper>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Paper sx={{ p: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    {getTrendIcon(trends.blocker_issues?.direction === 'down' ? 'up' : trends.blocker_issues?.direction === 'up' ? 'down' : 'neutral')}
                                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                        Blocker Issues Trend
                                    </Typography>
                                </Box>
                                <Chip
                                    label={trends.blocker_issues?.trend || 'stable'}
                                    size="small"
                                    sx={{
                                        backgroundColor: getTrendColor(trends.blocker_issues?.trend),
                                        color: 'white',
                                        mb: 1
                                    }}
                                />
                                <Typography variant="h6" sx={{ color: getTrendColor(trends.blocker_issues?.trend) }}>
                                    {trends.blocker_issues?.change_percent > 0 ? '+' : ''}
                                    {trends.blocker_issues?.change_percent.toFixed(1)}%
                                </Typography>
                            </Paper>
                        </Grid>
                    </Grid>
                )}

                {/* Velocity Indicator */}
                {velocity && (
                    <Paper sx={{ p: 2, mb: 3, backgroundColor: '#f5f5f5' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                            <Speed />
                            <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                Improvement Velocity
                            </Typography>
                        </Box>
                        <Grid container spacing={2}>
                            <Grid item xs={12} sm={6} md={3}>
                                <Typography variant="caption" color="text.secondary">
                                    Velocity Indicator
                                </Typography>
                                <Chip
                                    label={velocity.velocity_indicator}
                                    sx={{
                                        backgroundColor: getVelocityColor(velocity.velocity_indicator),
                                        color: 'white',
                                        textTransform: 'capitalize'
                                    }}
                                />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                                <Typography variant="caption" color="text.secondary">
                                    Average Improvement Rate
                                </Typography>
                                <Typography variant="h6">
                                    {velocity.average_improvement_rate > 0 ? '+' : ''}
                                    {velocity.average_improvement_rate.toFixed(2)}%
                                </Typography>
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                                <Typography variant="caption" color="text.secondary">
                                    Current Success Rate
                                </Typography>
                                <Typography variant="h6">
                                    {velocity.current_success_rate.toFixed(1)}%
                                </Typography>
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                                <Typography variant="caption" color="text.secondary">
                                    Estimated Runs to 100%
                                </Typography>
                                <Typography variant="h6">
                                    {velocity.estimated_runs_to_100_percent !== null
                                        ? velocity.estimated_runs_to_100_percent
                                        : 'N/A'}
                                </Typography>
                            </Grid>
                        </Grid>
                    </Paper>
                )}

                {/* Historical Runs Table */}
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mt: 2 }}>
                    Recent Runs
                </Typography>
                <TableContainer component={Paper}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>Timestamp</TableCell>
                                <TableCell align="center">Success Rate</TableCell>
                                <TableCell align="center">Passed</TableCell>
                                <TableCell align="center">Failed</TableCell>
                                <TableCell align="center">Errors</TableCell>
                                <TableCell align="center">Blockers</TableCell>
                                <TableCell align="center">Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {runs.slice().reverse().map((run, index) => (
                                <TableRow key={run.run_id} sx={{ '&:hover': { backgroundColor: '#f5f5f5' } }}>
                                    <TableCell>
                                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                            {formatDate(run.timestamp)}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Chip
                                            label={`${run.metrics.success_rate.toFixed(1)}%`}
                                            size="small"
                                            icon={run.metrics.success_rate >= 90 ? <CheckCircle /> : <ErrorIcon />}
                                            color={run.metrics.success_rate >= 90 ? 'success' : run.metrics.success_rate >= 70 ? 'warning' : 'error'}
                                        />
                                    </TableCell>
                                    <TableCell align="center">
                                        <Typography variant="body2" sx={{ color: '#4caf50' }}>
                                            {run.metrics.passed_steps}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Typography variant="body2" sx={{ color: '#d32f2f' }}>
                                            {run.metrics.failed_steps}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Typography variant="body2">
                                            {run.metrics.total_errors}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Typography variant="body2" sx={{ color: run.metrics.blocker_issues > 0 ? '#d32f2f' : 'text.primary' }}>
                                            {run.metrics.blocker_issues}
                                        </Typography>
                                    </TableCell>
                                    <TableCell align="center">
                                        <Tooltip title={baseline?.run_id === run.run_id ? "Current baseline" : "Set as baseline"}>
                                            <IconButton
                                                size="small"
                                                onClick={() => handleSetBaseline(run.run_id)}
                                                disabled={baseline?.run_id === run.run_id}
                                                sx={{
                                                    color: baseline?.run_id === run.run_id ? '#1976d2' : 'inherit'
                                                }}
                                            >
                                                {baseline?.run_id === run.run_id ? <Bookmark /> : <BookmarkBorder />}
                                            </IconButton>
                                        </Tooltip>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>

                {/* Help Text */}
                <Alert severity="info" sx={{ mt: 2 }}>
                    <Typography variant="body2">
                        <strong>Trend Indicators:</strong> Improving trends (green) indicate progress toward migration readiness.
                        Degrading trends (red) require attention. Velocity shows the rate of improvement per run.
                    </Typography>
                </Alert>
            </CardContent>
        </Card>
    );
}
