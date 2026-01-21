import { Box, Card, CardContent, Grid, Typography, Chip, LinearProgress, CircularProgress } from '@mui/material';
import { CheckCircle, Warning, Error as ErrorIcon, Info } from '@mui/icons-material';

interface ExecutiveSummaryData {
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
}

interface ExecutiveSummaryProps {
    data: ExecutiveSummaryData;
}

export default function ExecutiveSummary({ data }: ExecutiveSummaryProps) {
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Ready':
                return 'success';
            case 'On Track':
                return 'warning';
            case 'At Risk':
                return 'error';
            default:
                return 'info';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'Ready':
                return <CheckCircle sx={{ fontSize: 40 }} color="success" />;
            case 'On Track':
                return <Warning sx={{ fontSize: 40 }} color="warning" />;
            case 'At Risk':
                return <ErrorIcon sx={{ fontSize: 40 }} color="error" />;
            default:
                return <Info sx={{ fontSize: 40 }} color="info" />;
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 90) return 'success';
        if (score >= 70) return 'warning';
        return 'error';
    };

    return (
        <Card sx={{ mb: 3, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
                    Executive Summary - Migration Readiness Report
                </Typography>

                <Grid container spacing={3}>
                    {/* Readiness Score - Large Circular Progress */}
                    <Grid item xs={12} md={4}>
                        <Box sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '100%',
                            position: 'relative'
                        }}>
                            <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                                <CircularProgress
                                    variant="determinate"
                                    value={data.readiness_score}
                                    size={150}
                                    thickness={6}
                                    sx={{
                                        color: data.readiness_score >= 90 ? '#4caf50' :
                                               data.readiness_score >= 70 ? '#ff9800' : '#f44336'
                                    }}
                                />
                                <Box
                                    sx={{
                                        top: 0,
                                        left: 0,
                                        bottom: 0,
                                        right: 0,
                                        position: 'absolute',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        flexDirection: 'column'
                                    }}
                                >
                                    <Typography variant="h3" component="div" sx={{ fontWeight: 'bold' }}>
                                        {Math.round(data.readiness_score)}%
                                    </Typography>
                                    <Typography variant="caption">
                                        Readiness
                                    </Typography>
                                </Box>
                            </Box>
                            <Box sx={{ mt: 2, textAlign: 'center' }}>
                                {getStatusIcon(data.overall_status)}
                                <Typography variant="h6" sx={{ mt: 1, fontWeight: 'bold' }}>
                                    {data.overall_status}
                                </Typography>
                            </Box>
                        </Box>
                    </Grid>

                    {/* Key Metrics */}
                    <Grid item xs={12} md={8}>
                        <Grid container spacing={2}>
                            {/* Total Validations */}
                            <Grid item xs={6} sm={3}>
                                <Box sx={{
                                    p: 2,
                                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                    borderRadius: 2,
                                    textAlign: 'center'
                                }}>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
                                        {data.total_validations}
                                    </Typography>
                                    <Typography variant="body2">
                                        Total Checks
                                    </Typography>
                                </Box>
                            </Grid>

                            {/* Passed Validations */}
                            <Grid item xs={6} sm={3}>
                                <Box sx={{
                                    p: 2,
                                    backgroundColor: 'rgba(76, 175, 80, 0.3)',
                                    borderRadius: 2,
                                    textAlign: 'center'
                                }}>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#4caf50' }}>
                                        {data.passed_validations}
                                    </Typography>
                                    <Typography variant="body2">
                                        Passing
                                    </Typography>
                                </Box>
                            </Grid>

                            {/* Warnings */}
                            <Grid item xs={6} sm={3}>
                                <Box sx={{
                                    p: 2,
                                    backgroundColor: 'rgba(255, 152, 0, 0.3)',
                                    borderRadius: 2,
                                    textAlign: 'center'
                                }}>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#ff9800' }}>
                                        {data.warnings}
                                    </Typography>
                                    <Typography variant="body2">
                                        Warnings
                                    </Typography>
                                </Box>
                            </Grid>

                            {/* Critical Issues */}
                            <Grid item xs={6} sm={3}>
                                <Box sx={{
                                    p: 2,
                                    backgroundColor: 'rgba(244, 67, 54, 0.3)',
                                    borderRadius: 2,
                                    textAlign: 'center'
                                }}>
                                    <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f44336' }}>
                                        {data.critical_issues}
                                    </Typography>
                                    <Typography variant="body2">
                                        Critical
                                    </Typography>
                                </Box>
                            </Grid>

                            {/* Severity Breakdown */}
                            <Grid item xs={12}>
                                <Box sx={{ mt: 2 }}>
                                    <Typography variant="subtitle2" gutterBottom>
                                        Issue Severity Breakdown
                                    </Typography>
                                    <Grid container spacing={1}>
                                        <Grid item xs={3}>
                                            <Chip
                                                label={`BLOCKER: ${data.severity_breakdown.BLOCKER}`}
                                                size="small"
                                                sx={{
                                                    width: '100%',
                                                    backgroundColor: '#d32f2f',
                                                    color: 'white',
                                                    fontWeight: 'bold'
                                                }}
                                            />
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Chip
                                                label={`HIGH: ${data.severity_breakdown.HIGH}`}
                                                size="small"
                                                sx={{
                                                    width: '100%',
                                                    backgroundColor: '#f57c00',
                                                    color: 'white',
                                                    fontWeight: 'bold'
                                                }}
                                            />
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Chip
                                                label={`MEDIUM: ${data.severity_breakdown.MEDIUM}`}
                                                size="small"
                                                sx={{
                                                    width: '100%',
                                                    backgroundColor: '#ffa726',
                                                    color: 'white',
                                                    fontWeight: 'bold'
                                                }}
                                            />
                                        </Grid>
                                        <Grid item xs={3}>
                                            <Chip
                                                label={`LOW: ${data.severity_breakdown.LOW}`}
                                                size="small"
                                                sx={{
                                                    width: '100%',
                                                    backgroundColor: '#66bb6a',
                                                    color: 'white',
                                                    fontWeight: 'bold'
                                                }}
                                            />
                                        </Grid>
                                    </Grid>
                                </Box>
                            </Grid>

                            {/* Progress Bar */}
                            <Grid item xs={12}>
                                <Box sx={{ mt: 1 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="caption">
                                            Progress to Ready State
                                        </Typography>
                                        <Typography variant="caption">
                                            {data.passed_validations} / {data.total_validations} Validations Passing
                                        </Typography>
                                    </Box>
                                    <LinearProgress
                                        variant="determinate"
                                        value={data.readiness_score}
                                        sx={{
                                            height: 10,
                                            borderRadius: 5,
                                            backgroundColor: 'rgba(255, 255, 255, 0.3)',
                                            '& .MuiLinearProgress-bar': {
                                                backgroundColor: data.readiness_score >= 90 ? '#4caf50' :
                                                               data.readiness_score >= 70 ? '#ff9800' : '#f44336',
                                                borderRadius: 5
                                            }
                                        }}
                                    />
                                </Box>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
            </CardContent>
        </Card>
    );
}
