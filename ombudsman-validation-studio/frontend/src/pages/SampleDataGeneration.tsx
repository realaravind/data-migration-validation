import { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    TextField,
    Grid,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Alert,
    CircularProgress,
    Chip,
    List,
    ListItem,
    ListItemText,
    Divider,
    Paper
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';

interface Schema {
    name: string;
    description: string;
    dimensions: string[];
    facts: string[];
}

export default function SampleDataGeneration() {
    const [loading, setLoading] = useState(false);
    const [schemas, setSchemas] = useState<Schema[]>([]);
    const [selectedTarget, setSelectedTarget] = useState('both');
    const [numDimensions, setNumDimensions] = useState(3);
    const [numFacts, setNumFacts] = useState(2);
    const [rowsPerDim, setRowsPerDim] = useState(100);
    const [rowsPerFact, setRowsPerFact] = useState(500);
    const [brokenFkRate, setBrokenFkRate] = useState(0.05);
    const [generationResult, setGenerationResult] = useState<any>(null);
    const [jobStatus, setJobStatus] = useState<any>(null);
    const [selectedSchema, setSelectedSchema] = useState<string | null>(null);

    useEffect(() => {
        fetchSchemas();
    }, []);

    const fetchSchemas = async () => {
        try {
            const response = await fetch('http://localhost:8000/data/schemas');
            const data = await response.json();
            setSchemas(data.schemas || []);
        } catch (error) {
            console.error('Failed to fetch schemas:', error);
        }
    };

    const selectSchema = (schema: Schema) => {
        setSelectedSchema(schema.name);
        setNumDimensions(schema.dimensions.length);
        setNumFacts(schema.facts.length);
    };

    const generateData = async () => {
        setLoading(true);
        setGenerationResult(null);
        setJobStatus(null);

        try {
            const response = await fetch('http://localhost:8000/data/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    num_dimensions: numDimensions,
                    num_facts: numFacts,
                    rows_per_dim: rowsPerDim,
                    rows_per_fact: rowsPerFact,
                    broken_fk_rate: brokenFkRate,
                    target: selectedTarget,
                    seed: Math.floor(Math.random() * 100000)
                })
            });

            const result = await response.json();
            setGenerationResult(result);

            // Poll for job status
            if (result.job_id) {
                pollJobStatus(result.job_id);
            }
        } catch (error) {
            console.error('Failed to generate data:', error);
            setGenerationResult({ status: 'error', message: String(error) });
        }

        setLoading(false);
    };

    const pollJobStatus = async (jobId: string) => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`http://localhost:8000/data/status/${jobId}`);
                const status = await response.json();
                setJobStatus(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(interval);
                }
            } catch (error) {
                console.error('Failed to fetch job status:', error);
                clearInterval(interval);
            }
        }, 2000);
    };

    const clearData = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/data/clear', {
                method: 'DELETE'
            });
            const result = await response.json();
            alert(`Cleared ${result.tables_dropped?.length || 0} tables`);
        } catch (error) {
            console.error('Failed to clear data:', error);
            alert('Failed to clear data');
        }
        setLoading(false);
    };

    const downloadSampleWorkload = async () => {
        try {
            // Use selected schema or default to Retail
            const schema = selectedSchema || 'Retail';

            const response = await fetch(`http://localhost:8000/data/download-sample-workload?schema=${encodeURIComponent(schema)}`);
            if (!response.ok) {
                throw new Error('Failed to download sample workload');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${schema.toLowerCase()}_sample_workload.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Failed to download sample workload:', error);
            alert('Failed to download sample workload');
        }
    };

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Sample Data Generation
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Generate synthetic test data for dimensions and facts with customizable schemas
            </Typography>

            <Grid container spacing={3}>
                {/* Configuration Panel */}
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Generation Settings
                            </Typography>

                            <FormControl fullWidth sx={{ mb: 2 }}>
                                <InputLabel>Target Database</InputLabel>
                                <Select
                                    value={selectedTarget}
                                    label="Target Database"
                                    onChange={(e) => setSelectedTarget(e.target.value)}
                                >
                                    <MenuItem value="both">Both (SQL Server + Snowflake)</MenuItem>
                                    <MenuItem value="sqlserver">SQL Server Only</MenuItem>
                                    <MenuItem value="snowflake">Snowflake Only</MenuItem>
                                </Select>
                            </FormControl>

                            <TextField
                                fullWidth
                                label="Number of Dimensions"
                                type="number"
                                value={numDimensions}
                                onChange={(e) => setNumDimensions(parseInt(e.target.value))}
                                sx={{ mb: 2 }}
                                InputProps={{ inputProps: { min: 1, max: 10 } }}
                            />

                            <TextField
                                fullWidth
                                label="Number of Facts"
                                type="number"
                                value={numFacts}
                                onChange={(e) => setNumFacts(parseInt(e.target.value))}
                                sx={{ mb: 2 }}
                                InputProps={{ inputProps: { min: 1, max: 10 } }}
                            />

                            <TextField
                                fullWidth
                                label="Rows Per Dimension"
                                type="number"
                                value={rowsPerDim}
                                onChange={(e) => setRowsPerDim(parseInt(e.target.value))}
                                sx={{ mb: 2 }}
                                InputProps={{ inputProps: { min: 10, max: 10000 } }}
                            />

                            <TextField
                                fullWidth
                                label="Rows Per Fact"
                                type="number"
                                value={rowsPerFact}
                                onChange={(e) => setRowsPerFact(parseInt(e.target.value))}
                                sx={{ mb: 2 }}
                                InputProps={{ inputProps: { min: 10, max: 100000 } }}
                            />

                            <TextField
                                fullWidth
                                label="Broken Foreign Key Rate (0.0 - 1.0)"
                                type="number"
                                value={brokenFkRate}
                                onChange={(e) => setBrokenFkRate(parseFloat(e.target.value))}
                                sx={{ mb: 2 }}
                                InputProps={{ inputProps: { min: 0, max: 1, step: 0.01 } }}
                            />

                            <Box sx={{ display: 'flex', gap: 2 }}>
                                <Button
                                    variant="contained"
                                    onClick={generateData}
                                    disabled={loading}
                                    fullWidth
                                >
                                    {loading ? <CircularProgress size={24} /> : 'Generate Sample Data'}
                                </Button>
                                <Button
                                    variant="outlined"
                                    color="error"
                                    onClick={clearData}
                                    disabled={loading}
                                >
                                    Clear Data
                                </Button>
                            </Box>

                            {/* Generation Result */}
                            {generationResult && (
                                <Box sx={{ mt: 2 }}>
                                    <Alert severity={generationResult.status === 'pending' ? 'info' : 'success'}>
                                        {generationResult.message}
                                    </Alert>
                                </Box>
                            )}

                            {/* Job Status */}
                            {jobStatus && (
                                <Box sx={{ mt: 2 }}>
                                    <Typography variant="subtitle2" gutterBottom>
                                        Job Status:
                                    </Typography>
                                    <Chip
                                        label={jobStatus.status}
                                        color={
                                            jobStatus.status === 'completed' ? 'success' :
                                            jobStatus.status === 'failed' ? 'error' :
                                            jobStatus.status === 'running' ? 'warning' : 'default'
                                        }
                                        size="small"
                                    />
                                    {jobStatus.message && (
                                        <Typography variant="body2" sx={{ mt: 1 }}>
                                            {jobStatus.message}
                                        </Typography>
                                    )}
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Available Schemas */}
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Available Schema Templates
                            </Typography>

                            <List>
                                {schemas.map((schema, index) => (
                                    <Box key={index}>
                                        <ListItem
                                            sx={{
                                                cursor: 'pointer',
                                                bgcolor: selectedSchema === schema.name ? 'action.selected' : 'transparent',
                                                '&:hover': {
                                                    bgcolor: 'action.hover'
                                                },
                                                borderLeft: selectedSchema === schema.name ? '4px solid #1976d2' : 'none',
                                                transition: 'all 0.2s'
                                            }}
                                            onClick={() => selectSchema(schema)}
                                        >
                                            <ListItemText
                                                primary={
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                        <Typography variant="h6">
                                                            {schema.name}
                                                        </Typography>
                                                        {selectedSchema === schema.name && (
                                                            <Chip label="Selected" color="primary" size="small" />
                                                        )}
                                                    </Box>
                                                }
                                                secondary={
                                                    <>
                                                        <Typography variant="body2" color="text.secondary" paragraph>
                                                            {schema.description}
                                                        </Typography>
                                                        <Box sx={{ mt: 1 }}>
                                                            <Typography variant="caption" display="block">
                                                                <strong>Dimensions ({schema.dimensions.length}):</strong> {schema.dimensions.join(', ')}
                                                            </Typography>
                                                            <Typography variant="caption" display="block">
                                                                <strong>Facts ({schema.facts.length}):</strong> {schema.facts.join(', ')}
                                                            </Typography>
                                                        </Box>
                                                    </>
                                                }
                                            />
                                        </ListItem>
                                        {index < schemas.length - 1 && <Divider />}
                                    </Box>
                                ))}
                            </List>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Info Box */}
            <Box sx={{ mt: 3 }}>
                <Alert severity="info">
                    <Typography variant="body2">
                        <strong>How it works:</strong> Click on any schema template to auto-fill the dimension and fact counts.
                        The sample data generator creates realistic test data based on predefined schemas.
                        You can customize the number of dimensions, facts, and rows to generate.
                        The broken foreign key rate allows you to introduce data quality issues for testing validation rules.
                    </Typography>
                </Alert>
            </Box>

            {/* Sample Workload Download */}
            <Box sx={{ mt: 3 }}>
                <Card>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            Sample Workload for Testing
                        </Typography>
                        <Typography variant="body2" color="text.secondary" paragraph>
                            Download a comprehensive sample workload file that contains 30 diverse SQL queries
                            covering various scenarios including row counts, filters, joins, aggregations, and date operations.
                            The workload is automatically generated based on the schema template you select above.
                        </Typography>

                        <Alert severity={selectedSchema ? "success" : "info"} sx={{ mb: 2 }}>
                            <Typography variant="body2">
                                <strong>{selectedSchema ? `${selectedSchema} Schema:` : 'Select a schema template above for customized workload.'}</strong>
                                {selectedSchema && (
                                    <span> The sample workload will include 30 queries covering the {selectedSchema} dimensions and facts
                                    with row counts, WHERE filters, JOIN operations, aggregations (SUM, AVG, COUNT, MIN, MAX),
                                    date filters, ORDER BY, GROUP BY with HAVING, DISTINCT, NULL checks, and subqueries.</span>
                                )}
                            </Typography>
                        </Alert>

                        <Button
                            variant="contained"
                            color="primary"
                            startIcon={<DownloadIcon />}
                            onClick={downloadSampleWorkload}
                            size="large"
                        >
                            Download Sample Workload (JSON)
                        </Button>

                        <Typography variant="caption" display="block" sx={{ mt: 2 }} color="text.secondary">
                            After downloading, you can upload this workload file in the Workload Analysis page to
                            automatically generate validation suggestions for your sample data.
                        </Typography>
                    </CardContent>
                </Card>
            </Box>
        </Box>
    );
}
