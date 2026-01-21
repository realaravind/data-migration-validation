import { Box, Card, CardContent, Typography, Grid, Chip, Accordion, AccordionSummary, AccordionDetails, Alert } from '@mui/material';
import { ExpandMore, Error as ErrorIcon, Warning, BugReport, Category } from '@mui/icons-material';

interface RootCauseGroup {
    category: string;
    title: string;
    description: string;
    affected_steps: string[];
    total_affected: number;
    total_errors: number;
    severity: string;
    recommended_action: string;
}

interface RootCauseGroupsProps {
    groups: RootCauseGroup[];
    runId?: string;
    onStepClick?: (runId: string, stepName: string) => void;
}

export default function RootCauseGroups({ groups, runId, onStepClick }: RootCauseGroupsProps) {
    if (!groups || groups.length === 0) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Root Cause Analysis
                    </Typography>
                    <Alert severity="success">
                        No error patterns detected. All validations are passing!
                    </Alert>
                </CardContent>
            </Card>
        );
    }

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'BLOCKER':
                return '#d32f2f';
            case 'HIGH':
                return '#f57c00';
            case 'MEDIUM':
                return '#ffa726';
            case 'LOW':
                return '#66bb6a';
            default:
                return '#9e9e9e';
        }
    };

    const getCategoryIcon = (category: string) => {
        if (category.includes('blocker') || category.includes('critical')) {
            return <ErrorIcon sx={{ color: '#d32f2f', fontSize: 28 }} />;
        } else if (category.includes('schema') || category.includes('dimension') || category.includes('fact')) {
            return <Category sx={{ color: '#2196f3', fontSize: 28 }} />;
        } else if (category.includes('foreign_key') || category.includes('null')) {
            return <BugReport sx={{ color: '#f57c00', fontSize: 28 }} />;
        } else {
            return <Warning sx={{ color: '#ff9800', fontSize: 28 }} />;
        }
    };

    return (
        <Card sx={{ mb: 3 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <BugReport />
                    Root Cause Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
                    Errors grouped by common patterns to help identify systemic issues
                </Typography>

                {/* Summary Stats */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                                {groups.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Root Cause Categories
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#ffebee', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
                                {groups.reduce((sum, g) => sum + g.total_affected, 0)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Affected Steps
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#fce4ec', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#c2185b' }}>
                                {groups.reduce((sum, g) => sum + g.total_errors, 0)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total Errors
                            </Typography>
                        </Box>
                    </Grid>
                </Grid>

                {/* Root Cause Groups */}
                <Box>
                    {groups.map((group, index) => (
                        <Accordion key={index} sx={{ mb: 1, '&:before': { display: 'none' } }}>
                            <AccordionSummary
                                expandIcon={<ExpandMore />}
                                sx={{
                                    backgroundColor: getSeverityColor(group.severity) + '10',
                                    borderLeft: `4px solid ${getSeverityColor(group.severity)}`,
                                    '&:hover': {
                                        backgroundColor: getSeverityColor(group.severity) + '20'
                                    }
                                }}
                            >
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                                    {getCategoryIcon(group.category)}
                                    <Box sx={{ flexGrow: 1 }}>
                                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                            {group.title}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {group.description}
                                        </Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                        <Chip
                                            label={group.severity}
                                            size="small"
                                            sx={{
                                                backgroundColor: getSeverityColor(group.severity),
                                                color: 'white',
                                                fontWeight: 'bold'
                                            }}
                                        />
                                        <Chip
                                            label={`${group.total_affected} steps`}
                                            size="small"
                                            variant="outlined"
                                        />
                                        <Chip
                                            label={`${group.total_errors} errors`}
                                            size="small"
                                            variant="outlined"
                                            color="error"
                                        />
                                    </Box>
                                </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                                <Grid container spacing={2}>
                                    {/* Affected Steps */}
                                    <Grid item xs={12} md={6}>
                                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                            Affected Validation Steps
                                        </Typography>
                                        <Box sx={{ maxHeight: 200, overflow: 'auto', p: 1, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                                            {group.affected_steps.map((step, idx) => (
                                                <Typography
                                                    key={idx}
                                                    variant="body2"
                                                    sx={{
                                                        mb: 0.5,
                                                        fontFamily: 'monospace',
                                                        cursor: runId && onStepClick ? 'pointer' : 'default',
                                                        color: runId && onStepClick ? 'primary.main' : 'text.primary',
                                                        '&:hover': runId && onStepClick ? {
                                                            textDecoration: 'underline',
                                                            color: 'primary.dark'
                                                        } : {}
                                                    }}
                                                    onClick={() => runId && onStepClick && onStepClick(runId, step)}
                                                >
                                                    {idx + 1}. {step}
                                                </Typography>
                                            ))}
                                        </Box>
                                    </Grid>

                                    {/* Recommended Action */}
                                    <Grid item xs={12} md={6}>
                                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                            Recommended Action
                                        </Typography>
                                        <Alert severity="info" sx={{ mt: 1 }}>
                                            {group.recommended_action}
                                        </Alert>
                                    </Grid>
                                </Grid>
                            </AccordionDetails>
                        </Accordion>
                    ))}
                </Box>
            </CardContent>
        </Card>
    );
}
