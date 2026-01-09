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
            title: '3. Batch Operations',
            description: 'Execute multiple pipelines, generate data, and validate across projects in coordinated batch jobs',
            path: '/batch',
            color: '#d32f2f',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '4. Workload Analysis',
            description: 'Upload Query Store workload and auto-generate validations based on actual query patterns',
            path: '/workload',
            color: '#f57c00',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '5. Run Comparison',
            description: 'Compare two pipeline runs to analyze improvements, regressions, and error deltas',
            path: '/run-comparison',
            color: '#00897b',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '6. Project Summary',
            description: 'Tech Lead dashboard showing project health, error trends, and actionable recommendations',
            path: '/project-summary',
            color: '#673ab7',
            status: 'active',
            badge: 'NEW'
        },
        {
            title: '7. User Manual',
            description: 'Complete end-user guide with step-by-step instructions for all features, best practices, and troubleshooting',
            path: 'http://localhost:8000/docs/user-manual',
            color: '#5e35b1',
            status: 'active',
            isExternal: true,
            badge: 'DOCS'
        },
        {
            title: '8. Technical Manual',
            description: 'Developer documentation with architecture details, API reference, and implementation guides',
            path: 'http://localhost:8000/docs/technical-manual',
            color: '#1565c0',
            status: 'active',
            isExternal: true,
            badge: 'DOCS'
        },
        {
            title: '9. Architecture Diagrams',
            description: '12 interactive Mermaid diagrams visualizing system architecture, data flows, and component relationships',
            path: 'http://localhost:8000/docs/architecture-diagrams',
            color: '#00897b',
            status: 'active',
            isExternal: true,
            badge: 'DIAGRAMS'
        },
        {
            title: '10. Connection Testing',
            description: 'Test and monitor SQL Server and Snowflake database connections',
            path: '/connections',
            color: '#9c27b0',
            status: 'active'
        },
        {
            title: '11. Sample Data Generation',
            description: 'Generate synthetic test data for dimensions and facts with customizable schemas',
            path: '/sample-data',
            color: '#0288d1',
            status: 'active'
        }
    ];

    return (
        <Box>
            <Grid container spacing={3}>
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
