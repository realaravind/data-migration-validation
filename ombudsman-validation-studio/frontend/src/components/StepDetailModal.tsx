import { useState, useEffect } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Box, Typography, Chip, Alert, CircularProgress,
    Button, Divider, Paper, IconButton, Tooltip, Tab, Tabs
} from '@mui/material';
import {
    Close, CheckCircle, Error as ErrorIcon, Warning,
    Code, CompareArrows, Info, Assessment
} from '@mui/icons-material';

interface StepDetailModalProps {
    open: boolean;
    onClose: () => void;
    runId: string;
    stepName: string;
}

interface StepDetail {
    run_id: string;
    step_name: string;
    status: string;
    severity?: string;
    validation_type?: string;
    message: string;
    error_count: number;
    execution_time?: string;
    errors?: any[];
    queries?: {
        sql_query?: string;
        snow_query?: string;
    };
    has_comparison_data: boolean;
    comparison_summary?: {
        total_rows: number;
        differing_rows: number;
        affected_columns: string[];
        difference_type?: string;
    };
    metadata?: any;
}

export default function StepDetailModal({ open, onClose, runId, stepName }: StepDetailModalProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [stepDetail, setStepDetail] = useState<StepDetail | null>(null);
    const [currentTab, setCurrentTab] = useState(0);

    useEffect(() => {
        if (open && runId && stepName) {
            fetchStepDetails();
        }
    }, [open, runId, stepName]);

    const fetchStepDetails = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`http://localhost:8000/results/${runId}/step/${stepName}`);

            if (!response.ok) {
                throw new Error(`Failed to fetch step details: ${response.statusText}`);
            }

            const data = await response.json();
            setStepDetail(data);
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'success':
            case 'passed':
                return <CheckCircle sx={{ color: '#4caf50', fontSize: 32 }} />;
            case 'failure':
            case 'failed':
                return <ErrorIcon sx={{ color: '#d32f2f', fontSize: 32 }} />;
            case 'warning':
                return <Warning sx={{ color: '#ff9800', fontSize: 32 }} />;
            default:
                return <Info sx={{ color: '#9e9e9e', fontSize: 32 }} />;
        }
    };

    const getSeverityColor = (severity?: string) => {
        switch (severity?.toUpperCase()) {
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

    const handleViewComparison = () => {
        // Navigate to comparison view - can be implemented later
        window.open(`/results/${runId}/step/${stepName}/comparison`, '_blank');
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: { minHeight: '60vh' }
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Assessment sx={{ fontSize: 28 }} />
                    <Typography variant="h6">
                        Validation Step Details
                    </Typography>
                </Box>
                <IconButton onClick={onClose} size="small">
                    <Close />
                </IconButton>
            </DialogTitle>

            <Divider />

            <DialogContent>
                {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
                        <CircularProgress />
                    </Box>
                )}

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                )}

                {stepDetail && !loading && (
                    <Box>
                        {/* Header Section */}
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 3 }}>
                            {getStatusIcon(stepDetail.status)}
                            <Box sx={{ flexGrow: 1 }}>
                                <Typography variant="h6" sx={{ fontFamily: 'monospace', mb: 1 }}>
                                    {stepDetail.step_name}
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                    <Chip
                                        label={stepDetail.status}
                                        size="small"
                                        color={stepDetail.status?.toLowerCase() === 'success' ? 'success' : 'error'}
                                    />
                                    {stepDetail.severity && (
                                        <Chip
                                            label={`Severity: ${stepDetail.severity}`}
                                            size="small"
                                            sx={{
                                                backgroundColor: getSeverityColor(stepDetail.severity),
                                                color: 'white'
                                            }}
                                        />
                                    )}
                                    {stepDetail.validation_type && (
                                        <Chip
                                            label={stepDetail.validation_type}
                                            size="small"
                                            variant="outlined"
                                        />
                                    )}
                                    {stepDetail.error_count > 0 && (
                                        <Chip
                                            label={`${stepDetail.error_count} errors`}
                                            size="small"
                                            color="error"
                                            variant="outlined"
                                        />
                                    )}
                                    {stepDetail.execution_time && (
                                        <Chip
                                            label={`Execution: ${stepDetail.execution_time}`}
                                            size="small"
                                            variant="outlined"
                                        />
                                    )}
                                </Box>
                            </Box>
                        </Box>

                        {/* Message */}
                        {stepDetail.message && (
                            <Alert
                                severity={stepDetail.status?.toLowerCase() === 'success' ? 'success' : 'error'}
                                sx={{ mb: 3 }}
                            >
                                {stepDetail.message}
                            </Alert>
                        )}

                        {/* Comparison Summary */}
                        {stepDetail.has_comparison_data && stepDetail.comparison_summary && (
                            <Paper sx={{ p: 2, mb: 3, backgroundColor: '#f5f5f5' }}>
                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CompareArrows />
                                    Comparison Summary
                                </Typography>
                                <Box sx={{ display: 'flex', gap: 3, mt: 2, flexWrap: 'wrap' }}>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Total Rows
                                        </Typography>
                                        <Typography variant="h6">
                                            {stepDetail.comparison_summary.total_rows.toLocaleString()}
                                        </Typography>
                                    </Box>
                                    <Box>
                                        <Typography variant="caption" color="text.secondary">
                                            Differing Rows
                                        </Typography>
                                        <Typography variant="h6" sx={{ color: '#d32f2f' }}>
                                            {stepDetail.comparison_summary.differing_rows.toLocaleString()}
                                        </Typography>
                                    </Box>
                                    {stepDetail.comparison_summary.affected_columns && stepDetail.comparison_summary.affected_columns.length > 0 && (
                                        <Box>
                                            <Typography variant="caption" color="text.secondary">
                                                Affected Columns
                                            </Typography>
                                            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                                                {stepDetail.comparison_summary.affected_columns.map((col, idx) => (
                                                    <Chip key={idx} label={col} size="small" />
                                                ))}
                                            </Box>
                                        </Box>
                                    )}
                                </Box>
                                <Box sx={{ mt: 2 }}>
                                    <Button
                                        variant="outlined"
                                        startIcon={<CompareArrows />}
                                        onClick={handleViewComparison}
                                        size="small"
                                    >
                                        View Full Comparison
                                    </Button>
                                </Box>
                            </Paper>
                        )}

                        {/* Tabs for Queries and Errors */}
                        {(stepDetail.queries || stepDetail.errors) && (
                            <Box>
                                <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                                    {stepDetail.queries && <Tab label="SQL Queries" icon={<Code />} iconPosition="start" />}
                                    {stepDetail.errors && stepDetail.errors.length > 0 && <Tab label={`Errors (${stepDetail.errors.length})`} icon={<ErrorIcon />} iconPosition="start" />}
                                </Tabs>

                                {/* SQL Queries Tab */}
                                {stepDetail.queries && currentTab === 0 && (
                                    <Box sx={{ mt: 2 }}>
                                        {stepDetail.queries.sql_query && (
                                            <Box sx={{ mb: 2 }}>
                                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                                    SQL Server Query
                                                </Typography>
                                                <Paper sx={{
                                                    p: 2,
                                                    backgroundColor: '#263238',
                                                    color: '#fff',
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.85rem',
                                                    maxHeight: 300,
                                                    overflow: 'auto'
                                                }}>
                                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                                        {stepDetail.queries.sql_query}
                                                    </pre>
                                                </Paper>
                                            </Box>
                                        )}
                                        {stepDetail.queries.snow_query && (
                                            <Box>
                                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                                    Snowflake Query
                                                </Typography>
                                                <Paper sx={{
                                                    p: 2,
                                                    backgroundColor: '#263238',
                                                    color: '#fff',
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.85rem',
                                                    maxHeight: 300,
                                                    overflow: 'auto'
                                                }}>
                                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                                        {stepDetail.queries.snow_query}
                                                    </pre>
                                                </Paper>
                                            </Box>
                                        )}
                                    </Box>
                                )}

                                {/* Errors Tab */}
                                {stepDetail.errors && stepDetail.errors.length > 0 && currentTab === (stepDetail.queries ? 1 : 0) && (
                                    <Box sx={{ mt: 2, maxHeight: 400, overflow: 'auto' }}>
                                        {stepDetail.errors.map((error, idx) => (
                                            <Alert key={idx} severity="error" sx={{ mb: 1 }}>
                                                {typeof error === 'string' ? error : JSON.stringify(error)}
                                            </Alert>
                                        ))}
                                    </Box>
                                )}
                            </Box>
                        )}
                    </Box>
                )}
            </DialogContent>

            <Divider />

            <DialogActions>
                <Button onClick={onClose} variant="outlined">
                    Close
                </Button>
            </DialogActions>
        </Dialog>
    );
}
