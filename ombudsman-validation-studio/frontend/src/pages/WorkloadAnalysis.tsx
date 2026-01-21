import { useState } from 'react';
import {
    Box,
    Typography,
    Paper,
    Button,
    Stepper,
    Step,
    StepLabel,
    Alert,
    CircularProgress,
    Card,
    CardContent,
    Grid,
    Chip,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Checkbox,
    FormControlLabel,
    LinearProgress,
    Divider,
    Stack
} from '@mui/material';
import {
    CloudUpload,
    CheckCircle,
    Analytics,
    Description,
    ExpandMore,
    Insights,
    Download
} from '@mui/icons-material';

interface ValidationSuggestion {
    validator_name: string;
    table_name: string;
    schema_name: string;
    columns: string[];
    confidence: number;
    reason: string;
    query_count: number;
    total_executions: number;
    source: string;
    metadata: any;
}

interface TableAnalysis {
    suggestions: ValidationSuggestion[];
    access_count: number;
    join_partners: string[];
    columns_analyzed: number;
}

interface WorkloadAnalysis {
    tables: Record<string, TableAnalysis>;
    coverage: {
        total_queries: number;
        queries_covered: number;
        coverage_percentage: number;
        total_executions_covered: number;
        validation_count: number;
        high_confidence_count: number;
        medium_confidence_count: number;
        low_confidence_count: number;
    };
    categories: Record<string, number>;
    total_suggestions: number;
}

interface Workload {
    workload_id: string;
    upload_date: string;
    query_count: number;
    total_executions: number;
    tables_count: number;
    analysis?: WorkloadAnalysis;
}

interface WorkloadAnalysisProps {
    currentProject?: { project_id: string; name: string };
}

export default function WorkloadAnalysis({ currentProject }: WorkloadAnalysisProps) {
    const [activeStep, setActiveStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [currentWorkload, setCurrentWorkload] = useState<Workload | null>(null);
    const [selectedValidations, setSelectedValidations] = useState<Set<string>>(new Set());
    const [generationResult, setGenerationResult] = useState<any>(null);
    const projectId = currentProject?.project_id || 'default_project';

    const steps = ['Upload Workload', 'View Analysis', 'Select Validations', 'Generate Pipelines'];

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setUploadedFile(file);
        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('project_id', projectId);

            const response = await fetch('http://localhost:8000/workload/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();

            // Fetch full workload details
            await fetch(
                `http://localhost:8000/workload/${projectId}/${data.workload_id}`
            );

            // Analyze the workload
            await analyzeWorkload(data.workload_id);

            setActiveStep(1);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setLoading(false);
        }
    };

    const analyzeWorkload = async (workloadId: string) => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/workload/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workload_id: workloadId,
                    project_id: projectId,
                    metadata: {} // Could be populated from database mapping
                })
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const response_data = await response.json();
            const analysis = response_data.data || response_data; // Handle both {data: ...} and direct response

            setCurrentWorkload({
                workload_id: workloadId,
                upload_date: new Date().toISOString(),
                query_count: analysis.coverage?.total_queries || 0,
                total_executions: analysis.coverage?.total_executions_covered || 0,
                tables_count: Object.keys(analysis.tables || {}).length,
                analysis
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Analysis failed');
        } finally {
            setLoading(false);
        }
    };

    const handleValidationToggle = (validationKey: string) => {
        const newSelected = new Set(selectedValidations);
        if (newSelected.has(validationKey)) {
            newSelected.delete(validationKey);
        } else {
            newSelected.add(validationKey);
        }
        setSelectedValidations(newSelected);
    };

    const handleGeneratePipelines = async () => {
        if (!currentWorkload?.analysis) return;

        setLoading(true);
        setError(null);

        try {
            // Collect selected validations
            const { tables } = currentWorkload.analysis;
            const selectedValidationsList: any[] = [];

            Object.entries(tables).forEach(([tableName, tableData]) => {
                tableData.suggestions.forEach((suggestion, idx) => {
                    const key = `${tableName}_${idx}`;
                    if (selectedValidations.has(key)) {
                        selectedValidationsList.push(suggestion);
                    }
                });
            });

            const response = await fetch('http://localhost:8000/workload/generate-pipelines', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    workload_id: currentWorkload.workload_id,
                    validations: selectedValidationsList
                })
            });

            if (!response.ok) {
                throw new Error('Pipeline generation failed');
            }

            const result = await response.json();
            setGenerationResult(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Generation failed');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateComparativePipelines = async () => {
        if (!currentWorkload) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/workload/generate-comparative-pipelines', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    workload_id: currentWorkload.workload_id,
                    schema_mapping: {
                        dim: 'DIM',
                        fact: 'FACT',
                        dbo: 'PUBLIC'
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Comparative pipeline generation failed');
            }

            const result = await response.json();
            setGenerationResult(result);
            setActiveStep(3);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Comparative generation failed');
        } finally {
            setLoading(false);
        }
    };

    const handleSaveToProject = async () => {
        if (!generationResult || !generationResult.pipeline_files) {
            alert('No pipelines to save. Please generate pipelines first.');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/workload/save-pipelines-to-project', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    pipeline_files: generationResult.pipeline_files
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save pipelines to project');
            }

            const result = await response.json();
            alert(`Successfully saved ${result.saved_count} pipeline(s) to project ${projectId}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Save failed');
            alert('Failed to save pipelines to project');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadQueryGenerator = () => {
        window.open('http://localhost:8000/workload/download-query-generator', '_blank');
    };

    const getConfidenceColor = (confidence: number) => {
        if (confidence >= 0.8) return 'success';
        if (confidence >= 0.6) return 'warning';
        return 'error';
    };

    const getConfidenceLabel = (confidence: number) => {
        if (confidence >= 0.8) return 'High';
        if (confidence >= 0.6) return 'Medium';
        return 'Low';
    };

    const renderUploadStep = () => (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
            <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
                Upload Query Store Workload
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
                Upload a JSON file exported from SQL Server Query Store containing your top queries
            </Typography>

            <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
                <Typography variant="subtitle2" gutterBottom>
                    <strong>Need a Query Store JSON file?</strong>
                </Typography>
                <Typography variant="body2" gutterBottom>
                    1. Download the SQL query generator script below
                </Typography>
                <Typography variant="body2" gutterBottom>
                    2. Run it on your SQL Server database (requires Query Store enabled)
                </Typography>
                <Typography variant="body2" gutterBottom>
                    3. Copy the JSON output and save it as a .json file
                </Typography>
                <Typography variant="body2">
                    4. Upload the file using the button below
                </Typography>
            </Alert>

            <Stack direction="row" spacing={2} justifyContent="center" sx={{ mb: 2 }}>
                <Button
                    variant="outlined"
                    startIcon={<Download />}
                    onClick={handleDownloadQueryGenerator}
                >
                    Download SQL Query Generator
                </Button>

                <Button
                    variant="contained"
                    component="label"
                    startIcon={<CloudUpload />}
                    disabled={loading}
                >
                    {loading ? 'Uploading...' : 'Upload JSON File'}
                    <input
                        type="file"
                        hidden
                        accept=".json"
                        onChange={handleFileUpload}
                    />
                </Button>
            </Stack>

            {uploadedFile && (
                <Alert severity="info" sx={{ mt: 2 }}>
                    Selected: {uploadedFile.name}
                </Alert>
            )}

            {loading && <CircularProgress sx={{ mt: 2 }} />}
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </Paper>
    );

    const renderAnalysisStep = () => {
        if (!currentWorkload?.analysis) return null;

        const { coverage, categories, tables } = currentWorkload.analysis;

        return (
            <Box>
                {/* Coverage Summary */}
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            <Insights sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Workload Coverage
                        </Typography>
                        <Grid container spacing={2} sx={{ mt: 1 }}>
                            <Grid item xs={12} md={3}>
                                <Typography variant="body2" color="text.secondary">
                                    Queries Analyzed
                                </Typography>
                                <Typography variant="h4">
                                    {coverage.total_queries}
                                </Typography>
                            </Grid>
                            <Grid item xs={12} md={3}>
                                <Typography variant="body2" color="text.secondary">
                                    Coverage
                                </Typography>
                                <Typography variant="h4">
                                    {coverage.coverage_percentage.toFixed(1)}%
                                </Typography>
                                <LinearProgress
                                    variant="determinate"
                                    value={coverage.coverage_percentage}
                                    sx={{ mt: 1 }}
                                />
                            </Grid>
                            <Grid item xs={12} md={3}>
                                <Typography variant="body2" color="text.secondary">
                                    Validations Generated
                                </Typography>
                                <Typography variant="h4">
                                    {coverage.validation_count}
                                </Typography>
                            </Grid>
                            <Grid item xs={12} md={3}>
                                <Typography variant="body2" color="text.secondary">
                                    Executions Covered
                                </Typography>
                                <Typography variant="h4">
                                    {coverage.total_executions_covered?.toLocaleString() || '0'}
                                </Typography>
                            </Grid>
                        </Grid>

                        <Divider sx={{ my: 2 }} />

                        {/* Confidence Distribution */}
                        <Typography variant="subtitle2" gutterBottom>
                            Confidence Distribution
                        </Typography>
                        <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                            <Chip
                                label={`High: ${coverage.high_confidence_count}`}
                                color="success"
                                size="small"
                            />
                            <Chip
                                label={`Medium: ${coverage.medium_confidence_count}`}
                                color="warning"
                                size="small"
                            />
                            <Chip
                                label={`Low: ${coverage.low_confidence_count}`}
                                color="error"
                                size="small"
                            />
                        </Stack>
                    </CardContent>
                </Card>

                {/* Category Breakdown */}
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            <Analytics sx={{ mr: 1, verticalAlign: 'middle' }} />
                            Validation Categories
                        </Typography>
                        <Grid container spacing={1} sx={{ mt: 1 }}>
                            {Object.entries(categories).map(([category, count]) => (
                                <Grid item xs={12} sm={6} md={4} key={category}>
                                    <Chip
                                        label={`${category}: ${count}`}
                                        variant="outlined"
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                            ))}
                        </Grid>
                    </CardContent>
                </Card>

                {/* Table Analysis */}
                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                    <Description sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Table Analysis ({Object.keys(tables).length} tables)
                </Typography>

                {Object.entries(tables).map(([tableName, tableData]) => (
                    <Accordion key={tableName} sx={{ mb: 1 }}>
                        <AccordionSummary expandIcon={<ExpandMore />}>
                            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                                <Typography sx={{ flexGrow: 1 }}>
                                    {tableName}
                                </Typography>
                                <Chip
                                    label={`${tableData.suggestions.length} suggestions`}
                                    size="small"
                                    color="primary"
                                    sx={{ mr: 2 }}
                                />
                                {tableData.access_count !== undefined && (
                                    <Chip
                                        label={`${tableData.access_count.toLocaleString()} accesses`}
                                        size="small"
                                        variant="outlined"
                                    />
                                )}
                            </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Typography variant="subtitle2" gutterBottom>
                                Suggested Validations:
                            </Typography>
                            {tableData.suggestions.slice(0, 5).map((suggestion, idx) => (
                                <Paper key={idx} sx={{ p: 2, mb: 1, bgcolor: 'grey.50' }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                        <Typography variant="body2" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
                                            {suggestion.validator_name}
                                        </Typography>
                                        <Chip
                                            label={`${getConfidenceLabel(suggestion.confidence)} (${(suggestion.confidence * 100).toFixed(0)}%)`}
                                            color={getConfidenceColor(suggestion.confidence)}
                                            size="small"
                                        />
                                    </Box>
                                    <Typography variant="body2" color="text.secondary">
                                        {suggestion.reason}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                                        Columns: {suggestion.columns?.length > 0 ? suggestion.columns.join(', ') : 'N/A'} •
                                        Queries: {suggestion.query_count || 0} •
                                        Executions: {suggestion.total_executions?.toLocaleString() || '0'}
                                    </Typography>
                                </Paper>
                            ))}
                            {tableData.suggestions.length > 5 && (
                                <Typography variant="caption" color="text.secondary">
                                    ... and {tableData.suggestions.length - 5} more suggestions
                                </Typography>
                            )}
                        </AccordionDetails>
                    </Accordion>
                ))}

                <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                    <Button
                        variant="outlined"
                        color="primary"
                        onClick={handleGenerateComparativePipelines}
                        disabled={loading}
                    >
                        {loading ? 'Generating...' : 'Generate Comparative Validations'}
                    </Button>
                    <Button
                        variant="contained"
                        onClick={() => setActiveStep(2)}
                    >
                        Continue to Selection
                    </Button>
                </Box>

                {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

                <Alert severity="info" sx={{ mt: 2 }}>
                    <Typography variant="body2">
                        <strong>Comparative Validations:</strong> Automatically generates pipeline validations that run
                        the same queries from your Query Store on both SQL Server and Snowflake and compare the results.
                        This bypasses manual selection and creates direct query-based validators.
                    </Typography>
                </Alert>
            </Box>
        );
    };

    const renderSelectionStep = () => {
        if (!currentWorkload?.analysis) return null;

        const { tables } = currentWorkload.analysis;
        let allValidations: Array<{ key: string; suggestion: ValidationSuggestion; tableName: string }> = [];

        Object.entries(tables).forEach(([tableName, tableData]) => {
            tableData.suggestions.forEach((suggestion, idx) => {
                allValidations.push({
                    key: `${tableName}_${idx}`,
                    suggestion,
                    tableName
                });
            });
        });

        return (
            <Box>
                <Typography variant="h6" gutterBottom>
                    Select Validations to Generate
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                    Choose which validations you want to include in your pipeline.
                    High confidence validations are recommended.
                </Typography>

                <Paper sx={{ p: 2, mb: 2, bgcolor: 'info.light' }}>
                    <Typography variant="body2">
                        {selectedValidations.size} of {allValidations.length} validations selected
                    </Typography>
                </Paper>

                <Button
                    variant="outlined"
                    size="small"
                    onClick={() => {
                        const highConf = allValidations
                            .filter(v => v.suggestion.confidence >= 0.8)
                            .map(v => v.key);
                        setSelectedValidations(new Set(highConf));
                    }}
                    sx={{ mb: 2, mr: 1 }}
                >
                    Select High Confidence
                </Button>
                <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setSelectedValidations(new Set(allValidations.map(v => v.key)))}
                    sx={{ mb: 2, mr: 1 }}
                >
                    Select All
                </Button>
                <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setSelectedValidations(new Set())}
                    sx={{ mb: 2 }}
                >
                    Clear All
                </Button>

                {allValidations.map(({ key, suggestion, tableName }) => (
                    <Paper key={key} sx={{ p: 2, mb: 1 }}>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={selectedValidations.has(key)}
                                    onChange={() => handleValidationToggle(key)}
                                />
                            }
                            label={
                                <Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                            {tableName} - {suggestion.validator_name}
                                        </Typography>
                                        <Chip
                                            label={`${(suggestion.confidence * 100).toFixed(0)}%`}
                                            color={getConfidenceColor(suggestion.confidence)}
                                            size="small"
                                        />
                                    </Box>
                                    <Typography variant="caption" color="text.secondary">
                                        {suggestion.reason}
                                    </Typography>
                                </Box>
                            }
                        />
                    </Paper>
                ))}

                <Button
                    variant="contained"
                    onClick={() => setActiveStep(3)}
                    disabled={selectedValidations.size === 0}
                    sx={{ mt: 2 }}
                >
                    Generate Pipelines ({selectedValidations.size} validations)
                </Button>
            </Box>
        );
    };

    const renderGenerateStep = () => {
        if (!generationResult) {
            return (
                <Paper sx={{ p: 4, textAlign: 'center' }}>
                    <CheckCircle sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
                    <Typography variant="h5" gutterBottom>
                        Ready to Generate Pipelines
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                        {selectedValidations.size} validations selected
                    </Typography>

                    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                    <Button
                        variant="contained"
                        size="large"
                        onClick={handleGeneratePipelines}
                        disabled={loading}
                        sx={{ mt: 2, mb: 2 }}
                    >
                        {loading ? 'Generating...' : 'Generate Pipeline Files'}
                    </Button>

                    {loading && <CircularProgress sx={{ display: 'block', mx: 'auto', mt: 2 }} />}

                    <Button variant="outlined" onClick={() => setActiveStep(0)} sx={{ mt: 2 }}>
                        Start Over
                    </Button>
                </Paper>
            );
        }

        // Show generation results
        return (
            <Box>
                <Alert severity="success" sx={{ mb: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        {generationResult.message}
                    </Typography>
                    <Typography variant="body2">
                        Generated {generationResult.total_tables} pipeline file(s) with {generationResult.total_validations} total validations
                    </Typography>
                </Alert>

                {/* Pipeline Files Summary */}
                <Typography variant="h6" gutterBottom>
                    <Description sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Generated Pipeline Files
                </Typography>

                {Object.entries(generationResult.pipeline_files || {}).map(([tableName, fileInfo]: [string, any]) => (
                    <Card key={tableName} sx={{ mb: 2 }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                                <Box>
                                    <Typography variant="h6">{tableName}</Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        {fileInfo.filename}
                                    </Typography>
                                </Box>
                                <Chip
                                    label={`${fileInfo.validation_count} validations`}
                                    color="primary"
                                    size="small"
                                />
                            </Box>

                            <Divider sx={{ my: 2 }} />

                            {/* YAML Preview */}
                            <Typography variant="subtitle2" gutterBottom>
                                Pipeline Preview:
                            </Typography>
                            <Paper sx={{ p: 2, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                                <pre style={{ margin: 0, fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                                    {fileInfo.yaml_content}
                                </pre>
                            </Paper>

                            {/* Download and Save Buttons */}
                            <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                                <Button
                                    variant="outlined"
                                    size="small"
                                    onClick={() => {
                                        const blob = new Blob([fileInfo.yaml_content], { type: 'text/yaml' });
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = fileInfo.filename;
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                        URL.revokeObjectURL(url);
                                    }}
                                >
                                    Download
                                </Button>
                            </Box>
                        </CardContent>
                    </Card>
                ))}

                {/* Summary */}
                <Paper sx={{ p: 2, mt: 3, bgcolor: 'info.light' }}>
                    <Typography variant="body2">
                        <strong>Summary:</strong> Generated {generationResult.total_tables} pipeline file(s)
                        at {new Date(generationResult.generated_at).toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                        Files saved to: backend/data/pipelines/
                    </Typography>
                </Paper>

                <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSaveToProject}
                        disabled={loading}
                    >
                        {loading ? 'Saving...' : 'Save All to Project'}
                    </Button>
                    <Button variant="outlined" onClick={() => {
                        setActiveStep(0);
                        setGenerationResult(null);
                        setSelectedValidations(new Set());
                        setCurrentWorkload(null);
                    }}>
                        Start New Workload
                    </Button>
                    <Button variant="outlined" onClick={() => setActiveStep(2)}>
                        Back to Selection
                    </Button>
                </Stack>

                {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
            </Box>
        );
    };

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Workload-Based Validation
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Upload Query Store workload and automatically generate validation pipelines based on actual query patterns
            </Typography>

            <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
                {steps.map((label) => (
                    <Step key={label}>
                        <StepLabel>{label}</StepLabel>
                    </Step>
                ))}
            </Stepper>

            {activeStep === 0 && renderUploadStep()}
            {activeStep === 1 && renderAnalysisStep()}
            {activeStep === 2 && renderSelectionStep()}
            {activeStep === 3 && renderGenerateStep()}
        </Box>
    );
}
