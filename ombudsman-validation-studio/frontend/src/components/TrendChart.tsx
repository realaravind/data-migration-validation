import { Box, Card, CardContent, Typography, Grid, Chip, Alert } from '@mui/material';
import { TrendingDown, TrendingUp, TrendingFlat, CalendarToday } from '@mui/icons-material';

interface TrendPoint {
    timestamp: string;
    total_errors: number;
}

interface Velocity {
    per_day: number;
    per_week: number;
}

interface TrendAnalysisData {
    error_trend: TrendPoint[];
    velocity: Velocity;
    projected_zero_date: string | null;
    regression_detected: boolean;
}

interface TrendChartProps {
    data: TrendAnalysisData;
}

export default function TrendChart({ data }: TrendChartProps) {
    const { error_trend, velocity, projected_zero_date, regression_detected } = data;

    // If no trend data, show message
    if (!error_trend || error_trend.length === 0) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Trend Analysis
                    </Typography>
                    <Alert severity="info">
                        Insufficient historical data for trend analysis. Execute this pipeline at least 2 times to see trends.
                    </Alert>
                </CardContent>
            </Card>
        );
    }

    // Calculate chart dimensions and scale
    const chartWidth = 600;
    const chartHeight = 200;
    const padding = 40;

    const maxErrors = Math.max(...error_trend.map(p => p.total_errors), 1);
    const minErrors = Math.min(...error_trend.map(p => p.total_errors), 0);

    // Calculate points for the line chart
    const points = error_trend.map((point, index) => {
        const x = padding + (index / (error_trend.length - 1 || 1)) * (chartWidth - 2 * padding);
        const y = chartHeight - padding - ((point.total_errors - minErrors) / (maxErrors - minErrors || 1)) * (chartHeight - 2 * padding);
        return { x, y, errors: point.total_errors, timestamp: point.timestamp };
    });

    // Create SVG path
    const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

    // Format date for display
    const formatDate = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    // Determine trend direction
    const getTrendIcon = () => {
        if (regression_detected) {
            return <TrendingUp sx={{ color: '#f44336', fontSize: 40 }} />;
        } else if (velocity.per_day < 0) {
            return <TrendingDown sx={{ color: '#4caf50', fontSize: 40 }} />;
        } else {
            return <TrendingFlat sx={{ color: '#ff9800', fontSize: 40 }} />;
        }
    };

    const getTrendColor = () => {
        if (regression_detected) return '#f44336';
        if (velocity.per_day < 0) return '#4caf50';
        return '#ff9800';
    };

    const getTrendMessage = () => {
        if (regression_detected) {
            return 'Errors increasing - regression detected';
        } else if (velocity.per_day < 0) {
            return 'Errors decreasing - good progress';
        } else {
            return 'Errors stable - no significant change';
        }
    };

    return (
        <Card sx={{ mb: 3 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    Trend Analysis
                    {regression_detected && (
                        <Chip
                            label="REGRESSION DETECTED"
                            color="error"
                            size="small"
                            sx={{ fontWeight: 'bold' }}
                        />
                    )}
                </Typography>

                <Grid container spacing={3}>
                    {/* Error Trend Chart */}
                    <Grid item xs={12} md={8}>
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                                Error Count Over Time (Last {error_trend.length} Runs)
                            </Typography>
                            <svg width={chartWidth} height={chartHeight} style={{ border: '1px solid #e0e0e0', borderRadius: '8px', background: '#fafafa' }}>
                                {/* Grid lines */}
                                <line x1={padding} y1={padding} x2={padding} y2={chartHeight - padding} stroke="#ccc" strokeWidth="2" />
                                <line x1={padding} y1={chartHeight - padding} x2={chartWidth - padding} y2={chartHeight - padding} stroke="#ccc" strokeWidth="2" />

                                {/* Horizontal grid lines */}
                                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                                    const y = chartHeight - padding - ratio * (chartHeight - 2 * padding);
                                    const value = Math.round(minErrors + ratio * (maxErrors - minErrors));
                                    return (
                                        <g key={i}>
                                            <line
                                                x1={padding}
                                                y1={y}
                                                x2={chartWidth - padding}
                                                y2={y}
                                                stroke="#e0e0e0"
                                                strokeWidth="1"
                                                strokeDasharray="4"
                                            />
                                            <text x={padding - 30} y={y + 5} fontSize="12" fill="#666">{value}</text>
                                        </g>
                                    );
                                })}

                                {/* Line path */}
                                <path
                                    d={pathData}
                                    fill="none"
                                    stroke={getTrendColor()}
                                    strokeWidth="3"
                                />

                                {/* Data points */}
                                {points.map((point, i) => (
                                    <g key={i}>
                                        <circle cx={point.x} cy={point.y} r="5" fill={getTrendColor()} />
                                        <title>{`${formatDate(point.timestamp)}: ${point.errors} errors`}</title>
                                    </g>
                                ))}

                                {/* X-axis labels (first and last) */}
                                <text x={padding} y={chartHeight - 10} fontSize="11" fill="#666">
                                    {formatDate(error_trend[0].timestamp)}
                                </text>
                                <text x={chartWidth - padding - 80} y={chartHeight - 10} fontSize="11" fill="#666">
                                    {formatDate(error_trend[error_trend.length - 1].timestamp)}
                                </text>

                                {/* Y-axis label */}
                                <text x={10} y={20} fontSize="12" fill="#666" fontWeight="bold">Errors</text>
                            </svg>
                        </Box>
                    </Grid>

                    {/* Velocity Metrics */}
                    <Grid item xs={12} md={4}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
                            {/* Trend Direction */}
                            <Box sx={{
                                p: 2,
                                backgroundColor: getTrendColor() + '20',
                                borderRadius: 2,
                                textAlign: 'center',
                                border: `2px solid ${getTrendColor()}`
                            }}>
                                {getTrendIcon()}
                                <Typography variant="body2" sx={{ mt: 1, fontWeight: 'bold', color: getTrendColor() }}>
                                    {getTrendMessage()}
                                </Typography>
                            </Box>

                            {/* Velocity Metrics */}
                            <Box sx={{ p: 2, backgroundColor: '#f5f5f5', borderRadius: 2 }}>
                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                    Error Reduction Velocity
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Per Day: <strong style={{ color: velocity.per_day < 0 ? '#4caf50' : '#f44336' }}>
                                        {velocity.per_day > 0 ? '+' : ''}{velocity.per_day.toFixed(2)}
                                    </strong>
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Per Week: <strong style={{ color: velocity.per_week < 0 ? '#4caf50' : '#f44336' }}>
                                        {velocity.per_week > 0 ? '+' : ''}{velocity.per_week.toFixed(2)}
                                    </strong>
                                </Typography>
                            </Box>

                            {/* Projected Completion */}
                            {projected_zero_date && (
                                <Box sx={{ p: 2, backgroundColor: '#e3f2fd', borderRadius: 2, border: '1px solid #2196f3' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                        <CalendarToday sx={{ fontSize: 20, color: '#2196f3' }} />
                                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#2196f3' }}>
                                            Projected Zero-Error Date
                                        </Typography>
                                    </Box>
                                    <Typography variant="body2" color="text.secondary">
                                        {formatDate(projected_zero_date)}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                        Based on current velocity
                                    </Typography>
                                </Box>
                            )}

                            {/* Current vs First Run */}
                            <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 2, border: '1px solid #ff9800' }}>
                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                    Progress Summary
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    First Run: <strong>{error_trend[0].total_errors}</strong> errors
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Latest Run: <strong>{error_trend[error_trend.length - 1].total_errors}</strong> errors
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                    Change: <strong style={{
                                        color: error_trend[error_trend.length - 1].total_errors < error_trend[0].total_errors ? '#4caf50' : '#f44336'
                                    }}>
                                        {error_trend[error_trend.length - 1].total_errors - error_trend[0].total_errors > 0 ? '+' : ''}
                                        {error_trend[error_trend.length - 1].total_errors - error_trend[0].total_errors}
                                    </strong>
                                </Typography>
                            </Box>
                        </Box>
                    </Grid>
                </Grid>
            </CardContent>
        </Card>
    );
}
