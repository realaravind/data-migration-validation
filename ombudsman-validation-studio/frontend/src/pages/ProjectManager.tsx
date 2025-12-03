import React, { useState, useEffect } from 'react';
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
    List,
    ListItem,
    ListItemText,
    ListItemSecondaryAction,
    IconButton,
    Chip,
    Alert,
    CircularProgress,
    Divider
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import AddIcon from '@mui/icons-material/Add';

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
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [newProject, setNewProject] = useState({
        name: '',
        description: '',
        sql_database: 'SampleDW',
        sql_schemas: 'dbo,dim,fact',
        snowflake_database: 'SAMPLEDW',
        snowflake_schemas: 'PUBLIC,DIM,FACT'
    });

    useEffect(() => {
        loadProjects();
    }, []);

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
            const response = await fetch('http://localhost:8000/projects/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newProject.name,
                    description: newProject.description,
                    sql_database: newProject.sql_database,
                    sql_schemas: newProject.sql_schemas.split(',').map(s => s.trim()),
                    snowflake_database: newProject.snowflake_database,
                    snowflake_schemas: newProject.snowflake_schemas.split(',').map(s => s.trim())
                })
            });

            const data = await response.json();

            if (response.ok) {
                setCreateDialogOpen(false);
                setNewProject({
                    name: '',
                    description: '',
                    sql_database: 'SampleDW',
                    sql_schemas: 'dbo,dim,fact',
                    snowflake_database: 'SAMPLEDW',
                    snowflake_schemas: 'PUBLIC,DIM,FACT'
                });
                await loadProjects();
                // Auto-select the new project with empty config
                const projectData = {
                    ...data.metadata,
                    config: {}
                };
                onProjectSelected(data.project_id, projectData);
            } else {
                setError(data.detail || 'Failed to create project');
            }
        } catch (err) {
            setError(`Failed to create project: ${err}`);
        }

        setLoading(false);
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
            const response = await fetch(`http://localhost:8000/projects/${projectId}`, {
                method: 'DELETE'
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
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
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
                        <TextField
                            label="Database"
                            fullWidth
                            value={newProject.sql_database}
                            onChange={(e) => setNewProject({ ...newProject, sql_database: e.target.value })}
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            label="Schemas (comma-separated)"
                            fullWidth
                            value={newProject.sql_schemas}
                            onChange={(e) => setNewProject({ ...newProject, sql_schemas: e.target.value })}
                            helperText="e.g., dbo,dim,fact"
                            sx={{ mb: 3 }}
                        />

                        <Typography variant="h6" gutterBottom>Snowflake Configuration</Typography>
                        <TextField
                            label="Database"
                            fullWidth
                            value={newProject.snowflake_database}
                            onChange={(e) => setNewProject({ ...newProject, snowflake_database: e.target.value })}
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            label="Schemas (comma-separated)"
                            fullWidth
                            value={newProject.snowflake_schemas}
                            onChange={(e) => setNewProject({ ...newProject, snowflake_schemas: e.target.value })}
                            helperText="e.g., PUBLIC,DIM,FACT - Schemas will be auto-mapped intelligently"
                            sx={{ mb: 2 }}
                        />

                        <Alert severity="info" sx={{ mt: 2 }}>
                            The system will automatically map SQL Server schemas to Snowflake schemas based on naming similarity.
                            You can adjust mappings later in the Database Mapping page.
                        </Alert>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={createProject}
                        variant="contained"
                        disabled={!newProject.name || loading}
                    >
                        {loading ? <CircularProgress size={20} /> : 'Create Project'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
