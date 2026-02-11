import React, { useState, useEffect, useCallback } from 'react';
import {
  Badge,
  IconButton,
  Drawer,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Button,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  AlertTitle,
  Tooltip,
  Stack,
  Paper,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  CheckCircle as SuccessIcon,
  ExpandMore as ExpandMoreIcon,
  Delete as DeleteIcon,
  DoneAll as DoneAllIcon,
  ContentCopy as CopyIcon,
  OpenInNew as OpenInNewIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import axios from 'axios';

interface FixSuggestion {
  title: string;
  description: string;
  steps: string[];
  code_snippet?: string;
  doc_link?: string;
}

interface AlertItem {
  id: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  category: string;
  title: string;
  message: string;
  source: string;
  details?: Record<string, any>;
  suggestions: FixSuggestion[];
  read: boolean;
}

const API_BASE_URL = __API_URL__ + '';

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'critical':
    case 'error':
      return <ErrorIcon color="error" />;
    case 'warning':
      return <WarningIcon color="warning" />;
    case 'info':
      return <InfoIcon color="info" />;
    default:
      return <InfoIcon />;
  }
};

const getSeverityColor = (severity: string): 'error' | 'warning' | 'info' | 'success' => {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'error';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'info';
  }
};

const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    connection: 'Connection',
    authentication: 'Authentication',
    permission: 'Permission',
    configuration: 'Configuration',
    validation: 'Validation',
    system: 'System',
  };
  return labels[category] || category;
};

export default function AlertsDrawer() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/alerts/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAlerts(response.data.alerts);
      setUnreadCount(response.data.unread_count);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/alerts/count`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUnreadCount(response.data.unread_count);
    } catch (err) {
      // Silently fail for count check
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchUnreadCount();

    // Poll for new alerts every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  useEffect(() => {
    if (open) {
      fetchAlerts();
    }
  }, [open, fetchAlerts]);

  const handleMarkRead = async (alertId: string) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_BASE_URL}/alerts/${alertId}/read`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAlerts();
    } catch (err) {
      console.error('Failed to mark alert as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_BASE_URL}/alerts/read-all`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAlerts();
    } catch (err) {
      console.error('Failed to mark all alerts as read:', err);
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/alerts/${alertId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAlerts();
    } catch (err) {
      console.error('Failed to delete alert:', err);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Clear all alerts?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/alerts/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAlerts();
    } catch (err) {
      console.error('Failed to clear alerts:', err);
    }
  };

  const handleCopyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      <Tooltip title={unreadCount > 0 ? `${unreadCount} unread alerts` : 'No new alerts'}>
        <IconButton
          onClick={() => setOpen(true)}
          sx={{
            ml: 1,
            color: unreadCount > 0 ? 'error.main' : 'inherit',
          }}
        >
          <Badge badgeContent={unreadCount} color="error" max={99}>
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Drawer
        anchor="right"
        open={open}
        onClose={() => setOpen(false)}
        PaperProps={{
          sx: { width: { xs: '100%', sm: 450, md: 500 } },
        }}
      >
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box
            sx={{
              p: 2,
              borderBottom: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              bgcolor: 'background.paper',
            }}
          >
            <Typography variant="h6">
              System Alerts
              {unreadCount > 0 && (
                <Chip
                  label={unreadCount}
                  color="error"
                  size="small"
                  sx={{ ml: 1 }}
                />
              )}
            </Typography>
            <Box>
              {alerts.length > 0 && (
                <>
                  <Tooltip title="Mark all as read">
                    <IconButton size="small" onClick={handleMarkAllRead}>
                      <DoneAllIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Clear all">
                    <IconButton size="small" onClick={handleClearAll} color="error">
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                </>
              )}
              <IconButton size="small" onClick={() => setOpen(false)}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>

          {/* Alerts List */}
          <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
            {alerts.length === 0 ? (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'text.secondary',
                }}
              >
                <SuccessIcon sx={{ fontSize: 64, mb: 2, color: 'success.main' }} />
                <Typography variant="h6">All Clear!</Typography>
                <Typography variant="body2">No system alerts at this time.</Typography>
              </Box>
            ) : (
              <List disablePadding>
                {alerts.map((alert) => (
                  <Paper
                    key={alert.id}
                    elevation={alert.read ? 0 : 2}
                    sx={{
                      mb: 1,
                      bgcolor: alert.read ? 'grey.50' : 'background.paper',
                      border: '1px solid',
                      borderColor: alert.read ? 'grey.200' : `${getSeverityColor(alert.severity)}.main`,
                      borderLeft: '4px solid',
                      borderLeftColor: `${getSeverityColor(alert.severity)}.main`,
                    }}
                  >
                    <Accordion
                      disableGutters
                      elevation={0}
                      sx={{ bgcolor: 'transparent' }}
                      onChange={() => !alert.read && handleMarkRead(alert.id)}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Box sx={{ width: '100%', pr: 2 }}>
                          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                            {getSeverityIcon(alert.severity)}
                            <Typography variant="subtitle2" fontWeight="bold">
                              {alert.title}
                            </Typography>
                            <Chip
                              label={getCategoryLabel(alert.category)}
                              size="small"
                              variant="outlined"
                              sx={{ ml: 'auto', height: 20, fontSize: '0.7rem' }}
                            />
                          </Stack>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {alert.message}
                          </Typography>
                          <Typography variant="caption" color="text.disabled">
                            {formatTimestamp(alert.timestamp)} - {alert.source}
                          </Typography>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Alert severity={getSeverityColor(alert.severity)} sx={{ mb: 2 }}>
                          <AlertTitle>Error Details</AlertTitle>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                            {alert.message}
                          </Typography>
                        </Alert>

                        {alert.suggestions.length > 0 && (
                          <Box>
                            <Typography variant="subtitle2" gutterBottom sx={{ color: 'primary.main' }}>
                              How to Fix
                            </Typography>
                            {alert.suggestions.map((suggestion, idx) => (
                              <Box key={idx} sx={{ mb: 2 }}>
                                <Typography variant="body2" fontWeight="bold" gutterBottom>
                                  {suggestion.title}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" paragraph>
                                  {suggestion.description}
                                </Typography>

                                {suggestion.steps.length > 0 && (
                                  <Box component="ol" sx={{ pl: 2, mb: 1 }}>
                                    {suggestion.steps.map((step, stepIdx) => (
                                      <Typography
                                        component="li"
                                        variant="body2"
                                        key={stepIdx}
                                        sx={{ mb: 0.5 }}
                                      >
                                        {step}
                                      </Typography>
                                    ))}
                                  </Box>
                                )}

                                {suggestion.code_snippet && (
                                  <Box
                                    sx={{
                                      position: 'relative',
                                      bgcolor: 'grey.900',
                                      borderRadius: 1,
                                      p: 1.5,
                                      mt: 1,
                                    }}
                                  >
                                    <IconButton
                                      size="small"
                                      onClick={() => handleCopyCode(suggestion.code_snippet!, `${alert.id}-${idx}`)}
                                      sx={{
                                        position: 'absolute',
                                        top: 4,
                                        right: 4,
                                        color: 'grey.400',
                                      }}
                                    >
                                      <CopyIcon fontSize="small" />
                                    </IconButton>
                                    {copiedId === `${alert.id}-${idx}` && (
                                      <Typography
                                        variant="caption"
                                        sx={{
                                          position: 'absolute',
                                          top: 8,
                                          right: 40,
                                          color: 'success.light',
                                        }}
                                      >
                                        Copied!
                                      </Typography>
                                    )}
                                    <Typography
                                      component="pre"
                                      sx={{
                                        fontFamily: 'monospace',
                                        fontSize: '0.75rem',
                                        color: 'grey.100',
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-all',
                                        m: 0,
                                        pr: 4,
                                      }}
                                    >
                                      {suggestion.code_snippet}
                                    </Typography>
                                  </Box>
                                )}

                                {suggestion.doc_link && (
                                  <Button
                                    size="small"
                                    startIcon={<OpenInNewIcon />}
                                    href={suggestion.doc_link}
                                    target="_blank"
                                    sx={{ mt: 1 }}
                                  >
                                    View Documentation
                                  </Button>
                                )}
                              </Box>
                            ))}
                          </Box>
                        )}

                        <Divider sx={{ my: 1 }} />
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <Button
                            size="small"
                            color="error"
                            startIcon={<DeleteIcon />}
                            onClick={() => handleDeleteAlert(alert.id)}
                          >
                            Dismiss
                          </Button>
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  </Paper>
                ))}
              </List>
            )}
          </Box>
        </Box>
      </Drawer>
    </>
  );
}
