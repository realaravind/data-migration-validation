import { useState, useEffect } from 'react';
import {
    Box, Typography, Card, CardContent, Grid, CircularProgress,
    Alert, Chip, Table, TableBody, TableCell, TableContainer,
    TableHead, TableRow, Paper, LinearProgress
} from '@mui/material';
import {
    TrendingUp, TrendingDown, TrendingFlat,
    CheckCircle, Warning, Error as ErrorIcon
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ProjectSummaryData {
    summary: {
        total_runs: number;
        total_errors_all_time: number;
        average_errors_per_run: number;
        health_score: number;
        trend_direction: string;
        recent_avg_errors: number;
        older_avg_errors: number;
    };
    error_trend: Array<{
        run_id: string;
        timestamp: string;
        total_errors: number;
        total_steps: number;
        failed_steps: number;
    }>;
    problematic_steps: Array<{
        step_name: string;
        total_errors: number;
        failure_count: number;
        total_runs: number;
        failure_rate: number;
    }>;
    recommendations: string[];
    latest_run: any;
    oldest_run: any;
}

export default function ProjectSummary() {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<ProjectSummaryData | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchProjectSummary();
    }, []);

    const fetchProjectSummary = async () => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:8000/results/project-summary');
            const result = await response.json();

            if (result.status === 'no_data') {
                setError('No pipeline runs found. Execute some pipelines to see project analytics.');
            } else if (result.status === 'success') {
                setData(result);
            } else {
                setError('Failed to load project summary');
            }
        } catch (err) {
            setError('Failed to fetch project summary: ' + (err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const getTrendIcon = (trend: string) => {
        switch (trend) {
            case 'improving':
                return <TrendingDown sx={{ color: 'success.main' }} />;
            case 'degrading':
                return <TrendingUp sx={{ color: 'error.main' }} />;
            default:
                return <TrendingFlat sx={{ color: 'info.main' }} />;
        }
    };

    const getTrendColor = (trend: string) => {
        switch (trend) {
            case 'improving':
                return 'success';
            case 'degrading':
                return 'error';
            default:
                return 'info';
        }
    };

    const getHealthColor = (score: number) => {
        if (score >= 80) return 'success';
        if (score >= 60) return 'warning';
        return 'error';
    };

    const getRecommendationSeverity = (rec: string): 'error' | 'warning' | 'info' | 'success' => {
        if (rec.startsWith('CRITICAL')) return 'error';
        if (rec.startsWith('ALERT') || rec.startsWith('WARNING') || rec.startsWith('PRIORITY')) return 'warning';
        if (rec.startsWith('POSITIVE') || rec.startsWith('GOOD')) return 'success';
        return 'info';
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box>
                <Typography variant="h4" gutterBottom>Project Summary</Typography>
                <Alert severity="info">{error}</Alert>
            </Box>
        );
    }

    if (!data) {
        return null;
    }

    const { summary, error_trend, problematic_steps, recommendations } = data;

    // Prepare chart data
    const chartData = error_trend.map(run => ({
        timestamp: new Date(run.timestamp).toLocaleDateString(),
        errors: run.total_errors,
        failed_steps: run.failed_steps
    }));

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Project Health Dashboard
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Tech Lead View - Comprehensive project analytics and error trends
            </Typography>

            {/* Key Metrics Cards */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} md={3}>
                    <Card>
                        <CardContent>
                            <Typography color="text.secondary" gutterBottom>
                                Total Pipeline Runs
                            </Typography>
                            <Typography variant="h3">
                                {summary.total_runs}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={3}>
                    <Card>
                        <CardContent>
                            <Typography color="text.secondary" gutterBottom>
                                Avg Errors Per Run
                            </Typography>
                            <Typography variant="h3">
                                {summary.average_errors_per_run}
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                                {getTrendIcon(summary.trend_direction)}
                                <Chip
                                    label={summary.trend_direction}
                                    size="small"
                                    color={getTrendColor(summary.trend_direction) as any}
                                    sx={{ ml: 1 }}
                                />
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={3}>
                    <Card>
                        <CardContent>
                            <Typography color="text.secondary" gutterBottom>
                                Project Health Score
                            </Typography>
                            <Typography variant="h3" color={`${getHealthColor(summary.health_score)}.main`}>
                                {summary.health_score}
                            </Typography>
                            <LinearProgress
                                variant="determinate"
                                value={summary.health_score}
                                color={getHealthColor(summary.health_score) as any}
                                sx={{ mt: 1, height: 8, borderRadius: 4 }}
                            />
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={3}>
                    <Card>
                        <CardContent>
                            <Typography color="text.secondary" gutterBottom>
                                Total Errors (All Time)
                            </Typography>
                            <Typography variant="h3">
                                {summary.total_errors_all_time}
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Error Trend Chart */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Error Trend Over Time
                    </Typography>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="errors"
                                stroke="#f44336"
                                strokeWidth={2}
                                name="Total Errors"
                            />
                            <Line
                                type="monotone"
                                dataKey="failed_steps"
                                stroke="#ff9800"
                                strokeWidth={2}
                                name="Failed Steps"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                    <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                            Recent Average: {summary.recent_avg_errors} errors
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            Previous Average: {summary.older_avg_errors} errors
                        </Typography>
                    </Box>
                </CardContent>
            </Card>

            {/* Recommendations */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                        <Warning sx={{ mr: 1 }} />
                        Recommendations & Action Items
                    </Typography>
                    {recommendations.map((rec, index) => (
                        <Alert
                            key={index}
                            severity={getRecommendationSeverity(rec)}
                            sx={{ mb: 1 }}
                        >
                            {rec}
                        </Alert>
                    ))}
                </CardContent>
            </Card>

            {/* Most Problematic Steps */}
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                        <ErrorIcon sx={{ mr: 1 }} />
                        Most Problematic Validation Steps
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                        <Table>
                            <TableHead>
                                <TableRow>
                                    <TableCell><strong>Step Name</strong></TableCell>
                                    <TableCell align="right"><strong>Total Errors</strong></TableCell>
                                    <TableCell align="right"><strong>Failures</strong></TableCell>
                                    <TableCell align="right"><strong>Total Runs</strong></TableCell>
                                    <TableCell align="right"><strong>Failure Rate</strong></TableCell>
                                    <TableCell align="center"><strong>Status</strong></TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {problematic_steps.map((step, index) => (
                                    <TableRow
                                        key={index}
                                        sx={{
                                            bgcolor: step.failure_rate > 80 ? 'error.light' :
                                                     step.failure_rate > 50 ? 'warning.light' : 'inherit'
                                        }}
                                    >
                                        <TableCell>{step.step_name}</TableCell>
                                        <TableCell align="right">{step.total_errors}</TableCell>
                                        <TableCell align="right">{step.failure_count}</TableCell>
                                        <TableCell align="right">{step.total_runs}</TableCell>
                                        <TableCell align="right">{step.failure_rate}%</TableCell>
                                        <TableCell align="center">
                                            {step.failure_rate > 80 ? (
                                                <Chip label="CRITICAL" color="error" size="small" />
                                            ) : step.failure_rate > 50 ? (
                                                <Chip label="HIGH" color="warning" size="small" />
                                            ) : step.failure_rate > 20 ? (
                                                <Chip label="MEDIUM" color="info" size="small" />
                                            ) : (
                                                <Chip label="LOW" color="success" size="small" />
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </CardContent>
            </Card>
        </Box>
    );
}
