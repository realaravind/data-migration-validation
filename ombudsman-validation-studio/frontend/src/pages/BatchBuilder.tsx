import React, { useState, useEffect, useCallback } from 'react';
import {
    Box,
    Paper,
    Typography,
    TextField,
    Button,
    FormControl,
    FormLabel,
    RadioGroup,
    FormControlLabel,
    Radio,
    Checkbox,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Chip,
    Alert,
    CircularProgress,
    Divider,
    IconButton,
    Tooltip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Select,
    MenuItem,
    InputLabel,
    Grid
} from '@mui/material';
import {
    Save as SaveIcon,
    ArrowBack as ArrowBackIcon,
    Description as DescriptionIcon,
    Add as AddIcon,
    Delete as DeleteIcon,
    PlayArrow as PlayArrowIcon,
    BookmarkAdd as BookmarkAddIcon,
    Bookmarks as BookmarksIcon,
    DragIndicator as DragIndicatorIcon,
    AccessTime as AccessTimeIcon,
    TrendingFlat as TrendingFlatIcon,
    CallSplit as CallSplitIcon,
    CheckCircle as CheckCircleIcon,
    Visibility as VisibilityIcon,
    Schedule as ScheduleIcon,
    Event as EventIcon,
    FolderOpen as FolderOpenIcon,
    Star as StarIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';

interface Pipeline {
    filename: string;
    name: string;
    type: string;
    table?: string;
    validation_count?: number;
    pipeline_count?: number;
    batch_type?: string;
    description?: string;
    active?: boolean;
}

interface BatchConfig {
    name: string;
    description: string;
    type: 'sequential' | 'parallel';
    stopOnError: boolean;
    maxParallel: number;
    selectedPipelines: string[];
    schedule?: {
        enabled: boolean;
        frequency: 'daily' | 'weekly' | 'monthly' | 'cron' | 'windows';
        time: string; // HH:MM format
        dayOfWeek?: string; // For weekly
        dayOfMonth?: number; // For monthly
        cronExpression?: string; // For cron (Linux)
        windowsTaskXml?: string; // For Windows Task Scheduler
    };
}

interface BatchTemplate {
    template_id: string;
    filename: string;
    name: string;
    description: string;
    tags: string[];
    created_at: string;
    pipeline_count: number;
    batch_type: string;
}

const BatchBuilder: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const editBatchName = new URLSearchParams(location.search).get('edit');

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const [availablePipelines, setAvailablePipelines] = useState<Pipeline[]>([]);
    const [batchConfig, setBatchConfig] = useState<BatchConfig>({
        name: '',
        description: '',
        type: 'sequential',
        stopOnError: true,
        maxParallel: 3,
        selectedPipelines: []
    });

    // Template state
    const [availableTemplates, setAvailableTemplates] = useState<BatchTemplate[]>([]);
    const [showTemplateDialog, setShowTemplateDialog] = useState(false);
    const [showSaveTemplateDialog, setShowSaveTemplateDialog] = useState(false);
    const [templateName, setTemplateName] = useState('');
    const [templateDescription, setTemplateDescription] = useState('');
    const [templateTags, setTemplateTags] = useState('');

    // Load available pipelines and templates
    useEffect(() => {
        loadPipelines();
        loadTemplates();
    }, []);

    // Load existing batch if in edit mode
    useEffect(() => {
        if (editBatchName) {
            loadBatchConfig(editBatchName);
        }
    }, [editBatchName]);

    const loadPipelines = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get('http://localhost:8000/workload/pipelines/list');
            // Filter to show only individual pipelines (not batch files)
            const pipelines = response.data.pipelines.filter((p: Pipeline) => p.type === 'pipeline');
            setAvailablePipelines(pipelines);
        } catch (err: any) {
            setError(`Failed to load pipelines: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const loadBatchConfig = async (batchName: string) => {
        setLoading(true);
        setError(null);
        try {
            // Get active project first
            const projectResponse = await axios.get('http://localhost:8000/projects/active');
            const projectId = projectResponse.data.active_project.project_id;

            // Load the batch YAML file with project_id
            const response = await axios.get(`http://localhost:8000/workload/batch/${batchName}?project_id=${projectId}`);
            const batchData = response.data.batch;

            setBatchConfig({
                name: batchName.replace('_batch', ''),
                description: batchData.description || '',
                type: batchData.type || 'sequential',
                stopOnError: batchData.stop_on_error !== false,
                maxParallel: batchData.max_parallel || 3,
                selectedPipelines: batchData.pipelines?.map((p: any) => p.file) || []
            });
        } catch (err: any) {
            setError(`Failed to load batch configuration: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleTogglePipeline = useCallback((filename: string) => {
        setBatchConfig(prev => ({
            ...prev,
            selectedPipelines: prev.selectedPipelines.includes(filename)
                ? prev.selectedPipelines.filter(f => f !== filename)
                : [...prev.selectedPipelines, filename]
        }));
    }, []);

    const handleSelectAll = () => {
        setBatchConfig(prev => ({
            ...prev,
            selectedPipelines: availablePipelines.map(p => p.filename)
        }));
    };

    const handleDeselectAll = () => {
        setBatchConfig(prev => ({
            ...prev,
            selectedPipelines: []
        }));
    };

    const loadTemplates = async () => {
        try {
            const response = await axios.get('http://localhost:8000/workload/batch/templates/list');
            setAvailableTemplates(response.data.templates || []);
        } catch (err: any) {
            console.error('Failed to load templates:', err);
        }
    };

    const handleLoadFromTemplate = async (templateId: string) => {
        try {
            const response = await axios.get(`http://localhost:8000/workload/batch/templates/${templateId}`);
            const templateData = response.data;
            const batchData = templateData.batch;

            setBatchConfig({
                name: '',
                description: batchData.description || '',
                type: batchData.type || 'sequential',
                stopOnError: batchData.stop_on_error !== false,
                maxParallel: batchData.max_parallel || 3,
                selectedPipelines: batchData.pipelines?.map((p: any) => p.file) || []
            });

            setShowTemplateDialog(false);
            setSuccess(`Loaded configuration from template: ${templateData.template.name}`);
        } catch (err: any) {
            setError(`Failed to load template: ${err.message}`);
        }
    };

    const handleSaveAsTemplate = async () => {
        if (!templateName.trim()) {
            setError('Template name is required');
            return;
        }

        if (batchConfig.selectedPipelines.length === 0) {
            setError('Please select at least one pipeline before saving as template');
            return;
        }

        try {
            const tags = templateTags.split(',').map(t => t.trim()).filter(t => t);

            const batchYaml = {
                name: `${batchConfig.name || 'template'}_batch`,
                description: batchConfig.description,
                type: batchConfig.type,
                stop_on_error: batchConfig.stopOnError,
                max_parallel: batchConfig.type === 'parallel' ? batchConfig.maxParallel : undefined,
                pipelines: batchConfig.selectedPipelines.map(filename => ({
                    file: filename
                }))
            };

            await axios.post('http://localhost:8000/workload/batch/templates/save', {
                template_name: templateName,
                description: templateDescription,
                tags: tags,
                batch_config: batchYaml
            });

            setSuccess(`Template "${templateName}" saved successfully!`);
            setShowSaveTemplateDialog(false);
            setTemplateName('');
            setTemplateDescription('');
            setTemplateTags('');

            // Reload templates
            loadTemplates();
        } catch (err: any) {
            setError(`Failed to save template: ${err.message}`);
        }
    };

    const handleDragEnd = (result: DropResult) => {
        if (!result.destination) {
            return;
        }

        const items = Array.from(batchConfig.selectedPipelines);
        const [reorderedItem] = items.splice(result.source.index, 1);
        items.splice(result.destination.index, 0, reorderedItem);

        setBatchConfig(prev => ({
            ...prev,
            selectedPipelines: items
        }));
    };

    const handleSaveBatch = async () => {
        // Validation
        if (!batchConfig.name.trim()) {
            setError('Batch name is required');
            return;
        }

        if (batchConfig.selectedPipelines.length === 0) {
            setError('Please select at least one pipeline');
            return;
        }

        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            // Create batch YAML structure
            const batchYaml = {
                batch: {
                    name: `${batchConfig.name}_batch`,
                    description: batchConfig.description,
                    type: batchConfig.type,
                    stop_on_error: batchConfig.stopOnError,
                    max_parallel: batchConfig.type === 'parallel' ? batchConfig.maxParallel : undefined,
                    pipelines: batchConfig.selectedPipelines.map(filename => ({
                        file: filename
                    }))
                }
            };

            // Save the batch file
            await axios.post('http://localhost:8000/workload/batch/save', {
                filename: `${batchConfig.name}_batch.yaml`,
                content: batchYaml
            });

            setSuccess(`Batch "${batchConfig.name}_batch" saved successfully!`);

            // Navigate back to batch operations after 2 seconds
            setTimeout(() => {
                navigate('/batch');
            }, 2000);

        } catch (err: any) {
            setError(`Failed to save batch: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };

    return (
        <Box sx={{ p: 3 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <IconButton onClick={() => navigate('/batch')} sx={{ mr: 2 }}>
                    <ArrowBackIcon />
                </IconButton>
                <Typography variant="h4">
                    {editBatchName ? 'Edit Batch' : 'Create New Batch'}
                </Typography>
            </Box>

            {/* Error/Success Messages */}
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

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <Box sx={{ display: 'flex', gap: 3 }}>
                    {/* Left Panel - Batch Configuration */}
                    <Paper sx={{ p: 3, flex: 1 }}>
                        <Typography variant="h6" gutterBottom>
                            Batch Configuration
                        </Typography>

                        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                            {/* Batch Name */}
                            <TextField
                                label="Batch Name"
                                value={batchConfig.name}
                                onChange={(e) => setBatchConfig({ ...batchConfig, name: e.target.value })}
                                fullWidth
                                required
                                helperText="A unique name for this batch (without _batch suffix)"
                                disabled={!!editBatchName}
                            />

                            {/* Description */}
                            <TextField
                                label="Description"
                                value={batchConfig.description}
                                onChange={(e) => setBatchConfig({ ...batchConfig, description: e.target.value })}
                                fullWidth
                                multiline
                                rows={3}
                                helperText="Optional description of what this batch does"
                            />

                            <Divider />

                            {/* Execution Type */}
                            <FormControl component="fieldset">
                                <FormLabel component="legend">Execution Type</FormLabel>
                                <RadioGroup
                                    value={batchConfig.type}
                                    onChange={(e) => setBatchConfig({ ...batchConfig, type: e.target.value as 'sequential' | 'parallel' })}
                                >
                                    <FormControlLabel
                                        value="sequential"
                                        control={<Radio />}
                                        label="Sequential - Run pipelines one after another"
                                    />
                                    <FormControlLabel
                                        value="parallel"
                                        control={<Radio />}
                                        label="Parallel - Run multiple pipelines simultaneously"
                                    />
                                </RadioGroup>
                            </FormControl>

                            {/* Max Parallel (only for parallel execution) */}
                            {batchConfig.type === 'parallel' && (
                                <TextField
                                    label="Max Parallel Pipelines"
                                    type="number"
                                    value={batchConfig.maxParallel}
                                    onChange={(e) => setBatchConfig({ ...batchConfig, maxParallel: parseInt(e.target.value) || 3 })}
                                    fullWidth
                                    inputProps={{ min: 1, max: 10 }}
                                    helperText="Maximum number of pipelines to run in parallel (1-10)"
                                />
                            )}

                            <Divider />

                            {/* Stop on Error */}
                            <FormControlLabel
                                control={
                                    <Checkbox
                                        checked={batchConfig.stopOnError}
                                        onChange={(e) => setBatchConfig({ ...batchConfig, stopOnError: e.target.checked })}
                                    />
                                }
                                label="Stop execution if a pipeline fails"
                            />

                            <Divider />

                            {/* Scheduling */}
                            <Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    <ScheduleIcon fontSize="small" color="primary" />
                                    <Typography variant="subtitle2">
                                        Batch Scheduling
                                    </Typography>
                                </Box>
                                <FormControlLabel
                                    control={
                                        <Checkbox
                                            checked={batchConfig.schedule?.enabled || false}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    // Enable scheduling - create or update schedule object
                                                    setBatchConfig({
                                                        ...batchConfig,
                                                        schedule: {
                                                            ...(batchConfig.schedule || {}),
                                                            frequency: batchConfig.schedule?.frequency || 'daily',
                                                            time: batchConfig.schedule?.time || '00:00',
                                                            enabled: true
                                                        }
                                                    });
                                                } else {
                                                    // Disable scheduling - set enabled to false
                                                    setBatchConfig({
                                                        ...batchConfig,
                                                        schedule: {
                                                            ...(batchConfig.schedule || {}),
                                                            frequency: batchConfig.schedule?.frequency || 'daily',
                                                            time: batchConfig.schedule?.time || '00:00',
                                                            enabled: false
                                                        }
                                                    });
                                                }
                                            }}
                                        />
                                    }
                                    label="Enable automatic scheduling"
                                />

                                {batchConfig.schedule?.enabled && (
                                    <Box sx={{ mt: 2, ml: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                                        {/* Frequency Selection */}
                                        <FormControl fullWidth size="small">
                                            <InputLabel>Frequency</InputLabel>
                                            <Select
                                                value={batchConfig.schedule?.frequency || 'daily'}
                                                label="Frequency"
                                                onChange={(e) => setBatchConfig({
                                                    ...batchConfig,
                                                    schedule: {
                                                        ...batchConfig.schedule!,
                                                        frequency: e.target.value as 'daily' | 'weekly' | 'monthly' | 'cron' | 'windows'
                                                    }
                                                })}
                                            >
                                                <MenuItem value="daily">Daily</MenuItem>
                                                <MenuItem value="weekly">Weekly</MenuItem>
                                                <MenuItem value="monthly">Monthly</MenuItem>
                                                <MenuItem value="cron">Cron Expression (Linux/Unix)</MenuItem>
                                                <MenuItem value="windows">Windows Task Scheduler</MenuItem>
                                            </Select>
                                        </FormControl>

                                        {/* Time Selection */}
                                        {!['cron', 'windows'].includes(batchConfig.schedule?.frequency || '') && (
                                            <TextField
                                                label="Execution Time"
                                                type="time"
                                                value={batchConfig.schedule?.time || '00:00'}
                                                onChange={(e) => setBatchConfig({
                                                    ...batchConfig,
                                                    schedule: {
                                                        ...batchConfig.schedule!,
                                                        time: e.target.value
                                                    }
                                                })}
                                                size="small"
                                                fullWidth
                                                InputLabelProps={{ shrink: true }}
                                            />
                                        )}

                                        {/* Day of Week (for weekly) */}
                                        {batchConfig.schedule?.frequency === 'weekly' && (
                                            <FormControl fullWidth size="small">
                                                <InputLabel>Day of Week</InputLabel>
                                                <Select
                                                    value={batchConfig.schedule?.dayOfWeek || 'Monday'}
                                                    label="Day of Week"
                                                    onChange={(e) => setBatchConfig({
                                                        ...batchConfig,
                                                        schedule: {
                                                            ...batchConfig.schedule!,
                                                            dayOfWeek: e.target.value
                                                        }
                                                    })}
                                                >
                                                    <MenuItem value="Monday">Monday</MenuItem>
                                                    <MenuItem value="Tuesday">Tuesday</MenuItem>
                                                    <MenuItem value="Wednesday">Wednesday</MenuItem>
                                                    <MenuItem value="Thursday">Thursday</MenuItem>
                                                    <MenuItem value="Friday">Friday</MenuItem>
                                                    <MenuItem value="Saturday">Saturday</MenuItem>
                                                    <MenuItem value="Sunday">Sunday</MenuItem>
                                                </Select>
                                            </FormControl>
                                        )}

                                        {/* Day of Month (for monthly) */}
                                        {batchConfig.schedule?.frequency === 'monthly' && (
                                            <TextField
                                                label="Day of Month"
                                                type="number"
                                                value={batchConfig.schedule?.dayOfMonth || 1}
                                                onChange={(e) => setBatchConfig({
                                                    ...batchConfig,
                                                    schedule: {
                                                        ...batchConfig.schedule!,
                                                        dayOfMonth: parseInt(e.target.value) || 1
                                                    }
                                                })}
                                                size="small"
                                                fullWidth
                                                inputProps={{ min: 1, max: 31 }}
                                                helperText="Enter 1-31 for day of month"
                                            />
                                        )}

                                        {/* Cron Expression (Linux/Unix) */}
                                        {batchConfig.schedule?.frequency === 'cron' && (
                                            <Box>
                                                <TextField
                                                    label="Cron Expression"
                                                    value={batchConfig.schedule?.cronExpression || '0 0 * * *'}
                                                    onChange={(e) => setBatchConfig({
                                                        ...batchConfig,
                                                        schedule: {
                                                            ...batchConfig.schedule!,
                                                            cronExpression: e.target.value
                                                        }
                                                    })}
                                                    size="small"
                                                    fullWidth
                                                    helperText="Format: minute hour day month weekday"
                                                    placeholder="0 0 * * *"
                                                />
                                                <Alert severity="info" sx={{ mt: 1 }}>
                                                    <Typography variant="caption" display="block" fontWeight="medium">Examples:</Typography>
                                                    <Typography variant="caption" display="block">• 0 2 * * * - Daily at 2:00 AM</Typography>
                                                    <Typography variant="caption" display="block">• 0 9 * * 1 - Every Monday at 9:00 AM</Typography>
                                                    <Typography variant="caption" display="block">• 0 0 1 * * - First day of month at midnight</Typography>
                                                </Alert>
                                            </Box>
                                        )}

                                        {/* Windows Task Scheduler */}
                                        {batchConfig.schedule?.frequency === 'windows' && (
                                            <Box>
                                                <Alert severity="info" sx={{ mb: 2 }}>
                                                    <Typography variant="caption" fontWeight="medium">
                                                        Windows Task Scheduler Configuration
                                                    </Typography>
                                                </Alert>

                                                {/* Trigger Type */}
                                                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                                                    <InputLabel>Trigger Type</InputLabel>
                                                    <Select
                                                        value={batchConfig.schedule?.windowsTaskXml?.includes('Daily') ? 'daily' :
                                                               batchConfig.schedule?.windowsTaskXml?.includes('Weekly') ? 'weekly' :
                                                               batchConfig.schedule?.windowsTaskXml?.includes('Monthly') ? 'monthly' : 'daily'}
                                                        label="Trigger Type"
                                                        size="small"
                                                    >
                                                        <MenuItem value="daily">Daily</MenuItem>
                                                        <MenuItem value="weekly">Weekly</MenuItem>
                                                        <MenuItem value="monthly">Monthly</MenuItem>
                                                        <MenuItem value="boot">At system startup</MenuItem>
                                                        <MenuItem value="logon">At logon</MenuItem>
                                                    </Select>
                                                </FormControl>

                                                <TextField
                                                    label="Start Time"
                                                    type="time"
                                                    value={batchConfig.schedule?.time || '00:00'}
                                                    onChange={(e) => setBatchConfig({
                                                        ...batchConfig,
                                                        schedule: {
                                                            ...batchConfig.schedule!,
                                                            time: e.target.value
                                                        }
                                                    })}
                                                    size="small"
                                                    fullWidth
                                                    InputLabelProps={{ shrink: true }}
                                                    sx={{ mb: 2 }}
                                                />

                                                <Alert severity="success" icon={<CheckCircleIcon />}>
                                                    <Typography variant="caption" fontWeight="medium">PowerShell Command:</Typography>
                                                    <Typography variant="caption" display="block" sx={{
                                                        fontFamily: 'monospace',
                                                        bgcolor: 'rgba(0,0,0,0.05)',
                                                        p: 1,
                                                        mt: 0.5,
                                                        borderRadius: 0.5,
                                                        wordBreak: 'break-all'
                                                    }}>
                                                        {`schtasks /create /tn "Ombudsman_${batchConfig.name || 'Batch'}" /tr "python run_batch.py ${batchConfig.name || 'batch'}_batch.yaml" /sc daily /st ${batchConfig.schedule?.time || '00:00'}`}
                                                    </Typography>
                                                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                                        Copy and run this command in PowerShell (as Administrator) to create the scheduled task.
                                                    </Typography>
                                                </Alert>
                                            </Box>
                                        )}

                                        {/* Schedule Preview */}
                                        {batchConfig.schedule?.frequency !== 'windows' && (
                                            <Alert severity="info" icon={<EventIcon />}>
                                                <Typography variant="caption" fontWeight="medium">
                                                    Next execution:
                                                </Typography>
                                                <Typography variant="caption" display="block">
                                                    {batchConfig.schedule?.frequency === 'daily' && `Daily at ${batchConfig.schedule?.time || '00:00'}`}
                                                    {batchConfig.schedule?.frequency === 'weekly' && `Every ${batchConfig.schedule?.dayOfWeek || 'Monday'} at ${batchConfig.schedule?.time || '00:00'}`}
                                                    {batchConfig.schedule?.frequency === 'monthly' && `Day ${batchConfig.schedule?.dayOfMonth || 1} of each month at ${batchConfig.schedule?.time || '00:00'}`}
                                                    {batchConfig.schedule?.frequency === 'cron' && `Cron: ${batchConfig.schedule?.cronExpression || '0 0 * * *'}`}
                                                </Typography>
                                            </Alert>
                                        )}
                                    </Box>
                                )}
                            </Box>

                            <Divider />

                            {/* Template Actions */}
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button
                                    variant="outlined"
                                    startIcon={<BookmarksIcon />}
                                    onClick={() => setShowTemplateDialog(true)}
                                    fullWidth
                                >
                                    Load from Template
                                </Button>
                                <Button
                                    variant="outlined"
                                    startIcon={<BookmarkAddIcon />}
                                    onClick={() => setShowSaveTemplateDialog(true)}
                                    fullWidth
                                    disabled={batchConfig.selectedPipelines.length === 0}
                                >
                                    Save as Template
                                </Button>
                            </Box>

                            <Divider />

                            {/* Execution Preview */}
                            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                                    <VisibilityIcon fontSize="small" color="primary" />
                                    <Typography variant="subtitle2">
                                        Execution Preview
                                    </Typography>
                                </Box>

                                {/* Basic Info */}
                                <Box sx={{ mb: 2 }}>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        Name: <strong>{batchConfig.name || '(not set)'}_batch</strong>
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" gutterBottom>
                                        Pipelines: <strong>{batchConfig.selectedPipelines.length}</strong>
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        Mode: <strong>{batchConfig.type === 'parallel' ? `Parallel (max ${batchConfig.maxParallel})` : 'Sequential'}</strong>
                                    </Typography>
                                </Box>

                                {/* Estimated Time */}
                                {batchConfig.selectedPipelines.length > 0 && (
                                    <Box sx={{ mb: 2, p: 1.5, bgcolor: 'info.light', borderRadius: 1 }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <AccessTimeIcon fontSize="small" />
                                            <Typography variant="body2" fontWeight="medium">
                                                Estimated Time:
                                            </Typography>
                                        </Box>
                                        <Typography variant="h6" sx={{ ml: 3, mt: 0.5 }}>
                                            {batchConfig.type === 'parallel'
                                                ? `~${Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) * 2}-${Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) * 5} min`
                                                : `~${batchConfig.selectedPipelines.length * 2}-${batchConfig.selectedPipelines.length * 5} min`
                                            }
                                        </Typography>
                                        <Typography variant="caption" sx={{ ml: 3, color: 'text.secondary' }}>
                                            {batchConfig.type === 'parallel'
                                                ? `${Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel)} batch${Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) > 1 ? 'es' : ''} of ${batchConfig.maxParallel} pipeline${batchConfig.maxParallel > 1 ? 's' : ''}`
                                                : `${batchConfig.selectedPipelines.length} pipeline${batchConfig.selectedPipelines.length > 1 ? 's' : ''} in sequence`
                                            }
                                        </Typography>
                                    </Box>
                                )}

                                {/* Execution Flow Visualization */}
                                {batchConfig.selectedPipelines.length > 0 && (
                                    <Box sx={{ mb: 2 }}>
                                        <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                                            Execution Flow:
                                        </Typography>
                                        <Box sx={{
                                            p: 1.5,
                                            border: '1px dashed',
                                            borderColor: 'divider',
                                            borderRadius: 1,
                                            bgcolor: 'background.paper'
                                        }}>
                                            {batchConfig.type === 'sequential' ? (
                                                // Sequential flow
                                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                                    {batchConfig.selectedPipelines.slice(0, 5).map((filename, index) => {
                                                        const pipeline = availablePipelines.find(p => p.filename === filename);
                                                        return (
                                                            <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                                <Chip label={`#${index + 1}`} size="small" color="primary" sx={{ width: 40 }} />
                                                                <TrendingFlatIcon fontSize="small" color="action" />
                                                                <Typography variant="caption" sx={{
                                                                    overflow: 'hidden',
                                                                    textOverflow: 'ellipsis',
                                                                    whiteSpace: 'nowrap',
                                                                    flex: 1
                                                                }}>
                                                                    {pipeline?.table || pipeline?.name || filename}
                                                                </Typography>
                                                            </Box>
                                                        );
                                                    })}
                                                    {batchConfig.selectedPipelines.length > 5 && (
                                                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                                                            ... and {batchConfig.selectedPipelines.length - 5} more
                                                        </Typography>
                                                    )}
                                                </Box>
                                            ) : (
                                                // Parallel flow
                                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                                    {Array.from({ length: Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) }).slice(0, 3).map((_, batchIndex) => {
                                                        const startIdx = batchIndex * batchConfig.maxParallel;
                                                        const batchPipelines = batchConfig.selectedPipelines.slice(startIdx, startIdx + batchConfig.maxParallel);
                                                        return (
                                                            <Box key={batchIndex}>
                                                                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                                                                    Batch {batchIndex + 1}:
                                                                </Typography>
                                                                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', ml: 1 }}>
                                                                    {batchPipelines.map((filename, idx) => {
                                                                        const pipeline = availablePipelines.find(p => p.filename === filename);
                                                                        return (
                                                                            <Chip
                                                                                key={idx}
                                                                                label={pipeline?.table?.split('_').pop() || `P${startIdx + idx + 1}`}
                                                                                size="small"
                                                                                variant="outlined"
                                                                                sx={{ fontSize: '0.7rem' }}
                                                                            />
                                                                        );
                                                                    })}
                                                                    <CallSplitIcon fontSize="small" color="action" sx={{ ml: 0.5 }} />
                                                                </Box>
                                                            </Box>
                                                        );
                                                    })}
                                                    {Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) > 3 && (
                                                        <Typography variant="caption" color="text.secondary">
                                                            ... {Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) - 3} more batch{Math.ceil(batchConfig.selectedPipelines.length / batchConfig.maxParallel) - 3 > 1 ? 'es' : ''}
                                                        </Typography>
                                                    )}
                                                </Box>
                                            )}
                                        </Box>
                                    </Box>
                                )}

                                {/* Error Handling */}
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: batchConfig.stopOnError ? 'error.light' : 'success.light', borderRadius: 1 }}>
                                    <CheckCircleIcon fontSize="small" />
                                    <Typography variant="caption">
                                        {batchConfig.stopOnError ? 'Stops on first error' : 'Continues on errors'}
                                    </Typography>
                                </Box>
                            </Box>

                            {/* Template Buttons */}
                            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                                <Button
                                    variant="outlined"
                                    startIcon={<FolderOpenIcon />}
                                    onClick={() => setShowTemplateDialog(true)}
                                    fullWidth
                                    size="small"
                                >
                                    Load Template
                                </Button>
                                <Button
                                    variant="outlined"
                                    startIcon={<StarIcon />}
                                    onClick={() => setShowSaveTemplateDialog(true)}
                                    disabled={batchConfig.selectedPipelines.length === 0}
                                    fullWidth
                                    size="small"
                                >
                                    Save as Template
                                </Button>
                            </Box>

                            {/* Save Button */}
                            <Button
                                variant="contained"
                                startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                                onClick={handleSaveBatch}
                                disabled={saving || !batchConfig.name.trim() || batchConfig.selectedPipelines.length === 0}
                                fullWidth
                                size="large"
                            >
                                {saving ? 'Saving...' : editBatchName ? 'Update Batch' : 'Create Batch'}
                            </Button>
                        </Box>
                    </Paper>

                    {/* Right Panel - Pipeline Selection */}
                    <Paper sx={{ p: 3, flex: 1, maxHeight: '80vh', overflow: 'auto' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h6">
                                Select Pipelines ({batchConfig.selectedPipelines.length}/{availablePipelines.length})
                            </Typography>
                            <Box>
                                <Button size="small" onClick={handleSelectAll} sx={{ mr: 1 }}>
                                    Select All
                                </Button>
                                <Button size="small" onClick={handleDeselectAll}>
                                    Deselect All
                                </Button>
                            </Box>
                        </Box>

                        {availablePipelines.length === 0 ? (
                            <Alert severity="info">
                                No pipelines available. Please create validation pipelines first.
                            </Alert>
                        ) : (
                            <List>
                                {availablePipelines.map((pipeline) => {
                                    const isSelected = batchConfig.selectedPipelines.includes(pipeline.filename);
                                    return (
                                        <ListItem
                                            key={pipeline.filename}
                                            sx={{
                                                border: '1px solid',
                                                borderColor: 'divider',
                                                borderRadius: 1,
                                                mb: 1,
                                                bgcolor: isSelected ? 'action.selected' : 'background.paper'
                                            }}
                                        >
                                            <ListItemIcon>
                                                <Checkbox
                                                    edge="start"
                                                    checked={isSelected}
                                                    onChange={() => handleTogglePipeline(pipeline.filename)}
                                                    tabIndex={-1}
                                                />
                                            </ListItemIcon>
                                            <ListItemIcon>
                                                <DescriptionIcon color="action" />
                                            </ListItemIcon>
                                            <ListItemText
                                                primary={
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                                            {pipeline.name || pipeline.filename}
                                                        </Typography>
                                                        {isSelected && (
                                                            <Chip
                                                                label="SELECTED"
                                                                size="small"
                                                                color="primary"
                                                            />
                                                        )}
                                                    </Box>
                                                }
                                                secondary={`Table: ${pipeline.table || 'Not specified'} • ${pipeline.validation_count || 0} validations`}
                                            />
                                        </ListItem>
                                    );
                                })}
                            </List>
                        )}
                    </Paper>
                </Box>
            )}

            {/* Load from Template Dialog */}
            <Dialog open={showTemplateDialog} onClose={() => setShowTemplateDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Load Batch Configuration from Template</DialogTitle>
                <DialogContent>
                    {availableTemplates.length === 0 ? (
                        <Alert severity="info">
                            No templates available. Create a batch configuration and save it as a template first.
                        </Alert>
                    ) : (
                        <List>
                            {availableTemplates.map((template) => (
                                <ListItem
                                    key={template.template_id}
                                    button
                                    onClick={() => handleLoadFromTemplate(template.template_id)}
                                    sx={{
                                        border: '1px solid',
                                        borderColor: 'divider',
                                        borderRadius: 1,
                                        mb: 1,
                                        '&:hover': {
                                            bgcolor: 'action.hover'
                                        }
                                    }}
                                >
                                    <ListItemIcon>
                                        <BookmarksIcon color="primary" />
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={template.name}
                                        secondary={
                                            <>
                                                <Typography variant="body2" component="span">
                                                    {template.description || 'No description'}
                                                </Typography>
                                                <br />
                                                <Typography variant="caption" component="span">
                                                    {template.pipeline_count} pipelines • {template.batch_type}
                                                </Typography>
                                                {template.tags && template.tags.length > 0 && (
                                                    <Box sx={{ mt: 0.5 }}>
                                                        {template.tags.map((tag, idx) => (
                                                            <Chip
                                                                key={idx}
                                                                label={tag}
                                                                size="small"
                                                                sx={{ mr: 0.5, mb: 0.5 }}
                                                            />
                                                        ))}
                                                    </Box>
                                                )}
                                            </>
                                        }
                                    />
                                </ListItem>
                            ))}
                        </List>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowTemplateDialog(false)}>Cancel</Button>
                </DialogActions>
            </Dialog>

            {/* Save as Template Dialog */}
            <Dialog open={showSaveTemplateDialog} onClose={() => setShowSaveTemplateDialog(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Save as Template</DialogTitle>
                <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                        <TextField
                            label="Template Name"
                            value={templateName}
                            onChange={(e) => setTemplateName(e.target.value)}
                            fullWidth
                            required
                            helperText="A descriptive name for this template"
                        />
                        <TextField
                            label="Description"
                            value={templateDescription}
                            onChange={(e) => setTemplateDescription(e.target.value)}
                            fullWidth
                            multiline
                            rows={3}
                            helperText="What this template is for"
                        />
                        <TextField
                            label="Tags (comma-separated)"
                            value={templateTags}
                            onChange={(e) => setTemplateTags(e.target.value)}
                            fullWidth
                            helperText="E.g., dimensions, facts, daily"
                        />
                        <Alert severity="info">
                            This template will save the current batch configuration ({batchConfig.selectedPipelines.length} pipelines)
                            as a reusable template.
                        </Alert>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setShowSaveTemplateDialog(false)}>Cancel</Button>
                    <Button
                        variant="contained"
                        onClick={handleSaveAsTemplate}
                        disabled={!templateName.trim()}
                    >
                        Save Template
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default BatchBuilder;
