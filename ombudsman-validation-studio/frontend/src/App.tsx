import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, AppBar, Toolbar, Typography, Container, Button, Box, Chip } from '@mui/material';
import { useState, useEffect } from 'react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
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

function App() {
    const [connectionStatus, setConnectionStatus] = useState<any>({
        sqlserver: { status: 'unknown' },
        snowflake: { status: 'unknown' }
    });
    const [currentProject, setCurrentProject] = useState<any>(() => {
        // Load from sessionStorage on init
        const saved = sessionStorage.getItem('currentProject');
        return saved ? JSON.parse(saved) : null;
    });

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

    const fetchConnectionStatus = async () => {
        try {
            const response = await fetch('http://localhost:8000/connections/status');
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

    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <Router>
                <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', m: 0, p: 0 }}>
                <AppBar position="static" sx={{ m: 0 }}>
                    <Toolbar>
                        <Typography variant="h6" component="div" sx={{ mr: 'auto' }}>
                            Plural Insight
                        </Typography>
                        <Button color="inherit" component={Link} to="/">Home</Button>
                        <Button color="inherit" component={Link} to="/projects">Projects</Button>

                        {/* Current Project Context - Visually Distinct */}
                        {currentProject && (
                            <Chip
                                label={`Project: ${currentProject.name}`}
                                sx={{
                                    ml: 3,
                                    bgcolor: 'rgba(255, 255, 255, 0.2)',
                                    color: 'white',
                                    fontWeight: 'bold',
                                    border: '1px solid rgba(255, 255, 255, 0.3)',
                                    '&:hover': {
                                        bgcolor: 'rgba(255, 255, 255, 0.3)'
                                    }
                                }}
                                icon={<FolderOpenIcon sx={{ color: 'white !important' }} />}
                            />
                        )}
                    </Toolbar>
                </AppBar>

                <Container maxWidth="xl" sx={{ py: 3, flexGrow: 1 }}>
                    <Routes>
                        <Route path="/" element={<LandingPage />} />
                        <Route path="/projects" element={<ProjectManagerWrapper currentProject={currentProject} setCurrentProject={setCurrentProject} />} />
                        <Route path="/pipeline" element={<PipelineYamlEditor currentProject={currentProject} />} />
                        <Route path="/pipeline-builder" element={<PipelineBuilder currentProject={currentProject} />} />
                        <Route path="/environment" element={<EnvironmentSetup />} />
                        <Route path="/metadata" element={<MetadataExtraction currentProject={currentProject} />} />
                        <Route path="/database-mapping" element={<DatabaseMapping currentProject={currentProject} />} />
                        <Route path="/rules" element={<ValidationRules currentProject={currentProject} />} />
                        <Route path="/validations" element={<Validations currentProject={currentProject} />} />
                        <Route path="/execution" element={<PipelineExecution currentProject={currentProject} />} />
                        <Route path="/suggestions" element={<PipelineSuggestions currentProject={currentProject} />} />
                        <Route path="/diagram" element={<MermaidDiagram currentProject={currentProject} />} />
                        <Route path="/connections" element={<ConnectionStatus />} />
                        <Route path="/sample-data" element={<SampleDataGeneration currentProject={currentProject} />} />
                        <Route path="/workload" element={<WorkloadAnalysis currentProject={currentProject} />} />
                        <Route path="/project-summary" element={<ProjectSummary />} />
                        <Route path="/run-comparison" element={<RunComparison />} />
                        <Route path="/results/:runId" element={<ResultsViewer />} />
                        <Route path="/comparison/:runId/:stepName" element={<ComparisonViewer />} />
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
                            © {new Date().getFullYear()} Plural Insight. All rights reserved.
                        </Typography>
                    </Box>
                )}
                </Box>
            </Router>
        </ThemeProvider>
    );
}

// Wrapper to use useNavigate hook
function ProjectManagerWrapper({ currentProject, setCurrentProject }: any) {
    const navigate = useNavigate();

    const handleProjectSelected = (projectId: string, metadata: any) => {
        setCurrentProject(metadata);
        // Redirect to database mapping page
        navigate('/database-mapping');
    };

    return <ProjectManager onProjectSelected={handleProjectSelected} />;
}

export default App;
