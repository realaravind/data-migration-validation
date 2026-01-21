import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Switch,
  FormControlLabel,
  Divider,
  Chip,
  IconButton,
  InputAdornment,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import {
  Save as SaveIcon,
  Close as CloseIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface AzureDevOpsConfig {
  enabled: boolean;
  organization_url: string;
  project_name: string;
  pat_token: string;
  work_item_type: string;
  area_path: string;
  iteration_path: string;
  assigned_to: string;
  auto_tags: string[];
  tag_prefix: string;
}

interface Project {
  project_id: string;
  name: string;
  description: string;
  azure_devops?: AzureDevOpsConfig;
}

export default function ProjectSettings() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [showPatToken, setShowPatToken] = useState(false);

  // Form state
  const [enabled, setEnabled] = useState(false);
  const [organizationUrl, setOrganizationUrl] = useState('');
  const [projectName, setProjectName] = useState('');
  const [patToken, setPatToken] = useState('');
  const [workItemType, setWorkItemType] = useState('Bug');
  const [areaPath, setAreaPath] = useState('');
  const [iterationPath, setIterationPath] = useState('');
  const [assignedTo, setAssignedTo] = useState('');
  const [autoTagsInput, setAutoTagsInput] = useState('');
  const [tagPrefix, setTagPrefix] = useState('OVS-');

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const fetchProject = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`http://localhost:8000/projects/${projectId}`);
      if (!response.ok) {
        throw new Error(`Failed to load project: ${response.status}`);
      }

      const data = await response.json();
      setProject(data.metadata);

      // Populate form with existing Azure DevOps config
      if (data.metadata.azure_devops) {
        const config = data.metadata.azure_devops;
        setEnabled(config.enabled || false);
        setOrganizationUrl(config.organization_url || '');
        setProjectName(config.project_name || '');
        setPatToken(config.pat_token || '');
        setWorkItemType(config.work_item_type || 'Bug');
        setAreaPath(config.area_path || '');
        setIterationPath(config.iteration_path || '');
        setAssignedTo(config.assigned_to || '');
        setAutoTagsInput(config.auto_tags?.join(', ') || 'ombudsman, data-validation');
        setTagPrefix(config.tag_prefix || 'OVS-');
      } else {
        // Set defaults
        setAutoTagsInput('ombudsman, data-validation');
      }
    } catch (err: any) {
      console.error('Error loading project:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8000/projects/${projectId}/azure-devops/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          organization_url: organizationUrl,
          project_name: projectName,
          pat_token: patToken,
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setTestResult({
          success: true,
          message: `Connection successful! Connected to project: ${result.project_name}`,
        });
      } else {
        setTestResult({
          success: false,
          message: result.message || 'Connection failed',
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: `Connection error: ${err.message}`,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const autoTags = autoTagsInput
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);

      const config: AzureDevOpsConfig = {
        enabled,
        organization_url: organizationUrl,
        project_name: projectName,
        pat_token: patToken,
        work_item_type: workItemType,
        area_path: areaPath,
        iteration_path: iterationPath,
        assigned_to: assignedTo,
        auto_tags: autoTags,
        tag_prefix: tagPrefix,
      };

      const token = localStorage.getItem('auth_token');
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`http://localhost:8000/projects/${projectId}/azure-devops/configure`, {
        method: 'POST',
        headers,
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error(`Failed to save configuration: ${response.status}`);
      }

      const result = await response.json();
      setSuccess('Azure DevOps configuration saved successfully!');

      // Refresh project data
      fetchProject();
    } catch (err: any) {
      console.error('Error saving configuration:', err);
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading project settings...</Typography>
      </Box>
    );
  }

  if (!project) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Project not found</Alert>
        <Button onClick={() => navigate('/projects')} sx={{ mt: 2 }}>
          Back to Projects
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <Box>
            <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SettingsIcon fontSize="large" />
              Project Settings
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {project.name} • Project ID: {project.project_id}
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<CloseIcon />}
            onClick={() => navigate('/projects')}
          >
            Close
          </Button>
        </Box>
      </Paper>

      {/* Alerts */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      {/* Azure DevOps Configuration */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">Azure DevOps Integration</Typography>
          <FormControlLabel
            control={
              <Switch
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                color="primary"
              />
            }
            label={enabled ? 'Enabled' : 'Disabled'}
          />
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Connection Settings */}
        <Card sx={{ mb: 3, bgcolor: 'background.default' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Connection Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Configure your Azure DevOps organization and project details
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Organization URL"
                  value={organizationUrl}
                  onChange={(e) => setOrganizationUrl(e.target.value)}
                  placeholder="https://dev.azure.com/your-organization"
                  helperText="Your Azure DevOps organization URL"
                  disabled={!enabled}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Project Name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="YourAzureDevOpsProject"
                  helperText="The name of your Azure DevOps project"
                  disabled={!enabled}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Personal Access Token (PAT)"
                  type={showPatToken ? 'text' : 'password'}
                  value={patToken}
                  onChange={(e) => setPatToken(e.target.value)}
                  placeholder="Enter your PAT token"
                  helperText="Token must have work item read/write permissions"
                  disabled={!enabled}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPatToken(!showPatToken)}
                          edge="end"
                        >
                          {showPatToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
            </Grid>

            {/* Test Connection */}
            <Box sx={{ mt: 2 }}>
              <Button
                variant="outlined"
                onClick={handleTestConnection}
                disabled={!enabled || !organizationUrl || !projectName || !patToken || testing}
                startIcon={testing ? <CircularProgress size={20} /> : null}
              >
                {testing ? 'Testing Connection...' : 'Test Connection'}
              </Button>

              {testResult && (
                <Alert
                  severity={testResult.success ? 'success' : 'error'}
                  sx={{ mt: 2 }}
                  icon={testResult.success ? <CheckCircleIcon /> : <ErrorIcon />}
                >
                  {testResult.message}
                </Alert>
              )}
            </Box>
          </CardContent>
        </Card>

        {/* Work Item Settings */}
        <Card sx={{ mb: 3, bgcolor: 'background.default' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Work Item Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Configure default settings for created work items
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Work Item Type"
                  value={workItemType}
                  onChange={(e) => setWorkItemType(e.target.value)}
                  placeholder="Bug"
                  helperText="Default work item type (Bug, Task, User Story, Issue)"
                  disabled={!enabled}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Assigned To"
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                  placeholder="user@example.com"
                  helperText="Default assignee email (optional)"
                  disabled={!enabled}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Area Path"
                  value={areaPath}
                  onChange={(e) => setAreaPath(e.target.value)}
                  placeholder="YourProject\\DataMigration"
                  helperText="Default area path (optional)"
                  disabled={!enabled}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Iteration Path"
                  value={iterationPath}
                  onChange={(e) => setIterationPath(e.target.value)}
                  placeholder="YourProject\\Sprint 1"
                  helperText="Default iteration path (optional)"
                  disabled={!enabled}
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Tagging Settings */}
        <Card sx={{ bgcolor: 'background.default' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Tagging Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Configure automatic tags for created work items
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  label="Auto Tags"
                  value={autoTagsInput}
                  onChange={(e) => setAutoTagsInput(e.target.value)}
                  placeholder="ombudsman, data-validation"
                  helperText="Comma-separated list of tags to automatically add"
                  disabled={!enabled}
                />
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {autoTagsInput.split(',').map((tag, idx) => {
                    const trimmedTag = tag.trim();
                    if (!trimmedTag) return null;
                    return (
                      <Chip
                        key={idx}
                        label={trimmedTag}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    );
                  })}
                </Box>
              </Grid>

              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Tag Prefix"
                  value={tagPrefix}
                  onChange={(e) => setTagPrefix(e.target.value)}
                  placeholder="OVS-"
                  helperText="Prefix for bug IDs in tags"
                  disabled={!enabled}
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Paper>

      {/* Save Button */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button
          variant="outlined"
          onClick={() => navigate('/projects')}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
          onClick={handleSave}
          disabled={saving || !enabled || !organizationUrl || !projectName || !patToken}
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </Button>
      </Box>
    </Box>
  );
}
