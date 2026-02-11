import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, AppBar, Toolbar, Typography, Container, Button, Box, Chip, IconButton, Menu, MenuItem } from '@mui/material';
import { useState, useEffect } from 'react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import AccountCircle from '@mui/icons-material/AccountCircle';
import HomeIcon from '@mui/icons-material/Home';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import UserProfile from './pages/UserProfile';
import ProtectedRoute from './components/ProtectedRoute';

// Project interface
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
import ProjectSwitcher from './components/ProjectSwitcher';
import PipelineYamlEditor from './pages/PipelineYamlEditor';
import LandingPage from './pages/LandingPage';
import EnvironmentSetup from './pages/EnvironmentSetup';
import MetadataExtraction from './pages/MetadataExtraction';
import ValidationRules from './pages/ValidationRules';
import Validations from './pages/Validations';
import PipelineExecution from './pages/PipelineExecution';
import PipelineSuggestions from './pages/PipelineSuggestions';
import MermaidDiagram from './pages/MermaidDiagram';
import ConnectionStatus from './pages/ConnectionStatus';
import SampleDataGeneration from './pages/SampleDataGeneration';
import DatabaseMapping from './pages/DatabaseMapping';
import ProjectManager from './pages/ProjectManager';
import PipelineBuilder from './pages/PipelineBuilder';
import ResultsViewer from './pages/ResultsViewer';
import WorkloadAnalysis from './pages/WorkloadAnalysis';
import ComparisonViewer from './pages/ComparisonViewer';
import ProjectSummary from './pages/ProjectSummary';
import RunComparison from './pages/RunComparison';
import AuditLogs from './pages/AuditLogs';
import NotificationSettings from './pages/NotificationSettings';
import BatchOperations from './pages/BatchOperations';
import BatchReportViewer from './pages/BatchReportViewerSimple';
import BatchBuilder from './pages/BatchBuilder';
import BugReportPreview from './pages/BugReportPreview';
import ProjectSettings from './pages/ProjectSettings';
import LogViewer from './pages/LogViewer';
import AlertsDrawer from './components/AlertsDrawer';

const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#1976d2',
        },
        secondary: {
            main: '#dc004e',
        },
    },
});

// UserMenu component for the AppBar
function UserMenu() {
    const navigate = useNavigate();
    const { user, isAuthenticated, logout } = useAuth();
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

    const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget);
    };

    const handleMenuClose = () => {
        setAnchorEl(null);
    };

    const handleProfile = () => {
        handleMenuClose();
        navigate('/profile');
    };

    const handleLogout = () => {
        handleMenuClose();
        logout();
        navigate('/login');
    };

    if (!isAuthenticated) {
        return (
            <Button color="inherit" component={Link} to="/login">
                Login
            </Button>
        );
    }

    return (
        <>
            <IconButton
                onClick={handleMenuOpen}
                sx={{
                    ml: 2,
                    color: 'white',
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                    '&:hover': {
                        bgcolor: 'rgba(255, 255, 255, 0.2)'
                    }
                }}
            >
                <AccountCircle />
            </IconButton>
            <Typography variant="body2" sx={{ ml: 1, color: 'white' }}>
                {user?.username}
            </Typography>
            <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
                anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                }}
                transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                }}
            >
                <MenuItem onClick={handleProfile}>Profile</MenuItem>
                <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
        </>
    );
}

// AppContent component that uses auth context
function AppContent() {
    const location = useLocation();
    const navigate = useNavigate();
    const { isAuthenticated } = useAuth();
    const isLandingPage = location.pathname === '/';

    const [connectionStatus, setConnectionStatus] = useState<any>({
        sqlserver: { status: 'unknown' },
        snowflake: { status: 'unknown' }
    });
    const [currentProject, setCurrentProject] = useState<Project | null>(() => {
        // Load from sessionStorage on init
        const saved = sessionStorage.getItem('currentProject');
        return saved ? JSON.parse(saved) : null;
    });
    const [allProjects, setAllProjects] = useState<Project[]>([]);

    useEffect(() => {
        fetchConnectionStatus();
        // Refresh every 30 seconds
        const interval = setInterval(fetchConnectionStatus, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        // Persist to sessionStorage whenever currentProject changes
        if (currentProject) {
            sessionStorage.setItem('currentProject', JSON.stringify(currentProject));
        } else {
            sessionStorage.removeItem('currentProject');
        }
    }, [currentProject]);

    // Auto-load project on mount
    useEffect(() => {
        const initializeProject = async () => {
            if (!isAuthenticated) return;

            try {
                // Fetch all projects from backend
                const response = await fetch(__API_URL__ + '/projects/list');
                if (!response.ok) {
                    console.error('Failed to fetch projects');
                    return;
                }

                const data = await response.json();
                const projects: Project[] = data.projects || [];
                setAllProjects(projects);

                // If no projects exist, redirect to project creation page
                if (projects.length === 0) {
                    navigate('/projects');
                    return;
                }

                // Check for last used project in sessionStorage
                const lastProjectId = sessionStorage.getItem('lastProjectId');
                let projectToLoad: Project | undefined;

                if (lastProjectId) {
                    // Try to find the last used project
                    projectToLoad = projects.find(p => p.project_id === lastProjectId);
                }

                if (!projectToLoad) {
                    // Fall back to most recently updated project
                    projectToLoad = projects.sort((a, b) =>
                        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
                    )[0];
                }

                // Load full project config from backend (this also sets active project)
                const projectResponse = await fetch(`${__API_URL__}/projects/${projectToLoad.project_id}`);
                if (projectResponse.ok) {
                    const projectData = await projectResponse.json();
                    const fullProject = {
                        ...projectData.metadata,
                        config: projectData.config
                    };
                    setCurrentProject(fullProject);
                    sessionStorage.setItem('lastProjectId', projectToLoad.project_id);
                    sessionStorage.setItem('currentProject', JSON.stringify(fullProject));
                    console.log('[App] Loaded project on init:', projectToLoad.project_id);
                } else {
                    // Fallback if API fails
                    setCurrentProject(projectToLoad);
                    sessionStorage.setItem('lastProjectId', projectToLoad.project_id);
                    sessionStorage.setItem('currentProject', JSON.stringify(projectToLoad));
                }
            } catch (error) {
                console.error('Failed to initialize project:', error);
            }
        };

        initializeProject();
    }, [isAuthenticated, navigate]);

    const fetchConnectionStatus = async () => {
        try {
            const response = await fetch(__API_URL__ + '/connections/status');
            const data = await response.json();
            setConnectionStatus(data.connections || {
                sqlserver: { status: 'unknown' },
                snowflake: { status: 'unknown' }
            });
        } catch (error) {
            console.error('Failed to fetch connection status:', error);
            setConnectionStatus({
                sqlserver: { status: 'error' },
                snowflake: { status: 'error' }
            });
        }
    };

    const handleProjectSwitch = async (project: Project) => {
        try {
            // Call backend API to set active project and load full config
            const token = localStorage.getItem('auth_token');
            const headers: any = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${__API_URL__}/projects/${project.project_id}`, { headers });
            if (response.ok) {
                const data = await response.json();
                const fullProject = {
                    ...data.metadata,
                    config: data.config
                };
                setCurrentProject(fullProject);
                sessionStorage.setItem('lastProjectId', project.project_id);
                sessionStorage.setItem('currentProject', JSON.stringify(fullProject));
                console.log('[App] Switched to project:', project.project_id);
            } else {
                console.error('[App] Failed to load project from backend');
                // Fallback to using the project from dropdown
                setCurrentProject(project);
                sessionStorage.setItem('lastProjectId', project.project_id);
                sessionStorage.setItem('currentProject', JSON.stringify(project));
            }
        } catch (error) {
            console.error('[App] Error switching project:', error);
            // Fallback to using the project from dropdown
            setCurrentProject(project);
            sessionStorage.setItem('lastProjectId', project.project_id);
            sessionStorage.setItem('currentProject', JSON.stringify(project));
        }
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', m: 0, p: 0 }}>
            <AppBar position="static" sx={{ m: 0 }}>
                <Toolbar>
                    {/* Logo as clickable dashboard link - Industry standard UX pattern */}
                    <Typography
                        variant="h6"
                        component="div"
                        onClick={() => navigate('/')}
                        sx={{
                            mr: 'auto',
                            cursor: 'pointer',
                            transition: 'opacity 0.2s ease',
                            userSelect: 'none',
                            '&:hover': {
                                opacity: 0.8
                            }
                        }}
                    >
                        Ombudsman.AI
                    </Typography>

                    {/* Project Switcher - Interactive dropdown to switch between projects */}
                    {isAuthenticated && (
                        <ProjectSwitcher
                            currentProject={currentProject}
                            allProjects={allProjects}
                            onProjectChange={handleProjectSwitch}
                            onCreateNew={() => navigate('/projects')}
                            onManageAll={() => navigate('/projects')}
                        />
                    )}

                    {/* Alerts Drawer - Shows system notifications */}
                    {isAuthenticated && <AlertsDrawer />}

                    {/* User Menu */}
                    <UserMenu />
                </Toolbar>
            </AppBar>

            <Container maxWidth="xl" sx={{ py: 3, flexGrow: 1 }}>
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/profile" element={
                        <ProtectedRoute>
                            <UserProfile />
                        </ProtectedRoute>
                    } />
                    <Route path="/" element={
                        <ProtectedRoute>
                            <LandingPage />
                        </ProtectedRoute>
                    } />
                    <Route path="/projects" element={
                        <ProtectedRoute>
                            <ProjectManagerWrapper setCurrentProject={setCurrentProject} />
                        </ProtectedRoute>
                    } />
                    <Route path="/pipeline" element={
                        <ProtectedRoute>
                            <PipelineYamlEditor />
                        </ProtectedRoute>
                    } />
                    <Route path="/pipeline-builder" element={
                        <ProtectedRoute>
                            <PipelineBuilder />
                        </ProtectedRoute>
                    } />
                    <Route path="/environment" element={
                        <ProtectedRoute>
                            <EnvironmentSetup />
                        </ProtectedRoute>
                    } />
                    <Route path="/metadata" element={
                        <ProtectedRoute>
                            <MetadataExtraction />
                        </ProtectedRoute>
                    } />
                    <Route path="/database-mapping" element={
                        <ProtectedRoute>
                            <DatabaseMapping />
                        </ProtectedRoute>
                    } />
                    <Route path="/rules" element={
                        <ProtectedRoute>
                            <ValidationRules />
                        </ProtectedRoute>
                    } />
                    <Route path="/validations" element={
                        <ProtectedRoute>
                            <Validations />
                        </ProtectedRoute>
                    } />
                    <Route path="/execution" element={
                        <ProtectedRoute>
                            <PipelineExecution />
                        </ProtectedRoute>
                    } />
                    <Route path="/suggestions" element={
                        <ProtectedRoute>
                            <PipelineSuggestions />
                        </ProtectedRoute>
                    } />
                    <Route path="/diagram" element={
                        <ProtectedRoute>
                            <MermaidDiagram />
                        </ProtectedRoute>
                    } />
                    <Route path="/connections" element={
                        <ProtectedRoute>
                            <ConnectionStatus />
                        </ProtectedRoute>
                    } />
                    <Route path="/sample-data" element={
                        <ProtectedRoute>
                            <SampleDataGeneration />
                        </ProtectedRoute>
                    } />
                    <Route path="/workload" element={
                        <ProtectedRoute>
                            <WorkloadAnalysis />
                        </ProtectedRoute>
                    } />
                    <Route path="/project-summary" element={
                        <ProtectedRoute>
                            <ProjectSummary />
                        </ProtectedRoute>
                    } />
                    <Route path="/run-comparison" element={
                        <ProtectedRoute>
                            <RunComparison />
                        </ProtectedRoute>
                    } />
                    <Route path="/results/:runId" element={
                        <ProtectedRoute>
                            <ResultsViewer />
                        </ProtectedRoute>
                    } />
                    <Route path="/comparison/:runId/:stepName" element={
                        <ProtectedRoute>
                            <ComparisonViewer />
                        </ProtectedRoute>
                    } />
                    <Route path="/audit-logs" element={
                        <ProtectedRoute>
                            <AuditLogs />
                        </ProtectedRoute>
                    } />
                    <Route path="/notifications" element={
                        <ProtectedRoute>
                            <NotificationSettings />
                        </ProtectedRoute>
                    } />
                    <Route path="/batch" element={
                        <ProtectedRoute>
                            <BatchOperations />
                        </ProtectedRoute>
                    } />
                    <Route path="/batch-builder" element={
                        <ProtectedRoute>
                            <BatchBuilder />
                        </ProtectedRoute>
                    } />
                    <Route path="/batch-report/:jobId" element={
                        <ProtectedRoute>
                            <BatchReportViewer />
                        </ProtectedRoute>
                    } />
                    <Route path="/bug-report/:reportId" element={
                        <ProtectedRoute>
                            <BugReportPreview />
                        </ProtectedRoute>
                    } />
                    <Route path="/projects/:projectId/settings" element={
                        <ProtectedRoute>
                            <ProjectSettings />
                        </ProtectedRoute>
                    } />
                    <Route path="/logs" element={
                        <ProtectedRoute>
                            <LogViewer />
                        </ProtectedRoute>
                    } />
                </Routes>
            </Container>

            {/* Connection Status Footer - Shows on all pages */}
            {connectionStatus && (
                <Box sx={{
                    mt: 'auto',
                    p: 2,
                    bgcolor: (connectionStatus.sqlserver?.status === 'success' && connectionStatus.snowflake?.status === 'success')
                        ? 'success.light'
                        : 'grey.100',
                    borderTop: '1px solid',
                    borderColor: 'divider',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {connectionStatus.sqlserver?.status === 'success' ? (
                                <CheckCircleIcon sx={{ color: 'success.dark' }} />
                            ) : (
                                <ErrorIcon sx={{ color: 'error.main' }} />
                            )}
                            <Typography variant="body2" fontWeight="medium">
                                SQL Server {connectionStatus.sqlserver?.status === 'success' ? 'Connected' : 'Disconnected'}
                            </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {connectionStatus.snowflake?.status === 'success' ? (
                                <CheckCircleIcon sx={{ color: 'success.dark' }} />
                            ) : (
                                <ErrorIcon sx={{ color: 'error.main' }} />
                            )}
                            <Typography variant="body2" fontWeight="medium">
                                Snowflake {connectionStatus.snowflake?.status === 'success' ? 'Connected' : 'Not Configured'}
                            </Typography>
                        </Box>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                        © {new Date().getFullYear()} Ombudsman.AI. All rights reserved.
                    </Typography>
                </Box>
            )}
        </Box>
    );
}

function App() {
    return (
        <AuthProvider>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                <Router>
                    <AppContent />
                </Router>
            </ThemeProvider>
        </AuthProvider>
    );
}

// Wrapper to use useNavigate hook
function ProjectManagerWrapper({ setCurrentProject }: any) {
    const navigate = useNavigate();

    const handleProjectSelected = (_projectId: string, metadata: any) => {
        setCurrentProject(metadata);
        sessionStorage.setItem('currentProject', JSON.stringify(metadata));
        navigate('/database-mapping');
    };

    return <ProjectManager onProjectSelected={handleProjectSelected} />;
}

export default App;
