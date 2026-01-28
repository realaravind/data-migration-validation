import React, { useState, useEffect } from 'react';
import {
    Box,
    Button,
    Card,
    CardContent,
    Tabs,
    Tab,
    Typography,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Checkbox,
    FormControlLabel,
    FormGroup,
    Chip,
    Alert,
    CircularProgress,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Paper,
    Divider,
    IconButton,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SaveIcon from '@mui/icons-material/Save';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CodeIcon from '@mui/icons-material/Code';
import ChatIcon from '@mui/icons-material/Chat';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import QuerySuggestions from '../components/QuerySuggestions';
import * as yaml from 'js-yaml';

interface SuggestedCheck {
    category: string;
    pipeline_type: string;
    checks: string[];
    reason: string;
    priority: string;
    applicable_columns?: any;
    examples?: string[];
    business_rules?: string[];
    aggregation_grains?: string[];
}

export default function PipelineBuilder() {
    const [currentProject, setCurrentProject] = useState<any>(null);
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Quick Build State
    const [selectedTable, setSelectedTable] = useState('');
    const [availableTables, setAvailableTables] = useState<any[]>([]);
    const [suggestedChecks, setSuggestedChecks] = useState<SuggestedCheck[]>([]);
    const [selectedChecks, setSelectedChecks] = useState<{[key: string]: boolean}>({});
    const [pipelineYaml, setPipelineYaml] = useState('');

    // Natural Language State
    const [nlDescription, setNlDescription] = useState('');
    const [nlDetectedChecks, setNlDetectedChecks] = useState<any[]>([]);
    const [nlPipelineYaml, setNlPipelineYaml] = useState('');

    // Advanced State
    const [advancedYaml, setAdvancedYaml] = useState('');

    // Pipeline Management State
    const [savedPipelines, setSavedPipelines] = useState<any[]>([]);
    const [pipelineName, setPipelineName] = useState('');
    const [pipelineDescription, setPipelineDescription] = useState('');
    const [showSaveDialog, setShowSaveDialog] = useState(false);
    const [showLoadDialog, setShowLoadDialog] = useState(false);

    // Query Suggestions State
    const [showQuerySuggestions, setShowQuerySuggestions] = useState(false);

    // Load active project from backend API (NOT sessionStorage)
    useEffect(() => {
        const loadActiveProject = async () => {
            try {
                const token = localStorage.getItem('auth_token');
                const headers: any = {};
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }

                // Get active project from backend
                const activeResponse = await fetch(__API_URL__ + '/projects/active', { headers });
                const activeData = await activeResponse.json();

                if (activeResponse.ok && activeData.active_project) {
                    const projectId = activeData.active_project.project_id;

                    // Get full project with config
                    const projectResponse = await fetch(`${__API_URL__}/projects/${projectId}`, { headers });
                    const projectData = await projectResponse.json();

                    if (projectResponse.ok && projectData.config) {
                        setCurrentProject({
                            ...activeData.active_project,
                            config: projectData.config
                        });
                        console.log('[PipelineBuilder] Loaded active project:', projectId);
                    }
                }
            } catch (err) {
                console.error('[PipelineBuilder] Failed to load active project:', err);
            }
        };

        loadActiveProject();
    }, []);

    // Load available tables from current project (Snowflake target tables)
    useEffect(() => {
        const loadTables = async () => {
            if (!currentProject?.project_id) {
                console.log('PipelineBuilder - No project ID available');
                return;
            }

            try {
                // Fetch project config from API directly (same pattern as loadSavedPipelines)
                const token = localStorage.getItem('auth_token');
                const headers: any = {};
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }

                const response = await fetch(`${__API_URL__}/projects/${currentProject.project_id}`, { headers });
                const data = await response.json();

                if (!response.ok || !data.config) {
                    console.log('PipelineBuilder - No config available from API');
                    setAvailableTables([]);
                    return;
                }

                const config = data.config;
                const tables: any[] = [];

                console.log('PipelineBuilder - Loading tables from API config:', {
                    hasConfig: !!config,
                    hasColumnMappings: !!config.column_mappings,
                    hasTables: !!config.tables,
                    hasTablesSnow: !!config.tables?.snow,
                    configKeys: Object.keys(config)
                });

                // Option 1: Use column_mappings if available (has both SQL and Snowflake table names)
                if (config.column_mappings) {
                    console.log('Using column_mappings:', Object.keys(config.column_mappings));
                    const mappings = config.column_mappings;
                    for (const [sqlTable, mapping] of Object.entries(mappings)) {
                        if (mapping && typeof mapping === 'object' && (mapping as any).target_table) {
                            tables.push({
                                sql_server_table: sqlTable,
                                snowflake_table: (mapping as any).target_table,
                                sql_columns: config.tables?.sql?.[sqlTable] || {},
                                snowflake_columns: config.tables?.snow?.[(mapping as any).target_table] || {}
                            });
                        }
                    }
                }
                // Option 2: Fallback to tables.snow if column_mappings not available
                else if (config.tables?.snow) {
                    console.log('Using tables.snow:', Object.keys(config.tables.snow));
                    const snowTables = config.tables.snow;
                    for (const [tableName, columns] of Object.entries(snowTables)) {
                        tables.push({
                            sql_server_table: tableName,  // Use same name as placeholder
                            snowflake_table: tableName,
                            sql_columns: {},
                            snowflake_columns: columns
                        });
                    }
                }

                console.log('PipelineBuilder - Loaded tables from API:', tables.length, tables.map(t => t.snowflake_table));
                setAvailableTables(tables);
            } catch (err) {
                console.error('PipelineBuilder - Failed to load tables from API:', err);
                setAvailableTables([]);
            }
        };

        loadTables();
    }, [currentProject?.project_id]);

    // Load saved pipelines for current project
    useEffect(() => {
        if (currentProject && currentProject.project_id) {
            loadSavedPipelines();
        }
    }, [currentProject]);

    // Load saved pipelines
    const loadSavedPipelines = async () => {
        if (!currentProject?.project_id) return;

        try {
            // Get auth token
            const token = localStorage.getItem('auth_token');
            const headers: any = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${__API_URL__}/pipelines/custom/project/${currentProject.project_id}`, { headers });
            const data = await response.json();

            if (response.ok) {
                setSavedPipelines(data.pipelines || []);
            }
        } catch (err) {
            console.error('Failed to load saved pipelines:', err);
        }
    };

    // Load a specific pipeline
    const handleLoadPipeline = async (pipelineName: string) => {
        if (!currentProject?.project_id) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${__API_URL__}/pipelines/custom/project/${currentProject.project_id}/${pipelineName}`
            );
            const data = await response.json();

            if (response.ok) {
                // Load into appropriate tab based on current tab
                if (activeTab === 0) {
                    setPipelineYaml(data.content);
                } else if (activeTab === 1) {
                    setNlPipelineYaml(data.content);
                } else {
                    setAdvancedYaml(data.content);
                }

                // Parse YAML to extract table name and set it in dropdown
                try {
                    const parsedYaml: any = yaml.load(data.content);
                    if (parsedYaml?.pipeline?.target?.table) {
                        setSelectedTable(parsedYaml.pipeline.target.table);
                    }
                } catch (parseError) {
                    console.warn('Could not parse YAML to extract table name:', parseError);
                }

                setPipelineName(pipelineName);
                setPipelineDescription(data.metadata?.description || '');
                setShowLoadDialog(false);
                setSuccess(`Pipeline '${pipelineName}' loaded successfully!`);
            } else {
                setError(data.detail || 'Failed to load pipeline');
            }
        } catch (err) {
            setError(`Error loading pipeline: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Delete a pipeline
    const handleDeletePipeline = async (pipelineName: string) => {
        if (!currentProject?.project_id) return;
        if (!confirm(`Are you sure you want to delete pipeline '${pipelineName}'?`)) return;

        setLoading(true);

        try {
            // Get auth token
            const token = localStorage.getItem('auth_token');
            console.log('[DELETE_PIPELINE] Token found:', !!token);
            const headers: any = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            console.log('[DELETE_PIPELINE] Deleting:', `${currentProject.project_id}/${pipelineName}`);
            console.log('[DELETE_PIPELINE] Headers:', headers);

            const response = await fetch(
                `${__API_URL__}/pipelines/custom/project/${currentProject.project_id}/${pipelineName}`,
                { method: 'DELETE', headers }
            );

            if (response.ok) {
                setSuccess(`Pipeline '${pipelineName}' deleted successfully!`);
                await loadSavedPipelines();
            } else {
                const data = await response.json();
                setError(data.detail || 'Failed to delete pipeline');
            }
        } catch (err) {
            setError(`Error deleting pipeline: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Quick Build: Analyze table and suggest validations
    const handleAnalyzeTable = async () => {
        if (!selectedTable) {
            setError('Please select a table first');
            return;
        }

        setLoading(true);
        setError(null);
        setSuggestedChecks([]);

        try {
            // Get table metadata - match by Snowflake table name (target)
            const tableMetadata = availableTables.find(t =>
                t.snowflake_table === selectedTable
            );

            if (!tableMetadata) {
                setError('Table metadata not found');
                return;
            }

            // Extract columns from Snowflake (target) - these are the columns that exist in the target database
            const snowflakeColumns = tableMetadata.snowflake_columns || {};
            const columns = Object.keys(snowflakeColumns).map(colName => ({
                name: colName,
                type: snowflakeColumns[colName]
            }));

            // Extract relationships - look for relationships where this table is the fact table
            // Use Snowflake relationships for Snowflake pipelines, SQL relationships for SQL pipelines
            let relationships: any[] = [];
            const databaseType = 'snowflake'; // Using Snowflake as target database

            // Load the appropriate relationship file based on database type
            if (databaseType === 'snowflake') {
                // Use Snowflake relationships (uppercase table names)
                if (currentProject?.config?.snow_relationships?.relationships) {
                    relationships = currentProject.config.snow_relationships.relationships;
                }
            } else {
                // Use SQL Server relationships (lowercase table names)
                if (currentProject?.config?.sql_relationships?.relationships) {
                    relationships = currentProject.config.sql_relationships.relationships;
                }
            }

            // Fallback to old relationships format if no database-specific relationships found
            if (relationships.length === 0) {
                if (Array.isArray(currentProject?.config?.relationships)) {
                    relationships = currentProject.config.relationships;
                } else if (currentProject?.config?.relationships?.relationships) {
                    relationships = currentProject.config.relationships.relationships;
                }
            }

            console.log('[PIPELINE_BUILDER] Database type:', databaseType);
            console.log('[PIPELINE_BUILDER] All relationships:', relationships);
            console.log('[PIPELINE_BUILDER] Selected table:', selectedTable);
            console.log('[PIPELINE_BUILDER] SQL Server table:', tableMetadata.sql_server_table);

            // Case-insensitive matching for fact_table
            const tableRelationships = relationships.filter((rel: any) => {
                const factTable = rel.fact_table?.toLowerCase();
                const selected = selectedTable?.toLowerCase();
                const sqlTable = tableMetadata.sql_server_table?.toLowerCase();
                return factTable === selected || factTable === sqlTable;
            });

            console.log('[PIPELINE_BUILDER] Filtered relationships:', tableRelationships);

            // Call intelligent suggest API
            const response = await fetch(__API_URL__ + '/pipelines/suggest-for-fact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fact_table: selectedTable,  // Snowflake table name
                    fact_schema: 'PUBLIC',  // Default Snowflake schema
                    database_type: 'snowflake',  // Changed to snowflake since we're using target
                    columns: columns,
                    relationships: tableRelationships
                })
            });

            const data = await response.json();

            if (response.ok) {
                console.log('=== API Response ===');
                console.log('Analysis:', data.analysis);
                console.log('Suggested checks count:', data.suggested_checks?.length);
                console.log('First 2 checks:', data.suggested_checks?.slice(0, 2));

                setSuggestedChecks(data.suggested_checks || []);
                setPipelineYaml(data.pipeline_yaml || '');

                // Initialize all checks as selected
                const initialSelection: {[key: string]: boolean} = {};
                data.suggested_checks.forEach((_check: SuggestedCheck, idx: number) => {
                    initialSelection[`check_${idx}`] = true;
                });
                setSelectedChecks(initialSelection);

                setSuccess(`Found ${data.total_validations} suggested validations!`);
            } else {
                setError(data.detail || 'Failed to analyze table');
            }
        } catch (err) {
            setError(`Error analyzing table: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Handle Query Suggestions selection
    const handleQuerySuggestionsSelect = (queries: any[]) => {
        const currentYaml = pipelineYaml || '';

        // Parse current YAML and inject custom_queries in the correct location (inside pipeline section)
        const parsed = yaml.load(currentYaml) as any;
        const pipelineSection = parsed.pipeline || {};

        // Convert queries to proper format
        const customQueries = queries.map(query => ({
            name: query.name,
            comparison_type: query.comparison_type,
            ...(query.tolerance && { tolerance: query.tolerance }),
            ...(query.limit && { limit: query.limit }),
            sql_query: query.sql_query,
            snow_query: query.snow_query
        }));

        // Add custom_queries to pipeline section (NOT at root level!)
        pipelineSection.custom_queries = customQueries;
        parsed.pipeline = pipelineSection;

        // Convert back to YAML
        const updatedYaml = yaml.dump(parsed);
        setPipelineYaml(updatedYaml);
        setSuccess(`Added ${queries.length} custom queries to pipeline!`);
    };

    // Natural Language: Generate pipeline
    const handleGenerateFromNL = async () => {
        if (!nlDescription.trim()) {
            setError('Please describe what you want to validate');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(__API_URL__ + '/pipelines/create-from-nl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    description: nlDescription,
                    context: {
                        sql_database: currentProject?.sql_database,
                        sql_schema: currentProject?.sql_schemas?.[0],
                        snowflake_database: currentProject?.snowflake_database,
                        snowflake_schema: currentProject?.snowflake_schemas?.[0]
                    }
                })
            });

            const data = await response.json();

            if (response.ok) {
                if (data.status === 'unclear') {
                    setError(data.message);
                } else {
                    setNlDetectedChecks(data.detected_intent?.checks || []);
                    setNlPipelineYaml(data.pipeline_yaml || '');
                    setSuccess('Pipeline generated successfully!');
                }
            } else {
                setError(data.detail || 'Failed to generate pipeline');
            }
        } catch (err) {
            setError(`Error generating pipeline: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Save pipeline - Open dialog
    const handleSavePipeline = async () => {
        const yamlToSave = activeTab === 0 ? pipelineYaml : activeTab === 1 ? nlPipelineYaml : advancedYaml;

        if (!yamlToSave) {
            setError('No pipeline to save');
            return;
        }

        setShowSaveDialog(true);
    };

    // Confirm save pipeline
    const handleConfirmSave = async () => {
        if (!currentProject?.project_id) {
            setError('No project selected');
            return;
        }

        if (!pipelineName.trim()) {
            setError('Please enter a pipeline name');
            return;
        }

        const yamlToSave = activeTab === 0 ? pipelineYaml : activeTab === 1 ? nlPipelineYaml : advancedYaml;

        setLoading(true);
        setError(null);

        try {
            // Get auth token
            const token = localStorage.getItem('auth_token');
            const headers: any = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(__API_URL__ + '/pipelines/custom/save', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    project_id: currentProject.project_id,
                    pipeline_name: pipelineName,
                    pipeline_yaml: yamlToSave,
                    description: pipelineDescription,
                    tags: []
                })
            });

            const data = await response.json();

            if (response.ok) {
                setSuccess(data.message || 'Pipeline saved successfully!');
                setShowSaveDialog(false);
                await loadSavedPipelines();
                // Don't clear the name/description - user might want to update
            } else {
                setError(data.detail || 'Failed to save pipeline');
            }
        } catch (err) {
            setError(`Error saving pipeline: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Execute pipeline
    const handleExecutePipeline = async () => {
        const yamlToExecute = activeTab === 0 ? pipelineYaml : activeTab === 1 ? nlPipelineYaml : advancedYaml;

        if (!yamlToExecute) {
            setError('No pipeline to execute');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // Get auth token
            const token = localStorage.getItem('auth_token');
            const headers: any = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(__API_URL__ + '/pipelines/execute', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    pipeline_yaml: yamlToExecute,
                    pipeline_name: selectedTable || 'custom_pipeline',
                    project_id: currentProject?.project_id || null
                })
            });

            const data = await response.json();

            if (response.ok) {
                setSuccess(`Pipeline execution started! Run ID: ${data.run_id}`);
            } else {
                setError(data.detail || 'Failed to execute pipeline');
            }
        } catch (err) {
            setError(`Error executing pipeline: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    // Get priority color
    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'CRITICAL': return 'error';
            case 'HIGH': return 'warning';
            case 'MEDIUM': return 'info';
            default: return 'default';
        }
    };

    // Copy YAML to clipboard
    const handleCopyYaml = (yaml: string) => {
        navigator.clipboard.writeText(yaml);
        setSuccess('YAML copied to clipboard!');
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4">Pipeline Builder</Typography>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                        variant="outlined"
                        startIcon={<FolderOpenIcon />}
                        onClick={() => setShowLoadDialog(true)}
                        disabled={loading || !currentProject}
                    >
                        Load Pipeline
                    </Button>
                    <Button
                        variant="outlined"
                        startIcon={<SaveIcon />}
                        onClick={handleSavePipeline}
                        disabled={loading || !currentProject}
                    >
                        Save Pipeline
                    </Button>
                </Box>
            </Box>

            {!currentProject && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Please select a project first to use the Pipeline Builder
                </Alert>
            )}

            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {success && (
                <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
                    {success}
                </Alert>
            )}

            <Paper sx={{ mb: 3 }}>
                <Tabs value={activeTab} onChange={(_e, newValue) => setActiveTab(newValue)}>
                    <Tab icon={<AutoFixHighIcon />} label="Quick Build" iconPosition="start" />
                    <Tab icon={<ChatIcon />} label="Natural Language" iconPosition="start" />
                    <Tab icon={<CodeIcon />} label="Advanced YAML" iconPosition="start" />
                </Tabs>
            </Paper>

            {/* TAB 1: Quick Build */}
            {activeTab === 0 && (
                <Box>
                    {availableTables.length === 0 && currentProject && (
                        <Alert severity="info" sx={{ mb: 3 }}>
                            <Typography variant="body2" fontWeight="medium">No tables found in this project</Typography>
                            <Typography variant="body2" sx={{ mt: 1 }}>
                                Please complete the following steps first:
                            </Typography>
                            <Typography variant="body2" component="div" sx={{ mt: 1 }}>
                                1. Go to <strong>Projects</strong> and open your project<br/>
                                2. Complete <strong>Database Mapping</strong> to extract and map tables<br/>
                                3. Return here to build pipelines for your fact tables
                            </Typography>
                        </Alert>
                    )}

                    <Card sx={{ mb: 3 }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <FormControl sx={{ flex: 1, minWidth: 250 }}>
                                    <InputLabel>Select Table</InputLabel>
                                    <Select
                                        value={selectedTable}
                                        onChange={(e) => setSelectedTable(e.target.value)}
                                        label="Select Table"
                                        disabled={availableTables.length === 0}
                                    >
                                        {availableTables.length === 0 ? (
                                            <MenuItem disabled value="">
                                                No tables found. Please complete Database Mapping first.
                                            </MenuItem>
                                        ) : (
                                            availableTables.map((table) => (
                                                <MenuItem key={table.snowflake_table} value={table.snowflake_table}>
                                                    {table.snowflake_table} {table.sql_server_table !== table.snowflake_table && `(← ${table.sql_server_table})`}
                                                </MenuItem>
                                            ))
                                        )}
                                    </Select>
                                </FormControl>

                                <Button
                                    variant="contained"
                                    startIcon={<AutoFixHighIcon />}
                                    onClick={handleAnalyzeTable}
                                    disabled={!selectedTable || loading}
                                    sx={{ whiteSpace: 'nowrap' }}
                                >
                                    {loading ? <CircularProgress size={24} /> : 'Analyze & Suggest'}
                                </Button>

                                <Button
                                    variant="outlined"
                                    startIcon={<AutoAwesomeIcon />}
                                    onClick={() => setShowQuerySuggestions(true)}
                                    disabled={!selectedTable || loading}
                                    sx={{ whiteSpace: 'nowrap' }}
                                >
                                    Custom Queries
                                </Button>
                            </Box>
                        </CardContent>
                    </Card>

                    {suggestedChecks.length > 0 && (
                        <Card sx={{ mb: 3 }}>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6">
                                        Suggested Validations ({suggestedChecks.reduce((sum, check) => sum + check.checks.length, 0)})
                                    </Typography>
                                    <Chip
                                        label={`${Object.values(selectedChecks).filter(Boolean).length} Selected`}
                                        color="primary"
                                    />
                                </Box>

                                {suggestedChecks.map((suggestion, idx) => (
                                    <Accordion key={idx} defaultExpanded={suggestion.priority === 'CRITICAL'}>
                                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                                                <Checkbox
                                                    checked={selectedChecks[`check_${idx}`] || false}
                                                    onChange={(e) => {
                                                        const checkKey = `check_${idx}`;
                                                        const newValue = e.target.checked;
                                                        setSelectedChecks(prev => ({
                                                            ...prev,
                                                            [checkKey]: newValue
                                                        }));
                                                    }}
                                                    onClick={(e) => e.stopPropagation()}
                                                />
                                                <Typography sx={{ flexGrow: 1 }}>
                                                    {suggestion.category}
                                                </Typography>
                                                <Chip
                                                    label={suggestion.priority}
                                                    color={getPriorityColor(suggestion.priority) as any}
                                                    size="small"
                                                />
                                                <Chip
                                                    label={`${suggestion.checks.length} checks`}
                                                    size="small"
                                                    variant="outlined"
                                                />
                                            </Box>
                                        </AccordionSummary>
                                        <AccordionDetails>
                                            <Typography variant="body2" color="text.secondary" paragraph>
                                                {suggestion.reason}
                                            </Typography>

                                            <FormGroup>
                                                {suggestion.checks.map((check, checkIdx) => (
                                                    <FormControlLabel
                                                        key={checkIdx}
                                                        control={<Checkbox defaultChecked size="small" />}
                                                        label={<Typography variant="body2">{check}</Typography>}
                                                    />
                                                ))}
                                            </FormGroup>

                                            {suggestion.applicable_columns && (
                                                <Box sx={{ mt: 2 }}>
                                                    <Typography variant="caption" color="text.secondary" display="block" fontWeight="bold">
                                                        Applicable Columns:
                                                    </Typography>
                                                    {Object.entries(suggestion.applicable_columns).map(([key, cols]: [string, any]) => (
                                                        Array.isArray(cols) && cols.length > 0 && (
                                                            <Box key={key} sx={{ mt: 1 }}>
                                                                <Typography variant="caption" color="primary" display="block">
                                                                    {key.replace(/_/g, ' ').toUpperCase()}:
                                                                </Typography>
                                                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                                                    {cols.map((col: string) => (
                                                                        <Chip
                                                                            key={col}
                                                                            label={col}
                                                                            size="small"
                                                                            variant="outlined"
                                                                            color={key.includes('additive') ? 'error' : key.includes('non_additive') ? 'warning' : 'default'}
                                                                        />
                                                                    ))}
                                                                </Box>
                                                            </Box>
                                                        )
                                                    ))}
                                                </Box>
                                            )}

                                            {suggestion.business_rules && suggestion.business_rules.length > 0 && (
                                                <Box sx={{ mt: 2, p: 1.5, bgcolor: '#e3f2fd', borderRadius: 1 }}>
                                                    <Typography variant="caption" color="primary" display="block" fontWeight="bold">
                                                        Business Rules:
                                                    </Typography>
                                                    {suggestion.business_rules.map((rule: string, ruleIdx: number) => (
                                                        <Typography key={ruleIdx} variant="body2" sx={{ mt: 0.5 }} color="text.primary">
                                                            ✓ {rule}
                                                        </Typography>
                                                    ))}
                                                </Box>
                                            )}

                                            {suggestion.examples && suggestion.examples.length > 0 && (
                                                <Box sx={{ mt: 2 }}>
                                                    <Typography variant="caption" color="text.secondary" display="block" fontWeight="bold">
                                                        Examples:
                                                    </Typography>
                                                    {suggestion.examples.map((example, exIdx) => (
                                                        <Typography key={exIdx} variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>
                                                            • {example}
                                                        </Typography>
                                                    ))}
                                                </Box>
                                            )}

                                            {suggestion.aggregation_grains && suggestion.aggregation_grains.length > 0 && (
                                                <Box sx={{ mt: 2 }}>
                                                    <Typography variant="caption" color="text.secondary" display="block" fontWeight="bold">
                                                        Time Grains:
                                                    </Typography>
                                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                                        {suggestion.aggregation_grains.map((grain: string, gIdx: number) => (
                                                            <Chip key={gIdx} label={grain} size="small" color="info" variant="outlined" />
                                                        ))}
                                                    </Box>
                                                </Box>
                                            )}
                                        </AccordionDetails>
                                    </Accordion>
                                ))}
                            </CardContent>
                        </Card>
                    )}

                    {pipelineYaml && (
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6">
                                        Pipeline Preview
                                    </Typography>
                                    <Button
                                        size="small"
                                        startIcon={<ContentCopyIcon />}
                                        onClick={() => handleCopyYaml(pipelineYaml)}
                                        variant="outlined"
                                    >
                                        Copy YAML
                                    </Button>
                                </Box>
                                <Paper
                                    sx={{
                                        p: 2,
                                        bgcolor: '#1e1e1e',
                                        maxHeight: 500,
                                        overflow: 'auto',
                                        border: '1px solid #333',
                                        borderRadius: 1
                                    }}
                                >
                                    <pre style={{
                                        margin: 0,
                                        fontSize: '13px',
                                        lineHeight: '1.6',
                                        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                        color: '#d4d4d4',
                                        whiteSpace: 'pre',
                                        textAlign: 'left',
                                        overflowX: 'auto'
                                    }}>
{pipelineYaml}
                                    </pre>
                                </Paper>
                            </CardContent>
                        </Card>
                    )}
                </Box>
            )}

            {/* TAB 2: Natural Language */}
            {activeTab === 1 && (
                <Box>
                    <Card sx={{ mb: 3 }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Describe What You Want to Validate
                            </Typography>

                            <Alert severity="info" sx={{ mb: 2 }}>
                                <Typography variant="body2">
                                    <strong>Examples:</strong><br/>
                                    • "Validate that total sales amount matches between SQL and Snowflake"<br/>
                                    • "Check for orphaned product IDs in the sales fact table"<br/>
                                    • "Ensure no gaps in daily sales data for 2024"
                                </Typography>
                            </Alert>

                            <TextField
                                fullWidth
                                multiline
                                rows={4}
                                value={nlDescription}
                                onChange={(e) => setNlDescription(e.target.value)}
                                placeholder="Describe the validations you need in plain English..."
                                sx={{ mb: 2 }}
                            />

                            <Button
                                variant="contained"
                                startIcon={<ChatIcon />}
                                onClick={handleGenerateFromNL}
                                disabled={loading || !nlDescription.trim()}
                                fullWidth
                                size="large"
                            >
                                {loading ? <CircularProgress size={24} /> : 'Generate Pipeline from Description'}
                            </Button>
                        </CardContent>
                    </Card>

                    {nlDetectedChecks.length > 0 && (
                        <Card sx={{ mb: 3 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom>
                                    Detected Checks ({nlDetectedChecks.length})
                                </Typography>

                                {nlDetectedChecks.map((check, idx) => (
                                    <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                                        <CheckCircleIcon color="success" />
                                        <Box>
                                            <Typography variant="body1" fontWeight="medium">
                                                {check.check}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                {check.reason}
                                            </Typography>
                                        </Box>
                                        <Chip label={check.type} size="small" sx={{ ml: 'auto' }} />
                                    </Box>
                                ))}
                            </CardContent>
                        </Card>
                    )}

                    {nlPipelineYaml && (
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6">
                                        Generated Pipeline
                                    </Typography>
                                    <Button
                                        size="small"
                                        startIcon={<ContentCopyIcon />}
                                        onClick={() => handleCopyYaml(nlPipelineYaml)}
                                        variant="outlined"
                                    >
                                        Copy YAML
                                    </Button>
                                </Box>
                                <Paper
                                    sx={{
                                        p: 2,
                                        bgcolor: '#1e1e1e',
                                        maxHeight: 500,
                                        overflow: 'auto',
                                        border: '1px solid #333',
                                        borderRadius: 1
                                    }}
                                >
                                    <pre style={{
                                        margin: 0,
                                        fontSize: '13px',
                                        lineHeight: '1.6',
                                        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                        color: '#d4d4d4',
                                        whiteSpace: 'pre',
                                        textAlign: 'left',
                                        overflowX: 'auto'
                                    }}>
{nlPipelineYaml}
                                    </pre>
                                </Paper>
                            </CardContent>
                        </Card>
                    )}
                </Box>
            )}

            {/* TAB 3: Advanced YAML */}
            {activeTab === 2 && (
                <Box>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography variant="h6">
                                    Manual YAML Editor
                                </Typography>
                                <Button
                                    size="small"
                                    startIcon={<ContentCopyIcon />}
                                    onClick={() => handleCopyYaml(advancedYaml)}
                                    variant="outlined"
                                    disabled={!advancedYaml}
                                >
                                    Copy YAML
                                </Button>
                            </Box>

                            <Alert severity="info" sx={{ mb: 2 }}>
                                <Typography variant="body2">
                                    Write your pipeline YAML manually or paste an existing pipeline to customize it.
                                </Typography>
                            </Alert>

                            <TextField
                                fullWidth
                                multiline
                                rows={20}
                                value={advancedYaml}
                                onChange={(e) => setAdvancedYaml(e.target.value)}
                                placeholder="pipeline:\n  name: My Custom Pipeline\n  steps:\n    - name: validate_schema\n      type: schema\n      checks:\n        - validate_schema_columns"
                                sx={{
                                    '& .MuiInputBase-root': {
                                        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                                        fontSize: '13px',
                                        lineHeight: '1.6',
                                        bgcolor: '#1e1e1e',
                                        color: '#d4d4d4'
                                    },
                                    '& .MuiInputBase-input': {
                                        color: '#d4d4d4'
                                    }
                                }}
                            />

                            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                <Button
                                    variant="outlined"
                                    onClick={() => {
                                        // Load a default pipeline template
                                        setAdvancedYaml(pipelineYaml || 'pipeline:\n  name: Custom Pipeline\n  steps: []');
                                    }}
                                >
                                    Load Template
                                </Button>
                                <Button
                                    variant="outlined"
                                    onClick={() => setAdvancedYaml('')}
                                >
                                    Clear
                                </Button>
                            </Box>
                        </CardContent>
                    </Card>
                </Box>
            )}

            {/* Save Pipeline Dialog */}
            <Dialog open={showSaveDialog} onClose={() => setShowSaveDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Save Pipeline</DialogTitle>
                <DialogContent>
                    <Box sx={{ pt: 2 }}>
                        <TextField
                            label="Pipeline Name"
                            fullWidth
                            value={pipelineName}
                            onChange={(e) => setPipelineName(e.target.value)}
                            placeholder="e.g., salesfact_validation"
                            helperText="Use only letters, numbers, and underscores"
                            sx={{ mb: 2 }}
                            required
                        />
                        <TextField
                            label="Description"
                            fullWidth
                            multiline
                            rows={3}
                            value={pipelineDescription}
                            onChange={(e) => setPipelineDescription(e.target.value)}
                            placeholder="Describe what this pipeline validates..."
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowSaveDialog(false)}>Cancel</Button>
                    <Button
                        onClick={handleConfirmSave}
                        variant="contained"
                        disabled={!pipelineName.trim() || loading}
                        startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
                    >
                        Save
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Load Pipeline Dialog */}
            <Dialog open={showLoadDialog} onClose={() => setShowLoadDialog(false)} maxWidth="md" fullWidth>
                <DialogTitle>
                    Load Saved Pipeline
                    {savedPipelines.length > 0 && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                            {savedPipelines.length} pipeline{savedPipelines.length !== 1 ? 's' : ''} available
                        </Typography>
                    )}
                </DialogTitle>
                <DialogContent>
                    {savedPipelines.length === 0 ? (
                        <Box sx={{ textAlign: 'center', py: 4 }}>
                            <Typography variant="body1" color="text.secondary">
                                No saved pipelines yet
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                Create a pipeline and save it to see it here
                            </Typography>
                        </Box>
                    ) : (
                        <List>
                            {savedPipelines.map((pipeline, index) => (
                                <React.Fragment key={pipeline.pipeline_name}>
                                    <ListItem>
                                        <ListItemText
                                            primary={
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <Typography variant="body1" fontWeight="medium">
                                                        {pipeline.pipeline_name}
                                                    </Typography>
                                                    {pipeline.tags && pipeline.tags.length > 0 && (
                                                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                                                            {pipeline.tags.map((tag: string) => (
                                                                <Chip key={tag} label={tag} size="small" />
                                                            ))}
                                                        </Box>
                                                    )}
                                                </Box>
                                            }
                                            secondary={
                                                <>
                                                    {pipeline.description && (
                                                        <Typography variant="body2" color="text.secondary">
                                                            {pipeline.description}
                                                        </Typography>
                                                    )}
                                                    {pipeline.updated_at && (
                                                        <Typography variant="caption" color="text.secondary">
                                                            Last updated: {new Date(pipeline.updated_at).toLocaleString()}
                                                        </Typography>
                                                    )}
                                                </>
                                            }
                                        />
                                        <ListItemSecondaryAction>
                                            <IconButton
                                                edge="end"
                                                onClick={() => handleLoadPipeline(pipeline.pipeline_name)}
                                                disabled={loading}
                                                sx={{ mr: 1 }}
                                            >
                                                <EditIcon />
                                            </IconButton>
                                            <IconButton
                                                edge="end"
                                                onClick={() => handleDeletePipeline(pipeline.pipeline_name)}
                                                disabled={loading}
                                                color="error"
                                            >
                                                <DeleteIcon />
                                            </IconButton>
                                        </ListItemSecondaryAction>
                                    </ListItem>
                                    {index < savedPipelines.length - 1 && <Divider />}
                                </React.Fragment>
                            ))}
                        </List>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowLoadDialog(false)}>Close</Button>
                </DialogActions>
            </Dialog>

            {/* Query Suggestions Dialog */}
            <QuerySuggestions
                open={showQuerySuggestions}
                onClose={() => setShowQuerySuggestions(false)}
                onSelectQueries={handleQuerySuggestionsSelect}
                selectedPipeline={selectedTable ? { pipeline_name: `validate_${selectedTable}` } : undefined}
            />
        </Box>
    );
}
