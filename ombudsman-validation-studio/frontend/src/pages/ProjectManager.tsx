import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    Button,
    Card,
    CardContent,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Grid,
    TextField,
    Typography,
    IconButton,
    Chip,
    Alert,
    CircularProgress,
    Divider,
    FormControlLabel,
    Checkbox,
    LinearProgress,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Autocomplete
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AutoModeIcon from '@mui/icons-material/AutoMode';
import SettingsIcon from '@mui/icons-material/Settings';

interface Project {
    project_id: string;
    name: string;
    description: string;
    created_at: string;
    updated_at: string;
    sql_database: string;
    sql_schemas: string[];
    snowflake_database: string;
    snowflake_schemas: string[];
    schema_mappings: { [key: string]: string };
}

interface ProjectManagerProps {
    onProjectSelected: (projectId: string, metadata: any) => void;
}

export default function ProjectManager({ onProjectSelected }: ProjectManagerProps) {
    const navigate = useNavigate();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [autoSetupEnabled, setAutoSetupEnabled] = useState(true);
    const [autoSetupProgress, setAutoSetupProgress] = useState(false);
    const [autoSetupStatus, setAutoSetupStatus] = useState<{
        message: string;
        pipelines_created: number;
        tables_processed: string[];
        batch_id?: string;
        batch_name?: string;
        errors: string[];
    } | null>(null);
    const [newProject, setNewProject] = useState({
        name: '',
        description: '',
        sql_database: '',
        sql_schemas: [] as string[],
        snowflake_database: '',
        snowflake_schemas: [] as string[]
    });
    const [sqlDatabases, setSqlDatabases] = useState<string[]>([]);
    const [snowflakeDatabases, setSnowflakeDatabases] = useState<string[]>([]);
    const [loadingDatabases, setLoadingDatabases] = useState(false);
    const [availableSqlSchemas, setAvailableSqlSchemas] = useState<string[]>([]);
    const [availableSnowSchemas, setAvailableSnowSchemas] = useState<string[]>([]);
    const [loadingSchemas, setLoadingSchemas] = useState(false);

    useEffect(() => {
        loadProjects();
    }, []);

    const fetchDatabases = async () => {
        setLoadingDatabases(true);
        try {
            const [sqlResponse, snowResponse] = await Promise.all([
                fetch('http://localhost:8000/connections/databases/sqlserver'),
                fetch('http://localhost:8000/connections/databases/snowflake')
            ]);

            const sqlData = await sqlResponse.json();
            const snowData = await snowResponse.json();

            if (sqlData.status === 'success' && sqlData.databases.length > 0) {
                setSqlDatabases(sqlData.databases);
                // Set first database as default if not already set
                if (!newProject.sql_database) {
                    const firstDb = sqlData.databases[0];
                    setNewProject(prev => ({ ...prev, sql_database: firstDb }));
                    // Fetch schemas for the first database
                    fetchSchemasForDatabase(firstDb, 'sql');
                }
            }

            if (snowData.status === 'success' && snowData.databases.length > 0) {
                setSnowflakeDatabases(snowData.databases);
                // Set first database as default if not already set
                if (!newProject.snowflake_database) {
                    const firstDb = snowData.databases[0];
                    setNewProject(prev => ({ ...prev, snowflake_database: firstDb }));
                    // Fetch schemas for the first database
                    fetchSchemasForDatabase(firstDb, 'snowflake');
                }
            }
        } catch (error) {
            console.error('Failed to fetch databases:', error);
        }
        setLoadingDatabases(false);
    };

    const fetchSchemasForDatabase = async (database: string, type: 'sql' | 'snowflake') => {
        setLoadingSchemas(true);
        try {
            const params = new URLSearchParams();
            if (type === 'sql') {
                params.append('sql_database', database);
                params.append('snowflake_database', newProject.snowflake_database || 'SAMPLEDW');
            } else {
                params.append('sql_database', newProject.sql_database || 'SampleDW');
                params.append('snowflake_database', database);
            }

            const response = await fetch(`http://localhost:8000/database-mapping/available-schemas?${params.toString()}`);
            const data = await response.json();

            if (response.ok) {
                if (type === 'sql' && data.sql_server) {
                    setAvailableSqlSchemas(data.sql_server);
                } else if (type === 'snowflake' && data.snowflake) {
                    setAvailableSnowSchemas(data.snowflake);
                }
            } else {
                console.error(`Failed to fetch ${type} schemas:`, data.detail);
            }
        } catch (error) {
            console.error(`Failed to fetch ${type} schemas:`, error);
        }
        setLoadingSchemas(false);
    };

    const loadProjects = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/projects/list');
            const data = await response.json();

            if (response.ok) {
                setProjects(data.projects || []);
            } else {
                setError(data.detail || 'Failed to load projects');
            }
        } catch (err) {
            setError(`Failed to load projects: ${err}`);
        }

        setLoading(false);
    };

    const createProject = async () => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('auth_token');
            const headers: HeadersInit = {
                'Content-Type': 'application/json'
            };

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch('http://localhost:8000/projects/create', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    name: newProject.name,
                    description: newProject.description,
                    sql_database: newProject.sql_database,
                    sql_schemas: newProject.sql_schemas,
                    snowflake_database: newProject.snowflake_database,
                    snowflake_schemas: newProject.snowflake_schemas
                })
            });

            const data = await response.json();

            if (response.ok) {
                setCreateDialogOpen(false);
                const projectId = data.project_id;

                // Reset form
                setNewProject({
                    name: '',
                    description: '',
                    sql_database: sqlDatabases.length > 0 ? sqlDatabases[0] : '',
                    sql_schemas: [],
                    snowflake_database: snowflakeDatabases.length > 0 ? snowflakeDatabases[0] : '',
                    snowflake_schemas: []
                });

                await loadProjects();

                // If auto-setup is enabled, trigger it
                if (autoSetupEnabled) {
                    await runAutoSetup(projectId, data.metadata);
                } else {
                    // Auto-select the new project with empty config
                    const projectData = {
                        ...data.metadata,
                        config: {}
                    };
                    onProjectSelected(projectId, projectData);
                }
            } else {
                setError(data.detail || 'Failed to create project');
            }
        } catch (err) {
            setError(`Failed to create project: ${err}`);
        }

        setLoading(false);
    };

    const runAutoSetup = async (projectId: string, metadata: any) => {
        setAutoSetupProgress(true);
        setAutoSetupStatus(null);
        setError(null);

        try {
            const token = localStorage.getItem('auth_token');
            const headers: any = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Call /setup endpoint to extract metadata and infer relationships
            // This does NOT create pipelines - user must review relationships first
            // Note: Not passing schema to extract ALL tables from ALL schemas
            const response = await fetch(`http://localhost:8000/projects/${projectId}/setup`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    connection: 'sqlserver'
                })
            });

            const result = await response.json();

            if (response.ok) {
                // Show success message and navigate to Database Mapping page
                alert(`Success! Extracted ${result.table_count} tables and inferred ${result.relationship_count} relationships.\n\nPlease review and validate the relationships before proceeding to automation.`);

                // Auto-select the project and navigate to Database Mapping page
                const projectData = {
                    ...metadata,
                    config: {}
                };
                onProjectSelected(projectId, projectData);

                setAutoSetupProgress(false);
            } else {
                setError(result.detail || 'Auto-setup failed');
                setAutoSetupProgress(false);
            }
        } catch (err) {
            setError(`Auto-setup failed: ${err}`);
            setAutoSetupProgress(false);
        }
    };

    const loadProject = async (projectId: string) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`http://localhost:8000/projects/${projectId}`);
            const data = await response.json();

            if (response.ok) {
                // Pass the full project data including config (which contains relationships)
                const projectData = {
                    ...data.metadata,
                    config: data.config
                };
                onProjectSelected(projectId, projectData);
            } else {
                setError(data.detail || 'Failed to load project');
            }
        } catch (err) {
            setError(`Failed to load project: ${err}`);
        }

        setLoading(false);
    };

    const deleteProject = async (projectId: string) => {
        if (!confirm('Are you sure you want to delete this project?')) {
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('auth_token');
            const headers: HeadersInit = {
                'Content-Type': 'application/json'
            };

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`http://localhost:8000/projects/${projectId}`, {
                method: 'DELETE',
                headers
            });

            const data = await response.json();

            if (response.ok) {
                await loadProjects();
            } else {
                setError(data.detail || 'Failed to delete project');
            }
        } catch (err) {
            setError(`Failed to delete project: ${err}`);
        }

        setLoading(false);
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    return (
        <Box sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h4">Projects</Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => setCreateDialogOpen(true)}
                >
                    Create New Project
                </Button>
            </Box>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : projects.length === 0 ? (
                <Card>
                    <CardContent sx={{ textAlign: 'center', p: 4 }}>
                        <Typography variant="h6" color="text.secondary">
                            No projects yet
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            Create your first project to start mapping databases
                        </Typography>
                        <Button
                            variant="contained"
                            startIcon={<AddIcon />}
                            onClick={() => setCreateDialogOpen(true)}
                            sx={{ mt: 2 }}
                        >
                            Create Project
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <Grid container spacing={3}>
                    {projects.map((project) => (
                        <Grid item xs={12} md={6} lg={4} key={project.project_id}>
                            <Card>
                                <CardContent>
                                    <Typography variant="h6" gutterBottom>
                                        {project.name}
                                    </Typography>
                                    {project.description && (
                                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                            {project.description}
                                        </Typography>
                                    )}

                                    <Divider sx={{ my: 2 }} />

                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            SQL Server
                                        </Typography>
                                        <Typography variant="body2">
                                            {project.sql_database}
                                        </Typography>
                                        <Box sx={{ mt: 1 }}>
                                            {project.sql_schemas.map(schema => (
                                                <Chip key={schema} label={schema} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                                            ))}
                                        </Box>
                                    </Box>

                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            Snowflake
                                        </Typography>
                                        <Typography variant="body2">
                                            {project.snowflake_database}
                                        </Typography>
                                        <Box sx={{ mt: 1 }}>
                                            {project.snowflake_schemas.map(schema => (
                                                <Chip key={schema} label={schema} size="small" color="primary" sx={{ mr: 0.5, mb: 0.5 }} />
                                            ))}
                                        </Box>
                                    </Box>

                                    <Typography variant="caption" color="text.secondary" display="block">
                                        Last updated: {formatDate(project.updated_at)}
                                    </Typography>

                                    <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                                        <Button
                                            variant="contained"
                                            size="small"
                                            startIcon={<FolderOpenIcon />}
                                            onClick={() => loadProject(project.project_id)}
                                            fullWidth
                                        >
                                            Open
                                        </Button>
                                        <IconButton
                                            size="small"
                                            onClick={() => navigate(`/projects/${project.project_id}/settings`)}
                                            color="primary"
                                            title="Project Settings"
                                        >
                                            <SettingsIcon />
                                        </IconButton>
                                        <IconButton
                                            size="small"
                                            onClick={() => deleteProject(project.project_id)}
                                            color="error"
                                        >
                                            <DeleteIcon />
                                        </IconButton>
                                    </Box>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            )}

            {/* Create Project Dialog */}
            <Dialog
                open={createDialogOpen}
                onClose={() => setCreateDialogOpen(false)}
                maxWidth="md"
                fullWidth
                TransitionProps={{
                    onEnter: fetchDatabases
                }}
            >
                <DialogTitle>Create New Project</DialogTitle>
                <DialogContent>
                    <Box sx={{ pt: 2 }}>
                        <TextField
                            label="Project Name"
                            fullWidth
                            value={newProject.name}
                            onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                            sx={{ mb: 2 }}
                            required
                        />

                        <TextField
                            label="Description"
                            fullWidth
                            multiline
                            rows={2}
                            value={newProject.description}
                            onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                            sx={{ mb: 3 }}
                        />

                        <Typography variant="h6" gutterBottom>SQL Server Configuration</Typography>
                        <Autocomplete
                            options={sqlDatabases}
                            value={newProject.sql_database}
                            onChange={(_, newValue) => {
                                setNewProject({ ...newProject, sql_database: newValue || '' });
                                if (newValue) {
                                    fetchSchemasForDatabase(newValue, 'sql');
                                }
                            }}
                            loading={loadingDatabases}
                            freeSolo
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Database"
                                    required
                                    InputProps={{
                                        ...params.InputProps,
                                        endAdornment: (
                                            <>
                                                {loadingDatabases ? <CircularProgress color="inherit" size={20} /> : null}
                                                {params.InputProps.endAdornment}
                                            </>
                                        ),
                                    }}
                                />
                            )}
                            sx={{ mb: 2 }}
                        />
                        <Autocomplete
                            multiple
                            options={availableSqlSchemas}
                            value={newProject.sql_schemas}
                            onChange={(_, newValue) => setNewProject({ ...newProject, sql_schemas: newValue })}
                            loading={loadingSchemas}
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Schemas"
                                    helperText="Select schemas to include in validation"
                                    InputProps={{
                                        ...params.InputProps,
                                        endAdornment: (
                                            <>
                                                {loadingSchemas ? <CircularProgress color="inherit" size={20} /> : null}
                                                {params.InputProps.endAdornment}
                                            </>
                                        ),
                                    }}
                                />
                            )}
                            sx={{ mb: 3 }}
                        />

                        <Typography variant="h6" gutterBottom>Snowflake Configuration</Typography>
                        <Autocomplete
                            options={snowflakeDatabases}
                            value={newProject.snowflake_database}
                            onChange={(_, newValue) => {
                                setNewProject({ ...newProject, snowflake_database: newValue || '' });
                                if (newValue) {
                                    fetchSchemasForDatabase(newValue, 'snowflake');
                                }
                            }}
                            loading={loadingDatabases}
                            freeSolo
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Database"
                                    required
                                    InputProps={{
                                        ...params.InputProps,
                                        endAdornment: (
                                            <>
                                                {loadingDatabases ? <CircularProgress color="inherit" size={20} /> : null}
                                                {params.InputProps.endAdornment}
                                            </>
                                        ),
                                    }}
                                />
                            )}
                            sx={{ mb: 2 }}
                        />
                        <Autocomplete
                            multiple
                            options={availableSnowSchemas}
                            value={newProject.snowflake_schemas}
                            onChange={(_, newValue) => setNewProject({ ...newProject, snowflake_schemas: newValue })}
                            loading={loadingSchemas}
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Schemas"
                                    helperText="Select schemas to include in validation - will be intelligently mapped"
                                    InputProps={{
                                        ...params.InputProps,
                                        endAdornment: (
                                            <>
                                                {loadingSchemas ? <CircularProgress color="inherit" size={20} /> : null}
                                                {params.InputProps.endAdornment}
                                            </>
                                        ),
                                    }}
                                />
                            )}
                            sx={{ mb: 2 }}
                        />

                        <Alert severity="info" sx={{ mt: 2 }}>
                            The system will automatically map SQL Server schemas to Snowflake schemas based on naming similarity.
                            You can adjust mappings later in the Database Mapping page.
                        </Alert>

                        <Divider sx={{ my: 3 }} />

                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={autoSetupEnabled}
                                    onChange={(e) => setAutoSetupEnabled(e.target.checked)}
                                    color="primary"
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1" fontWeight="medium">
                                        Auto-Setup All Tables (Recommended)
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        Automatically create pipelines with intelligent validations and custom queries
                                        for all common tables, then execute them in parallel as a batch
                                    </Typography>
                                </Box>
                            }
                        />

                        {autoSetupEnabled && (
                            <Alert severity="success" sx={{ mt: 2 }}>
                                <Typography variant="body2" fontWeight="medium">
                                    Auto-Setup will:
                                </Typography>
                                <List dense>
                                    <ListItem sx={{ py: 0 }}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircleIcon fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary="Extract metadata from both databases"
                                            primaryTypographyProps={{ variant: 'caption' }}
                                        />
                                    </ListItem>
                                    <ListItem sx={{ py: 0 }}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircleIcon fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary="Find all common tables between SQL Server and Snowflake"
                                            primaryTypographyProps={{ variant: 'caption' }}
                                        />
                                    </ListItem>
                                    <ListItem sx={{ py: 0 }}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircleIcon fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary="Generate intelligent validation suggestions for each table"
                                            primaryTypographyProps={{ variant: 'caption' }}
                                        />
                                    </ListItem>
                                    <ListItem sx={{ py: 0 }}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircleIcon fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary="Create custom business queries with JOINs"
                                            primaryTypographyProps={{ variant: 'caption' }}
                                        />
                                    </ListItem>
                                    <ListItem sx={{ py: 0 }}>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <CheckCircleIcon fontSize="small" color="success" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary="Create and execute a batch job to validate all tables in parallel"
                                            primaryTypographyProps={{ variant: 'caption' }}
                                        />
                                    </ListItem>
                                </List>
                            </Alert>
                        )}
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={createProject}
                        variant="contained"
                        disabled={!newProject.name || loading}
                        startIcon={autoSetupEnabled ? <AutoModeIcon /> : <AddIcon />}
                    >
                        {loading ? <CircularProgress size={20} /> : autoSetupEnabled ? 'Create & Auto-Setup' : 'Create Project'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Auto-Setup Progress Dialog */}
            <Dialog open={autoSetupProgress} maxWidth="md" fullWidth>
                <DialogTitle>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AutoModeIcon color="primary" />
                        <Typography variant="h6">Auto-Setup in Progress</Typography>
                    </Box>
                </DialogTitle>
                <DialogContent>
                    {!autoSetupStatus ? (
                        <Box sx={{ textAlign: 'center', py: 3 }}>
                            <CircularProgress size={60} />
                            <Typography variant="h6" sx={{ mt: 3 }}>
                                Setting up your project...
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                Extracting metadata, creating pipelines, and starting batch execution
                            </Typography>
                            <LinearProgress sx={{ mt: 3 }} />
                        </Box>
                    ) : (
                        <Box sx={{ py: 2 }}>
                            <Alert severity={autoSetupStatus.errors.length > 0 ? 'warning' : 'success'} sx={{ mb: 3 }}>
                                <Typography variant="body1" fontWeight="medium">
                                    {autoSetupStatus.message}
                                </Typography>
                            </Alert>

                            <Grid container spacing={2} sx={{ mb: 3 }}>
                                <Grid item xs={6}>
                                    <Card variant="outlined">
                                        <CardContent>
                                            <Typography variant="h3" color="primary">
                                                {autoSetupStatus.pipelines_created}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                Pipelines Created
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                                <Grid item xs={6}>
                                    <Card variant="outlined">
                                        <CardContent>
                                            <Typography variant="h3" color="success.main">
                                                {autoSetupStatus.tables_processed.length}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                Tables Processed
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            </Grid>

                            {autoSetupStatus.batch_name && (
                                <Alert severity="info" sx={{ mb: 2 }}>
                                    <Typography variant="body2">
                                        <strong>Batch:</strong> {autoSetupStatus.batch_name}
                                    </Typography>
                                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                                        Executing all validations in parallel...
                                    </Typography>
                                </Alert>
                            )}

                            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                                Redirecting to batch results in 3 seconds...
                            </Typography>
                            <LinearProgress sx={{ mt: 1 }} />
                        </Box>
                    )}
                </DialogContent>
            </Dialog>
        </Box>
    );
}
