import {
    Box,
    Typography,
    Card,
    CardContent,
    Grid,
    Button,
    Chip,
    Paper,
    Stack,
    Divider
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import {
    FolderOpen as ProjectIcon,
    AccountTree as PipelineIcon,
    Layers as BatchIcon,
    Analytics as WorkloadIcon,
    Compare as CompareIcon,
    Dashboard as SummaryIcon,
    MenuBook as UserManualIcon,
    Code as TechManualIcon,
    Architecture as DiagramIcon,
    Cable as ConnectionIcon,
    DataObject as SampleDataIcon,
    Article as LogsIcon,
} from '@mui/icons-material';

interface Feature {
    title: string;
    description: string;
    path: string;
    icon: JSX.Element;
    color: string;
    badge?: string;
    isExternal?: boolean;
}

interface FeatureGroup {
    title: string;
    subtitle: string;
    icon: JSX.Element;
    color: string;
    bgColor: string;
    features: Feature[];
}

export default function LandingPage() {
    const navigate = useNavigate();

    const featureGroups: FeatureGroup[] = [
        {
            title: 'Core Operations',
            subtitle: 'Project setup, pipeline creation, and batch execution',
            icon: <ProjectIcon />,
            color: '#ff6f00',
            bgColor: 'rgba(255, 111, 0, 0.05)',
            features: [
                {
                    title: 'Projects',
                    description: 'Create and manage data migration projects with database configurations',
                    path: '/projects',
                    icon: <ProjectIcon />,
                    color: '#ff6f00',
                },
                {
                    title: 'Pipeline Builder',
                    description: 'AI-powered pipeline creation with auto-suggest and visual interface',
                    path: '/pipeline-builder',
                    icon: <PipelineIcon />,
                    color: '#1976d2',
                    badge: 'NEW'
                },
                {
                    title: 'Batch Operations',
                    description: 'Execute multiple pipelines and validations in coordinated batch jobs',
                    path: '/batch',
                    icon: <BatchIcon />,
                    color: '#d32f2f',
                    badge: 'NEW'
                },
                {
                    title: 'Workload Analysis',
                    description: 'Upload Query Store workload and auto-generate validations',
                    path: '/workload',
                    icon: <WorkloadIcon />,
                    color: '#f57c00',
                    badge: 'NEW'
                }
            ]
        },
        {
            title: 'Analytics & Reporting',
            subtitle: 'Performance analysis and project health monitoring',
            icon: <CompareIcon />,
            color: '#673ab7',
            bgColor: 'rgba(103, 58, 183, 0.05)',
            features: [
                {
                    title: 'Run Comparison',
                    description: 'Compare pipeline runs to analyze improvements and regressions',
                    path: '/run-comparison',
                    icon: <CompareIcon />,
                    color: '#00897b',
                    badge: 'NEW'
                },
                {
                    title: 'Project Summary',
                    description: 'Tech Lead dashboard with project health and actionable insights',
                    path: '/project-summary',
                    icon: <SummaryIcon />,
                    color: '#673ab7',
                    badge: 'NEW'
                }
            ]
        },
        {
            title: 'Documentation & Setup',
            subtitle: 'Guides, architecture diagrams, and system configuration',
            icon: <UserManualIcon />,
            color: '#1565c0',
            bgColor: 'rgba(21, 101, 192, 0.05)',
            features: [
                {
                    title: 'User Manual',
                    description: 'Complete guide with step-by-step instructions and best practices',
                    path: __API_URL__ + '/docs/user-manual',
                    icon: <UserManualIcon />,
                    color: '#5e35b1',
                    isExternal: true,
                    badge: 'DOCS'
                },
                {
                    title: 'Technical Manual',
                    description: 'Developer documentation with architecture and API reference',
                    path: __API_URL__ + '/docs/technical-manual',
                    icon: <TechManualIcon />,
                    color: '#1565c0',
                    isExternal: true,
                    badge: 'DOCS'
                },
                {
                    title: 'Architecture Diagrams',
                    description: 'Interactive Mermaid diagrams visualizing system architecture',
                    path: __API_URL__ + '/docs/architecture-diagrams',
                    icon: <DiagramIcon />,
                    color: '#00897b',
                    isExternal: true,
                    badge: 'DIAGRAMS'
                },
                {
                    title: 'Connection Testing',
                    description: 'Test and monitor SQL Server and Snowflake connections',
                    path: '/connections',
                    icon: <ConnectionIcon />,
                    color: '#9c27b0'
                },
                {
                    title: 'Sample Data Generation',
                    description: 'Generate synthetic test data for dimensions and facts',
                    path: '/sample-data',
                    icon: <SampleDataIcon />,
                    color: '#0288d1'
                },
                {
                    title: 'Application Logs',
                    description: 'View and search application logs with filtering and export',
                    path: '/logs',
                    icon: <LogsIcon />,
                    color: '#546e7a',
                    badge: 'ADMIN'
                }
            ]
        }
    ];

    return (
        <Box>
            <Stack spacing={4}>
                {featureGroups.map((group, groupIndex) => (
                    <Paper
                        key={groupIndex}
                        sx={{
                            p: 3,
                            backgroundColor: group.bgColor,
                            border: `1px solid ${group.color}20`,
                            borderRadius: 2
                        }}
                        elevation={0}
                    >
                        {/* Section Header */}
                        <Box sx={{ mb: 3 }}>
                            <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
                                <Box
                                    sx={{
                                        color: group.color,
                                        display: 'flex',
                                        alignItems: 'center'
                                    }}
                                >
                                    {group.icon}
                                </Box>
                                <Box>
                                    <Typography
                                        variant="h5"
                                        sx={{
                                            fontWeight: 600,
                                            color: group.color,
                                            mb: 0.5
                                        }}
                                    >
                                        {group.title}
                                    </Typography>
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                    >
                                        {group.subtitle}
                                    </Typography>
                                </Box>
                                <Chip
                                    label={`${group.features.length} features`}
                                    size="small"
                                    sx={{
                                        ml: 'auto',
                                        backgroundColor: `${group.color}20`,
                                        color: group.color,
                                        fontWeight: 600
                                    }}
                                />
                            </Stack>
                            <Divider sx={{ borderColor: `${group.color}30` }} />
                        </Box>

                        {/* Feature Cards */}
                        <Grid container spacing={2}>
                            {group.features.map((feature, featureIndex) => (
                                <Grid item xs={12} sm={6} md={4} lg={3} key={featureIndex}>
                                    <Card
                                        sx={{
                                            height: '100%',
                                            minHeight: 140,
                                            display: 'flex',
                                            flexDirection: 'column',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease-in-out',
                                            borderLeft: `3px solid ${feature.color}`,
                                            backgroundColor: 'background.paper',
                                            '&:hover': {
                                                transform: 'translateY(-4px)',
                                                boxShadow: 6,
                                                borderLeftWidth: '4px'
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
                                        <CardContent sx={{ flexGrow: 1, p: 2, '&:last-child': { pb: 2 } }}>
                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                                <Box sx={{ color: feature.color, display: 'flex', alignItems: 'center' }}>
                                                    {feature.icon}
                                                </Box>
                                                {feature.badge && (
                                                    <Chip
                                                        label={feature.badge}
                                                        size="small"
                                                        color="primary"
                                                        sx={{
                                                            height: 20,
                                                            fontSize: '0.65rem',
                                                            fontWeight: 'bold'
                                                        }}
                                                    />
                                                )}
                                            </Box>
                                            <Typography
                                                variant="subtitle1"
                                                sx={{
                                                    fontWeight: 600,
                                                    color: feature.color,
                                                    mb: 1,
                                                    fontSize: '0.95rem'
                                                }}
                                            >
                                                {feature.title}
                                            </Typography>
                                            <Typography
                                                variant="body2"
                                                color="text.secondary"
                                                sx={{
                                                    fontSize: '0.8rem',
                                                    lineHeight: 1.4,
                                                    mb: 1.5
                                                }}
                                            >
                                                {feature.description}
                                            </Typography>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                fullWidth
                                                sx={{
                                                    borderColor: feature.color,
                                                    color: feature.color,
                                                    fontSize: '0.75rem',
                                                    py: 0.5,
                                                    '&:hover': {
                                                        borderColor: feature.color,
                                                        backgroundColor: `${feature.color}10`
                                                    }
                                                }}
                                            >
                                                Open
                                            </Button>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            ))}
                        </Grid>
                    </Paper>
                ))}
            </Stack>
        </Box>
    );
}
