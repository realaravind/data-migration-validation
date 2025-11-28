import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, AppBar, Toolbar, Typography, Container, Button } from '@mui/material';
import PipelineYamlEditor from './pages/PipelineYamlEditor';
import ValidationDashboard from './pages/ValidationDashboard';
import LandingPage from './pages/LandingPage';
import EnvironmentSetup from './pages/EnvironmentSetup';
import MetadataExtraction from './pages/MetadataExtraction';
import ValidationRules from './pages/ValidationRules';
import Validations from './pages/Validations';
import PipelineExecution from './pages/PipelineExecution';
import PipelineSuggestions from './pages/PipelineSuggestions';
import MermaidDiagram from './pages/MermaidDiagram';

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
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <Router>
                <AppBar position="static">
                    <Toolbar>
                        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                            Ombudsman Validation Studio
                        </Typography>
                        <Button color="inherit" component={Link} to="/">Home</Button>
                        <Button color="inherit" component={Link} to="/pipeline">Pipeline Editor</Button>
                        <Button color="inherit" component={Link} to="/dashboard">Dashboard</Button>
                    </Toolbar>
                </AppBar>

                <Container maxWidth="xl" sx={{ mt: 4 }}>
                    <Routes>
                        <Route path="/" element={<LandingPage />} />
                        <Route path="/pipeline" element={<PipelineYamlEditor />} />
                        <Route path="/dashboard" element={<ValidationDashboard />} />
                        <Route path="/environment" element={<EnvironmentSetup />} />
                        <Route path="/metadata" element={<MetadataExtraction />} />
                        <Route path="/rules" element={<ValidationRules />} />
                        <Route path="/validations" element={<Validations />} />
                        <Route path="/execution" element={<PipelineExecution />} />
                        <Route path="/suggestions" element={<PipelineSuggestions />} />
                        <Route path="/diagram" element={<MermaidDiagram />} />
                    </Routes>
                </Container>
            </Router>
        </ThemeProvider>
    );
}

export default App;
