import { Box, Card, CardContent, Typography, Grid, Chip, Accordion, AccordionSummary, AccordionDetails, Alert, Button, IconButton, Tooltip } from '@mui/material';
import { ExpandMore, CheckCircle, Warning, Info, ContentCopy, TrendingUp, Build, Speed } from '@mui/icons-material';
import { useState } from 'react';

interface Recommendation {
    priority: string;
    title: string;
    description: string;
    action_items: string[];
    commands: string[];
    effort: string;
    impact: string;
    affected_count: number;
    category: string;
    affected_steps?: string[];
}

interface RecommendationsListProps {
    recommendations: Recommendation[];
    runId?: string;
    onStepClick?: (runId: string, stepName: string) => void;
}

export default function RecommendationsList({ recommendations, runId, onStepClick }: RecommendationsListProps) {
    const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

    if (!recommendations || recommendations.length === 0) {
        return (
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Actionable Recommendations
                    </Typography>
                    <Alert severity="success">
                        No recommendations needed. All validations are performing well!
                    </Alert>
                </CardContent>
            </Card>
        );
    }

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'P1':
                return '#d32f2f';
            case 'P2':
                return '#f57c00';
            case 'P3':
                return '#1976d2';
            default:
                return '#9e9e9e';
        }
    };

    const getPriorityIcon = (priority: string) => {
        switch (priority) {
            case 'P1':
                return <Warning sx={{ color: '#d32f2f', fontSize: 28 }} />;
            case 'P2':
                return <Warning sx={{ color: '#f57c00', fontSize: 28 }} />;
            case 'P3':
                return <Info sx={{ color: '#1976d2', fontSize: 28 }} />;
            default:
                return <CheckCircle sx={{ color: '#4caf50', fontSize: 28 }} />;
        }
    };

    const getEffortIcon = (effort: string) => {
        if (effort === 'High') return <Build sx={{ fontSize: 18 }} />;
        if (effort === 'Medium') return <Build sx={{ fontSize: 18 }} />;
        return <Speed sx={{ fontSize: 18 }} />;
    };

    const getImpactColor = (impact: string) => {
        if (impact === 'High') return '#d32f2f';
        if (impact === 'Medium') return '#f57c00';
        return '#4caf50';
    };

    const copyToClipboard = (text: string, index: number) => {
        navigator.clipboard.writeText(text).then(() => {
            setCopiedIndex(index);
            setTimeout(() => setCopiedIndex(null), 2000);
        });
    };

    // Group by priority
    const p1Recommendations = recommendations.filter(r => r.priority === 'P1');
    const p2Recommendations = recommendations.filter(r => r.priority === 'P2');
    const p3Recommendations = recommendations.filter(r => r.priority === 'P3');

    return (
        <Card sx={{ mb: 3 }}>
            <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingUp />
                    Actionable Recommendations
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 2 }}>
                    Priority-classified actions to improve migration readiness
                </Typography>

                {/* Summary Stats */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#ffebee', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#d32f2f' }}>
                                {p1Recommendations.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                P1 Critical
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#fff3e0', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#f57c00' }}>
                                {p2Recommendations.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                P2 High Priority
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                        <Box sx={{ p: 2, backgroundColor: '#e3f2fd', borderRadius: 2, textAlign: 'center' }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#1976d2' }}>
                                {p3Recommendations.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                P3 Medium Priority
                            </Typography>
                        </Box>
                    </Grid>
                </Grid>

                {/* Recommendations List */}
                <Box>
                    {recommendations.map((rec, index) => (
                        <Accordion key={index} sx={{ mb: 1, '&:before': { display: 'none' } }}>
                            <AccordionSummary
                                expandIcon={<ExpandMore />}
                                sx={{
                                    backgroundColor: getPriorityColor(rec.priority) + '10',
                                    borderLeft: `4px solid ${getPriorityColor(rec.priority)}`,
                                    '&:hover': {
                                        backgroundColor: getPriorityColor(rec.priority) + '20'
                                    }
                                }}
                            >
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                                    {getPriorityIcon(rec.priority)}
                                    <Box sx={{ flexGrow: 1 }}>
                                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                            {rec.title}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {rec.description}
                                        </Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                                        <Chip
                                            label={rec.priority}
                                            size="small"
                                            sx={{
                                                backgroundColor: getPriorityColor(rec.priority),
                                                color: 'white',
                                                fontWeight: 'bold'
                                            }}
                                        />
                                        <Chip
                                            icon={getEffortIcon(rec.effort)}
                                            label={`Effort: ${rec.effort}`}
                                            size="small"
                                            variant="outlined"
                                        />
                                        <Chip
                                            label={`Impact: ${rec.impact}`}
                                            size="small"
                                            variant="outlined"
                                            sx={{
                                                borderColor: getImpactColor(rec.impact),
                                                color: getImpactColor(rec.impact)
                                            }}
                                        />
                                    </Box>
                                </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                                <Grid container spacing={2}>
                                    {/* Action Items */}
                                    <Grid item xs={12} md={6}>
                                        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                            Action Items
                                        </Typography>
                                        <Box sx={{ p: 1, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                                            {rec.action_items.map((item, idx) => (
                                                <Box key={idx} sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                                                    <CheckCircle sx={{ fontSize: 16, color: '#4caf50', mr: 1, mt: 0.3 }} />
                                                    <Typography variant="body2">
                                                        {item}
                                                    </Typography>
                                                </Box>
                                            ))}
                                        </Box>
                                    </Grid>

                                    {/* Commands */}
                                    {rec.commands && rec.commands.length > 0 && (
                                        <Grid item xs={12} md={6}>
                                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                                Commands & Examples
                                            </Typography>
                                            <Box sx={{ position: 'relative' }}>
                                                <Box sx={{
                                                    p: 2,
                                                    backgroundColor: '#263238',
                                                    borderRadius: 1,
                                                    fontFamily: 'monospace',
                                                    fontSize: '0.85rem',
                                                    color: '#fff',
                                                    maxHeight: 200,
                                                    overflow: 'auto'
                                                }}>
                                                    {rec.commands.map((cmd, idx) => (
                                                        <Typography
                                                            key={idx}
                                                            variant="body2"
                                                            sx={{
                                                                fontFamily: 'monospace',
                                                                color: cmd.startsWith('#') ? '#81c784' : '#fff',
                                                                mb: 0.5
                                                            }}
                                                        >
                                                            {cmd}
                                                        </Typography>
                                                    ))}
                                                </Box>
                                                <Tooltip title={copiedIndex === index ? "Copied!" : "Copy commands"}>
                                                    <IconButton
                                                        size="small"
                                                        onClick={() => copyToClipboard(rec.commands.join('\n'), index)}
                                                        sx={{
                                                            position: 'absolute',
                                                            top: 8,
                                                            right: 8,
                                                            color: 'white',
                                                            backgroundColor: 'rgba(0,0,0,0.3)',
                                                            '&:hover': {
                                                                backgroundColor: 'rgba(0,0,0,0.5)'
                                                            }
                                                        }}
                                                    >
                                                        <ContentCopy sx={{ fontSize: 18 }} />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        </Grid>
                                    )}

                                    {/* Affected Steps */}
                                    {rec.affected_steps && rec.affected_steps.length > 0 && (
                                        <Grid item xs={12}>
                                            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                                Affected Validation Steps
                                            </Typography>
                                            <Box sx={{ maxHeight: 200, overflow: 'auto', p: 1, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                                                {rec.affected_steps.map((step, idx) => (
                                                    <Typography
                                                        key={idx}
                                                        variant="body2"
                                                        sx={{
                                                            mb: 0.5,
                                                            fontFamily: 'monospace',
                                                            cursor: runId && onStepClick ? 'pointer' : 'default',
                                                            color: runId && onStepClick ? 'primary.main' : 'text.primary',
                                                            '&:hover': runId && onStepClick ? {
                                                                textDecoration: 'underline',
                                                                color: 'primary.dark'
                                                            } : {}
                                                        }}
                                                        onClick={() => runId && onStepClick && onStepClick(runId, step)}
                                                    >
                                                        {idx + 1}. {step}
                                                    </Typography>
                                                ))}
                                            </Box>
                                        </Grid>
                                    )}

                                    {/* Metadata */}
                                    <Grid item xs={12}>
                                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1 }}>
                                            <Chip
                                                label={`Category: ${rec.category}`}
                                                size="small"
                                                variant="outlined"
                                            />
                                            {rec.affected_count > 0 && (
                                                <Chip
                                                    label={`${rec.affected_count} affected items`}
                                                    size="small"
                                                    variant="outlined"
                                                    color="warning"
                                                />
                                            )}
                                        </Box>
                                    </Grid>
                                </Grid>
                            </AccordionDetails>
                        </Accordion>
                    ))}
                </Box>

                {/* Help Text */}
                <Alert severity="info" sx={{ mt: 3 }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        Priority Legend:
                    </Typography>
                    <Typography variant="caption" component="div">
                        P1 (Critical) - Address immediately, blocks migration progress
                    </Typography>
                    <Typography variant="caption" component="div">
                        P2 (High) - Address soon, significant impact on quality
                    </Typography>
                    <Typography variant="caption" component="div">
                        P3 (Medium) - Address after P1/P2, improvements and optimizations
                    </Typography>
                </Alert>
            </CardContent>
        </Card>
    );
}
