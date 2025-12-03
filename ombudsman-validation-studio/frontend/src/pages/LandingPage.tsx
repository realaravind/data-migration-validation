import { Box, Typography, Card, CardContent, Grid, Button, Chip } from '@mui/material';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
    const navigate = useNavigate();

    const features = [
        {
            title: '1. Projects',
            description: 'Create and manage data migration projects with database and schema configurations',
            path: '/projects',
            color: '#ff6f00',
            status: 'active'
        },
        {
            title: '2. Pipeline Builder',
            description: 'AI-powered pipeline creation with auto-suggest, natural language, and visual interface',
            path: '/pipeline-builder',
            color: '#1976d2',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '3. Pipeline Execution',
            description: 'Execute YAML-based validation pipelines with real-time status tracking',
            path: '/execution',
            color: '#ed6c02',
            status: 'active'
        },
        {
            title: '4. Connection Testing',
            description: 'Test and monitor SQL Server and Snowflake database connections',
            path: '/connections',
            color: '#9c27b0',
            status: 'active'
        },
        {
            title: '5. Sample Data Generation',
            description: 'Generate synthetic test data for dimensions and facts with customizable schemas',
            path: '/sample-data',
            color: '#0288d1',
            status: 'active'
        },
        {
            title: '6. Mermaid Diagrams',
            description: 'Generate visual pipeline diagrams for better understanding',
            path: '/diagram',
            color: '#00796b',
            status: 'active'
        },
        {
            title: '7. Workload Analysis',
            description: 'Upload Query Store workload and auto-generate validations based on actual query patterns',
            path: '/workload',
            color: '#f57c00',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '8. Project Summary',
            description: 'Tech Lead dashboard showing project health, error trends, and actionable recommendations',
            path: '/project-summary',
            color: '#673ab7',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '9. Run Comparison',
            description: 'Compare two pipeline runs to analyze improvements, regressions, and error deltas',
            path: '/run-comparison',
            color: '#00897b',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '10. Interactive API Docs',
            description: 'Explore all API endpoints with interactive documentation and testing interface',
            path: 'http://localhost:8000/docs',
            color: '#2e7d32',
            status: 'active',
            isExternal: true
        }
    ];

    return (
        <Box>
            <Typography variant="h3" gutterBottom>
                Ombudsman Validation Studio
            </Typography>
            <Typography variant="h6" paragraph color="text.secondary">
                Complete Data Migration Validation Platform - All Ombudsman Core Features Available
            </Typography>

            <Grid container spacing={3} sx={{ mt: 2 }}>
                {features.map((feature, index) => (
                    <Grid item xs={12} md={6} lg={3} key={index}>
                        <Card
                            sx={{
                                height: '100%',
                                display: 'flex',
                                flexDirection: 'column',
                                cursor: 'pointer',
                                transition: 'all 0.3s',
                                borderLeft: `4px solid ${feature.color}`,
                                '&:hover': {
                                    transform: 'translateY(-4px)',
                                    boxShadow: 4
                                }
                            }}
                            onClick={() => {
                                if (feature.isExternal) {
                                    window.open(feature.path, '_blank');
                                } else {
                                    navigate(feature.path);
                                }
                            }}
                        >
                            <CardContent sx={{ flexGrow: 1 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                    <Typography variant="h6" sx={{ color: feature.color }}>
                                        {feature.title}
                                    </Typography>
                                    {feature.badge && (
                                        <Chip
                                            label={feature.badge}
                                            size="small"
                                            color="primary"
                                            sx={{
                                                fontWeight: 'bold',
                                                animation: 'pulse 2s infinite'
                                            }}
                                        />
                                    )}
                                </Box>
                                <Typography variant="body2" color="text.secondary" paragraph>
                                    {feature.description}
                                </Typography>
                                <Button
                                    variant="outlined"
                                    size="small"
                                    sx={{ mt: 'auto', borderColor: feature.color, color: feature.color }}
                                >
                                    Open
                                </Button>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
}
