import { Box, Card, CardContent, Typography, Grid, Chip, Alert, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, LinearProgress } from '@mui/material';
import { AttachMoney, Warning, TrendingUp, Assessment } from '@mui/icons-material';

interface FinancialImpactProps {
    data: {
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
}

export default function FinancialImpact({ data }: FinancialImpactProps) {
    const { table_criticality, financial_impact, risk_assessment } = data;

    const getRiskColor = (risk: string) => {
        switch (risk) {
            case 'Critical': return '#d32f2f';
            case 'High': return '#f57c00';
            case 'Medium': return '#ffa726';
            case 'Low': return '#66bb6a';
            default: return '#9e9e9e';
        }
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
    };

    return (
        <Card sx={{ mb: 3 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AttachMoney />
                    Financial Impact & Risk Assessment
                </Typography>

                <Grid container spacing={3} sx={{ mt: 1 }}>
                    {/* Risk Overview */}
                    <Grid item xs={12} md={4}>
                        <Box sx={{
                            p: 3,
                            backgroundColor: getRiskColor(risk_assessment.overall_risk) + '20',
                            borderRadius: 2,
                            border: `2px solid ${getRiskColor(risk_assessment.overall_risk)}`,
                            textAlign: 'center'
                        }}>
                            <Warning sx={{ fontSize: 48, color: getRiskColor(risk_assessment.overall_risk), mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: getRiskColor(risk_assessment.overall_risk) }}>
                                {risk_assessment.overall_risk}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Overall Risk Level
                            </Typography>
                            <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                                {risk_assessment.migration_readiness}
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Financial Impact */}
                    <Grid item xs={12} md={4}>
                        <Box sx={{ p: 3, backgroundColor: '#fff3e0', borderRadius: 2, textAlign: 'center' }}>
                            <AttachMoney sx={{ fontSize: 48, color: '#f57c00', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                                {formatCurrency(financial_impact.total_estimated_cost)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Estimated Cost Impact
                            </Typography>
                            <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                                Avg: {formatCurrency(financial_impact.average_cost_per_error)}/error
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Critical Tables */}
                    <Grid item xs={12} md={4}>
                        <Box sx={{ p: 3, backgroundColor: '#ffebee', borderRadius: 2, textAlign: 'center' }}>
                            <Assessment sx={{ fontSize: 48, color: '#d32f2f', mb: 1 }} />
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
                                {risk_assessment.critical_tables_at_risk}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Critical Tables at Risk
                            </Typography>
                            <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
                                {risk_assessment.blocker_issues} blockers, {risk_assessment.high_severity_issues} high severity
                            </Typography>
                        </Box>
                    </Grid>

                    {/* Risk Factors */}
                    {risk_assessment.risk_factors.length > 0 && (
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mt: 2 }}>
                                Risk Factors
                            </Typography>
                            {risk_assessment.risk_factors.map((factor, idx) => (
                                <Alert key={idx} severity={factor.impact === 'Critical' ? 'error' : 'warning'} sx={{ mb: 1 }}>
                                    <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                                        {factor.factor}
                                    </Typography>
                                    <Typography variant="body2">
                                        {factor.description}
                                    </Typography>
                                </Alert>
                            ))}
                        </Grid>
                    )}

                    {/* Cost Breakdown Table */}
                    {financial_impact.cost_breakdown.length > 0 && (
                        <Grid item xs={12}>
                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mt: 2 }}>
                                Top Cost Impact Tables
                            </Typography>
                            <TableContainer component={Paper} sx={{ maxHeight: 300 }}>
                                <Table size="small" stickyHeader>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell><strong>Table Name</strong></TableCell>
                                            <TableCell align="right"><strong>Errors</strong></TableCell>
                                            <TableCell align="right"><strong>Criticality</strong></TableCell>
                                            <TableCell align="right"><strong>Unit Cost</strong></TableCell>
                                            <TableCell align="right"><strong>Total Cost</strong></TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {financial_impact.cost_breakdown.map((row, idx) => (
                                            <TableRow key={idx}>
                                                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                                    {row.table_name}
                                                </TableCell>
                                                <TableCell align="right">{row.error_count}</TableCell>
                                                <TableCell align="right">
                                                    <Chip
                                                        label={row.criticality_score}
                                                        size="small"
                                                        color={row.criticality_score >= 8 ? 'error' : row.criticality_score >= 6 ? 'warning' : 'default'}
                                                    />
                                                </TableCell>
                                                <TableCell align="right">{formatCurrency(row.unit_cost)}</TableCell>
                                                <TableCell align="right" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                                                    {formatCurrency(row.total_cost)}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </Grid>
                    )}
                </Grid>
            </CardContent>
        </Card>
    );
}
