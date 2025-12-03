import { useState, useEffect } from 'react';
import {
    Box, Typography, Card, CardContent, Grid, CircularProgress,
    Alert, Chip, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, FormControl, InputLabel,
    Select, MenuItem, Button
} from '@mui/material';
import {
    TrendingUp, TrendingDown, TrendingFlat, Compare,
    CheckCircle, Error as ErrorIcon, RemoveCircle
} from '@mui/icons-material';

interface PipelineRun {
    run_id: string;
    timestamp: string;
    total_errors: number;
    total_steps: number;
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
    }>;
}

export default function RunComparison() {
    const [loading, setLoading] = useState(false);
    const [availableRuns, setAvailableRuns] = useState<PipelineRun[]>([]);
    const [selectedRun1, setSelectedRun1] = useState('');
    const [selectedRun2, setSelectedRun2] = useState('');
    const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchAvailableRuns();
    }, []);

    const fetchAvailableRuns = async () => {
        try {
            const response = await fetch('http://localhost:8000/results');
            const data = await response.json();

            const runs: PipelineRun[] = data.results.map((result: any) => ({
                run_id: result.run_id,
                timestamp: result.timestamp || result.execution_time,
                total_errors: 0, // Will be calculated
                total_steps: (result.steps || result.results || []).length
            }));

            // Sort by timestamp desc (most recent first)
            runs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

            setAvailableRuns(runs);

            // Auto-select the two most recent runs if available
            if (runs.length >= 2) {
                setSelectedRun1(runs[1].run_id);  // Older run
                setSelectedRun2(runs[0].run_id);  // Newer run
            }
        } catch (err) {
            console.error('Failed to fetch runs:', err);
        }
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
                `http://localhost:8000/results/compare/${selectedRun1}/vs/${selectedRun2}`
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

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Pipeline Run Comparison
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Compare two pipeline runs to analyze error trends and identify improvements or regressions
            </Typography>

            {/* Run Selection */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Grid container spacing={3} alignItems="center">
                        <Grid item xs={12} md={4}>
                            <FormControl fullWidth>
                                <InputLabel>Baseline Run (Older)</InputLabel>
                                <Select
                                    value={selectedRun1}
                                    label="Baseline Run (Older)"
                                    onChange={(e) => setSelectedRun1(e.target.value)}
                                >
                                    {availableRuns.map((run) => (
                                        <MenuItem key={run.run_id} value={run.run_id}>
                                            {run.run_id} - {new Date(run.timestamp).toLocaleString()}
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
                                >
                                    {availableRuns.map((run) => (
                                        <MenuItem key={run.run_id} value={run.run_id}>
                                            {run.run_id} - {new Date(run.timestamp).toLocaleString()}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        <Grid item xs={12} md={4}>
                            <Button
                                variant="contained"
                                fullWidth
                                onClick={handleCompare}
                                disabled={loading || !selectedRun1 || !selectedRun2}
                                startIcon={<Compare />}
                            >
                                {loading ? <CircularProgress size={24} /> : 'Compare Runs'}
                            </Button>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                </Alert>
            )}

            {comparisonData && (
                <>
                    {/* Summary Cards */}
                    <Grid container spacing={3} sx={{ mb: 4 }}>
                        <Grid item xs={12} md={3}>
                            <Card>
                                <CardContent>
                                    <Typography color="text.secondary" gutterBottom>
                                        Overall Trend
                                    </Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        {getTrendIcon(comparisonData.comparison_summary.overall_trend)}
                                        <Chip
                                            label={comparisonData.comparison_summary.overall_trend.toUpperCase()}
                                            color={getTrendColor(comparisonData.comparison_summary.overall_trend) as any}
                                        />
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>

                        <Grid item xs={12} md={3}>
                            <Card>
                                <CardContent>
                                    <Typography color="text.secondary" gutterBottom>
                                        Error Change
                                    </Typography>
                                    <Typography variant="h4" color={
                                        comparisonData.comparison_summary.total_error_delta < 0 ? 'success.main' :
                                        comparisonData.comparison_summary.total_error_delta > 0 ? 'error.main' : 'inherit'
                                    }>
                                        {comparisonData.comparison_summary.total_error_delta > 0 ? '+' : ''}
                                        {comparisonData.comparison_summary.total_error_delta}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        ({comparisonData.comparison_summary.error_delta_percentage > 0 ? '+' : ''}
                                        {comparisonData.comparison_summary.error_delta_percentage}%)
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>

                        <Grid item xs={12} md={3}>
                            <Card>
                                <CardContent>
                                    <Typography color="text.secondary" gutterBottom>
                                        Baseline: {comparisonData.run1.run_id}
                                    </Typography>
                                    <Typography variant="h5">
                                        {comparisonData.run1.total_errors} errors
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {comparisonData.run1.total_steps} steps
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>

                        <Grid item xs={12} md={3}>
                            <Card>
                                <CardContent>
                                    <Typography color="text.secondary" gutterBottom>
                                        Comparison: {comparisonData.run2.run_id}
                                    </Typography>
                                    <Typography variant="h5">
                                        {comparisonData.run2.total_errors} errors
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {comparisonData.run2.total_steps} steps
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    </Grid>

                    {/* Step Changes Summary */}
                    <Card sx={{ mb: 4 }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Step-Level Changes
                            </Typography>
                            <Grid container spacing={2}>
                                <Grid item xs={6} md={3}>
                                    <Chip
                                        icon={<CheckCircle />}
                                        label={`${comparisonData.comparison_summary.improved_steps} Improved`}
                                        color="success"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid item xs={6} md={3}>
                                    <Chip
                                        icon={<ErrorIcon />}
                                        label={`${comparisonData.comparison_summary.degraded_steps} Degraded`}
                                        color="error"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid item xs={6} md={3}>
                                    <Chip
                                        icon={<RemoveCircle />}
                                        label={`${comparisonData.comparison_summary.stable_steps} Stable`}
                                        color="info"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid item xs={6} md={3}>
                                    <Chip
                                        label={`${comparisonData.comparison_summary.new_steps} New / ${comparisonData.comparison_summary.removed_steps} Removed`}
                                        color="default"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                            </Grid>
                        </CardContent>
                    </Card>

                    {/* Detailed Step Comparison Table */}
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Detailed Step-by-Step Comparison
                            </Typography>
                            <TableContainer component={Paper} variant="outlined">
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell><strong>Step Name</strong></TableCell>
                                            <TableCell align="center"><strong>Baseline Errors</strong></TableCell>
                                            <TableCell align="center"><strong>Comparison Errors</strong></TableCell>
                                            <TableCell align="center"><strong>Change</strong></TableCell>
                                            <TableCell align="center"><strong>Trend</strong></TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {comparisonData.step_comparisons.map((step, index) => (
                                            <TableRow
                                                key={index}
                                                sx={{
                                                    bgcolor: step.trend === 'improved' ? 'success.light' :
                                                             step.trend === 'degraded' ? 'error.light' :
                                                             step.change === 'added' ? 'info.light' :
                                                             step.change === 'removed' ? 'warning.light' : 'inherit'
                                                }}
                                            >
                                                <TableCell>{step.step_name}</TableCell>
                                                <TableCell align="center">
                                                    {step.exists_in_run1 ? (step.run1_errors ?? '-') : 'N/A'}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.exists_in_run2 ? (step.run2_errors ?? '-') : 'N/A'}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.error_delta !== undefined ? (
                                                        <Typography
                                                            color={
                                                                step.error_delta < 0 ? 'success.main' :
                                                                step.error_delta > 0 ? 'error.main' : 'inherit'
                                                            }
                                                        >
                                                            {step.error_delta > 0 ? '+' : ''}{step.error_delta}
                                                        </Typography>
                                                    ) : step.change ? (
                                                        <Chip label={step.change} size="small" />
                                                    ) : '-'}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {step.trend && (
                                                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                                            {getTrendIcon(step.trend)}
                                                            <Chip
                                                                label={step.trend}
                                                                size="small"
                                                                color={getTrendColor(step.trend) as any}
                                                                sx={{ ml: 1 }}
                                                            />
                                                        </Box>
                                                    )}
                                                    {step.change && (
                                                        <Chip
                                                            label={step.change === 'added' ? 'New Step' : step.change === 'removed' ? 'Removed Step' : step.change}
                                                            size="small"
                                                            color={step.change === 'added' ? 'info' : 'warning'}
                                                        />
                                                    )}
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
        </Box>
    );
}
