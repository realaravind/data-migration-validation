import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  TextField,
  Switch,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Chip,
  Alert,
  Snackbar,
  Stack,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Send,
  Refresh,
  Settings,
  CheckCircle,
  Error as ErrorIcon,
  History,
  Assessment,
  Close,
} from '@mui/icons-material';
import axios from 'axios';

// Type Definitions
interface NotificationConfig {
  enabled: boolean;
  smtp_host?: string;
  smtp_port: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_use_tls: boolean;
  smtp_from_email?: string;
  smtp_from_name: string;
  default_slack_webhook?: string;
  slack_channel?: string;
  default_webhook_url?: string;
  webhook_timeout: number;
  max_notifications_per_hour: number;
  max_retries: number;
  retry_delay_seconds: number;
}

interface NotificationRule {
  id?: string;
  name: string;
  description?: string;
  enabled: boolean;
  event: string;
  channels: string[];
  priority: string;
  conditions?: any;
  throttle_minutes?: number;
  email_recipients?: string[];
  slack_webhook_url?: string;
  webhook_url?: string;
  message_template?: string;
  created_at?: string;
  updated_at?: string;
}

interface NotificationHistory {
  id: string;
  rule_id?: string;
  channel: string;
  event: string;
  priority: string;
  title: string;
  message: string;
  recipients: string[];
  sent_at: string;
  success: boolean;
  error_message?: string;
  retry_count: number;
  metadata?: any;
}

interface NotificationStats {
  total_sent: number;
  successful: number;
  failed: number;
  by_channel: Record<string, number>;
  by_event: Record<string, number>;
  by_priority: Record<string, number>;
  recent_failures: NotificationHistory[];
}

const API_BASE_URL = __API_URL__ + '';

const NotificationSettings: React.FC = () => {
  // State Management
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<NotificationConfig | null>(null);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [history, setHistory] = useState<NotificationHistory[]>([]);
  const [stats, setStats] = useState<NotificationStats | null>(null);

  // Available options
  const [channels, setChannels] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [priorities, setPriorities] = useState<any[]>([]);

  // Dialog States
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<NotificationRule | null>(null);

  // Form States
  const [editedConfig, setEditedConfig] = useState<NotificationConfig | null>(null);
  const [editedRule, setEditedRule] = useState<NotificationRule | null>(null);
  const [testChannel, setTestChannel] = useState('email');
  const [testRecipient, setTestRecipient] = useState('');

  // Snackbar
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info'>('info');

  // Initial Load
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadConfig(),
        loadRules(),
        loadHistory(),
        loadStats(),
        loadOptions(),
      ]);
    } catch (error) {
      console.error('Failed to load data:', error);
      showSnackbar('Failed to load notification data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/notifications/config`);
      setConfig(response.data.config);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const loadRules = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/notifications/rules`);
      setRules(response.data);
    } catch (error) {
      console.error('Failed to load rules:', error);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/notifications/history`, {
        params: { limit: 50 }
      });
      setHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/notifications/stats`);
      setStats(response.data.stats);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadOptions = async () => {
    try {
      const [channelsRes, eventsRes, prioritiesRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/notifications/channels`),
        axios.get(`${API_BASE_URL}/notifications/events`),
        axios.get(`${API_BASE_URL}/notifications/priorities`),
      ]);
      setChannels(channelsRes.data.channels || []);
      setEvents(eventsRes.data.events || []);
      setPriorities(prioritiesRes.data.priorities || []);
    } catch (error) {
      console.error('Failed to load options:', error);
    }
  };

  // Configuration Handlers
  const handleSaveConfig = async () => {
    if (!editedConfig) return;

    try {
      await axios.put(`${API_BASE_URL}/notifications/config`, editedConfig);
      setConfig(editedConfig);
      setConfigDialogOpen(false);
      showSnackbar('Configuration saved successfully', 'success');
    } catch (error: any) {
      console.error('Failed to save config:', error);
      showSnackbar(error.response?.data?.detail || 'Failed to save configuration', 'error');
    }
  };

  // Rule Handlers
  const handleCreateRule = () => {
    setSelectedRule(null);
    setEditedRule({
      name: '',
      description: '',
      enabled: true,
      event: 'validation_completed',
      channels: ['email'],
      priority: 'medium',
      email_recipients: [],
    });
    setRuleDialogOpen(true);
  };

  const handleEditRule = (rule: NotificationRule) => {
    setSelectedRule(rule);
    setEditedRule({ ...rule });
    setRuleDialogOpen(true);
  };

  const handleSaveRule = async () => {
    if (!editedRule) return;

    try {
      if (selectedRule?.id) {
        // Update existing rule
        await axios.put(`${API_BASE_URL}/notifications/rules/${selectedRule.id}`, editedRule);
        showSnackbar('Rule updated successfully', 'success');
      } else {
        // Create new rule
        await axios.post(`${API_BASE_URL}/notifications/rules`, editedRule);
        showSnackbar('Rule created successfully', 'success');
      }
      setRuleDialogOpen(false);
      loadRules();
    } catch (error: any) {
      console.error('Failed to save rule:', error);
      showSnackbar(error.response?.data?.detail || 'Failed to save rule', 'error');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!window.confirm('Are you sure you want to delete this rule?')) return;

    try {
      await axios.delete(`${API_BASE_URL}/notifications/rules/${ruleId}`);
      showSnackbar('Rule deleted successfully', 'success');
      loadRules();
    } catch (error: any) {
      console.error('Failed to delete rule:', error);
      showSnackbar(error.response?.data?.detail || 'Failed to delete rule', 'error');
    }
  };

  const handleToggleRule = async (ruleId: string) => {
    try {
      await axios.post(`${API_BASE_URL}/notifications/rules/${ruleId}/toggle`);
      showSnackbar('Rule toggled successfully', 'success');
      loadRules();
    } catch (error: any) {
      console.error('Failed to toggle rule:', error);
      showSnackbar(error.response?.data?.detail || 'Failed to toggle rule', 'error');
    }
  };

  // Test Notification Handler
  const handleTestNotification = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/notifications/test`, {
        channel: testChannel,
        recipient: testRecipient,
        title: 'Test Notification',
        message: 'This is a test notification from Ombudsman Validation Studio',
      });

      if (response.data.status === 'success') {
        showSnackbar('Test notification sent successfully', 'success');
        setTestDialogOpen(false);
        setTestRecipient('');
      } else {
        showSnackbar('Test notification failed', 'error');
      }
    } catch (error: any) {
      console.error('Failed to send test:', error);
      showSnackbar(error.response?.data?.detail || 'Failed to send test notification', 'error');
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const getPriorityColor = (priority: string): 'default' | 'success' | 'warning' | 'error' => {
    switch (priority.toLowerCase()) {
      case 'low': return 'success';
      case 'medium': return 'default';
      case 'high': return 'warning';
      case 'critical': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Notification Settings</Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={loadData}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<Send />}
            onClick={() => setTestDialogOpen(true)}
          >
            Test Notification
          </Button>
        </Stack>
      </Stack>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab icon={<Settings />} label="Configuration" />
          <Tab icon={<Assessment />} label="Rules" />
          <Tab icon={<History />} label="History" />
          <Tab icon={<Assessment />} label="Statistics" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {tabValue === 0 && (
        <Box>
          {/* Configuration Tab */}
          <Grid container spacing={3}>
            {/* Global Settings */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">Global Settings</Typography>
                    <Button
                      variant="contained"
                      startIcon={<Edit />}
                      onClick={() => {
                        setEditedConfig(config ? { ...config } : null);
                        setConfigDialogOpen(true);
                      }}
                    >
                      Edit Configuration
                    </Button>
                  </Stack>
                  <Divider sx={{ mb: 2 }} />
                  {config && (
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={<Switch checked={config.enabled} disabled />}
                          label="Notifications Enabled"
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          Max Notifications/Hour: {config.max_notifications_per_hour}
                        </Typography>
                      </Grid>
                    </Grid>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Email Settings */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Email (SMTP) Settings
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {config ? (
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        <strong>Host:</strong> {config.smtp_host || 'Not configured'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Port:</strong> {config.smtp_port}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Username:</strong> {config.smtp_username || 'Not configured'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>From Email:</strong> {config.smtp_from_email || 'Not configured'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>TLS:</strong> {config.smtp_use_tls ? 'Enabled' : 'Disabled'}
                      </Typography>
                    </Stack>
                  ) : (
                    <Alert severity="warning">Configuration not loaded</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Slack Settings */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Slack Settings
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {config ? (
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        <strong>Webhook URL:</strong> {config.default_slack_webhook ? 'Configured' : 'Not configured'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Channel:</strong> {config.slack_channel || 'Default'}
                      </Typography>
                    </Stack>
                  ) : (
                    <Alert severity="warning">Configuration not loaded</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Webhook Settings */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Webhook Settings
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  {config ? (
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        <strong>Default URL:</strong> {config.default_webhook_url || 'Not configured'}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Timeout:</strong> {config.webhook_timeout}s
                      </Typography>
                    </Stack>
                  ) : (
                    <Alert severity="warning">Configuration not loaded</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {tabValue === 1 && (
        <Box>
          {/* Rules Tab */}
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Notification Rules</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={handleCreateRule}
            >
              Create Rule
            </Button>
          </Stack>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Name
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Event
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Channels
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Priority
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Enabled
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rules.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={4}>
                        No notification rules configured. Create one to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  rules.map((rule) => (
                    <TableRow key={rule.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {rule.name}
                        </Typography>
                        {rule.description && (
                          <Typography variant="caption" color="text.secondary">
                            {rule.description}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip label={rule.event} size="small" />
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5}>
                          {rule.channels.map((channel) => (
                            <Chip key={channel} label={channel} size="small" variant="outlined" />
                          ))}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={rule.priority}
                          size="small"
                          color={getPriorityColor(rule.priority)}
                        />
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={rule.enabled}
                          onChange={() => rule.id && handleToggleRule(rule.id)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <Tooltip title="Edit">
                            <IconButton size="small" onClick={() => handleEditRule(rule)}>
                              <Edit fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => rule.id && handleDeleteRule(rule.id)}
                            >
                              <Delete fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {tabValue === 2 && (
        <Box>
          {/* History Tab */}
          <Typography variant="h6" mb={2}>
            Notification History
          </Typography>

          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Timestamp
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Event
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Title
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Channel
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Priority
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                    Status
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={4}>
                        No notification history available
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  history.map((item) => (
                    <TableRow key={item.id} hover>
                      <TableCell>
                        <Typography variant="caption">
                          {new Date(item.sent_at).toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={item.event} size="small" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{item.title}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={item.channel} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={item.priority}
                          size="small"
                          color={getPriorityColor(item.priority)}
                        />
                      </TableCell>
                      <TableCell>
                        {item.success ? (
                          <Chip
                            icon={<CheckCircle />}
                            label="Success"
                            size="small"
                            color="success"
                          />
                        ) : (
                          <Chip
                            icon={<ErrorIcon />}
                            label="Failed"
                            size="small"
                            color="error"
                          />
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {tabValue === 3 && stats && (
        <Box>
          {/* Statistics Tab */}
          <Grid container spacing={3}>
            {/* Summary Cards */}
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="primary">
                    {stats.total_sent}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Sent
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="success.main">
                    {stats.successful}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Successful
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="error">
                    {stats.failed}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Failed
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="text.primary">
                    {stats.total_sent > 0
                      ? ((stats.successful / stats.total_sent) * 100).toFixed(1)
                      : 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Success Rate
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* By Channel */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    By Channel
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack spacing={1}>
                    {Object.entries(stats.by_channel).map(([channel, count]) => (
                      <Box key={channel} display="flex" justifyContent="space-between">
                        <Typography variant="body2">{channel}</Typography>
                        <Chip label={count} size="small" />
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* By Event */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    By Event
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack spacing={1}>
                    {Object.entries(stats.by_event).map(([event, count]) => (
                      <Box key={event} display="flex" justifyContent="space-between">
                        <Typography variant="body2">{event}</Typography>
                        <Chip label={count} size="small" />
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* By Priority */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    By Priority
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack spacing={1}>
                    {Object.entries(stats.by_priority).map(([priority, count]) => (
                      <Box key={priority} display="flex" justifyContent="space-between">
                        <Chip
                          label={priority}
                          size="small"
                          color={getPriorityColor(priority)}
                        />
                        <Chip label={count} size="small" />
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Configuration Dialog */}
      <Dialog open={configDialogOpen} onClose={() => setConfigDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Edit Configuration</Typography>
            <IconButton onClick={() => setConfigDialogOpen(false)}>
              <Close />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          {editedConfig && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={editedConfig.enabled}
                      onChange={(e) =>
                        setEditedConfig({ ...editedConfig, enabled: e.target.checked })
                      }
                    />
                  }
                  label="Enable Notifications"
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle1" gutterBottom>
                  Email (SMTP) Settings
                </Typography>
              </Grid>
              <Grid item xs={12} sm={8}>
                <TextField
                  label="SMTP Host"
                  fullWidth
                  value={editedConfig.smtp_host || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, smtp_host: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="SMTP Port"
                  type="number"
                  fullWidth
                  value={editedConfig.smtp_port}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, smtp_port: parseInt(e.target.value) })
                  }
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="SMTP Username"
                  fullWidth
                  value={editedConfig.smtp_username || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, smtp_username: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="SMTP Password"
                  type="password"
                  fullWidth
                  value={editedConfig.smtp_password || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, smtp_password: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="From Email"
                  fullWidth
                  value={editedConfig.smtp_from_email || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, smtp_from_email: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={editedConfig.smtp_use_tls}
                      onChange={(e) =>
                        setEditedConfig({ ...editedConfig, smtp_use_tls: e.target.checked })
                      }
                    />
                  }
                  label="Use TLS"
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle1" gutterBottom>
                  Slack Settings
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Default Slack Webhook URL"
                  fullWidth
                  value={editedConfig.default_slack_webhook || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, default_slack_webhook: e.target.value })
                  }
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle1" gutterBottom>
                  Webhook Settings
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Default Webhook URL"
                  fullWidth
                  value={editedConfig.default_webhook_url || ''}
                  onChange={(e) =>
                    setEditedConfig({ ...editedConfig, default_webhook_url: e.target.value })
                  }
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveConfig}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rule Dialog */}
      <Dialog open={ruleDialogOpen} onClose={() => setRuleDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {selectedRule ? 'Edit Rule' : 'Create Rule'}
            </Typography>
            <IconButton onClick={() => setRuleDialogOpen(false)}>
              <Close />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          {editedRule && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Rule Name"
                  fullWidth
                  required
                  value={editedRule.name}
                  onChange={(e) =>
                    setEditedRule({ ...editedRule, name: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Description"
                  fullWidth
                  multiline
                  rows={2}
                  value={editedRule.description || ''}
                  onChange={(e) =>
                    setEditedRule({ ...editedRule, description: e.target.value })
                  }
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth required>
                  <InputLabel>Event</InputLabel>
                  <Select
                    value={editedRule.event}
                    onChange={(e) =>
                      setEditedRule({ ...editedRule, event: e.target.value })
                    }
                    label="Event"
                  >
                    {events.map((event) => (
                      <MenuItem key={event.value} value={event.value}>
                        {event.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth required>
                  <InputLabel>Priority</InputLabel>
                  <Select
                    value={editedRule.priority}
                    onChange={(e) =>
                      setEditedRule({ ...editedRule, priority: e.target.value })
                    }
                    label="Priority"
                  >
                    {priorities.map((priority) => (
                      <MenuItem key={priority.value} value={priority.value}>
                        {priority.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth required>
                  <InputLabel>Channels</InputLabel>
                  <Select
                    multiple
                    value={editedRule.channels}
                    onChange={(e) =>
                      setEditedRule({
                        ...editedRule,
                        channels: typeof e.target.value === 'string'
                          ? e.target.value.split(',')
                          : e.target.value,
                      })
                    }
                    label="Channels"
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {channels.map((channel) => (
                      <MenuItem key={channel.value} value={channel.value}>
                        {channel.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Email Recipients (comma-separated)"
                  fullWidth
                  value={editedRule.email_recipients?.join(', ') || ''}
                  onChange={(e) =>
                    setEditedRule({
                      ...editedRule,
                      email_recipients: e.target.value.split(',').map((s) => s.trim()),
                    })
                  }
                  helperText="Required for email notifications"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={editedRule.enabled}
                      onChange={(e) =>
                        setEditedRule({ ...editedRule, enabled: e.target.checked })
                      }
                    />
                  }
                  label="Enabled"
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRuleDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveRule}>
            {selectedRule ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Notification Dialog */}
      <Dialog open={testDialogOpen} onClose={() => setTestDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Test Notification</Typography>
            <IconButton onClick={() => setTestDialogOpen(false)}>
              <Close />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Channel</InputLabel>
                <Select
                  value={testChannel}
                  onChange={(e) => setTestChannel(e.target.value)}
                  label="Channel"
                >
                  {channels.map((channel) => (
                    <MenuItem key={channel.value} value={channel.value}>
                      {channel.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label={
                  testChannel === 'email'
                    ? 'Recipient Email'
                    : testChannel === 'slack'
                    ? 'Slack Webhook URL (optional)'
                    : 'Webhook URL'
                }
                fullWidth
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.target.value)}
                helperText={
                  testChannel === 'slack'
                    ? 'Leave empty to use default webhook'
                    : 'Enter the recipient or URL'
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            startIcon={<Send />}
            onClick={handleTestNotification}
            disabled={testChannel === 'email' && !testRecipient}
          >
            Send Test
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbarOpen(false)}
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default NotificationSettings;
