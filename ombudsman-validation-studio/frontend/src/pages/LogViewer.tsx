import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Stack,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  TablePagination,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Refresh,
  Download,
  Search,
  FilterList,
  Delete,
  PlayArrow,
  Stop,
} from '@mui/icons-material';
import axios from 'axios';

// Type Definitions
interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  module?: string;
  function?: string;
  line?: number;
  exception?: string;
  user_id?: string;
  project_id?: string;
  action?: string;
}

interface LogResponse {
  logs: LogEntry[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

interface LevelCounts {
  levels: Record<string, number>;
}

const API_BASE_URL = __API_URL__ + '';

const getLevelColor = (level: string): 'error' | 'warning' | 'info' | 'success' | 'default' => {
  switch (level.toUpperCase()) {
    case 'ERROR':
    case 'CRITICAL':
      return 'error';
    case 'WARNING':
      return 'warning';
    case 'INFO':
      return 'info';
    case 'DEBUG':
      return 'default';
    default:
      return 'default';
  }
};

const LogViewer: React.FC = () => {
  // State
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [levelCounts, setLevelCounts] = useState<Record<string, number>>({});
  const [loggers, setLoggers] = useState<string[]>([]);

  // Pagination
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);

  // Filters
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [loggerFilter, setLoggerFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<ReturnType<typeof setInterval> | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      params.append('page', String(page + 1));
      params.append('page_size', String(pageSize));
      if (levelFilter) params.append('level', levelFilter);
      if (loggerFilter) params.append('logger', loggerFilter);
      if (searchQuery) params.append('search', searchQuery);

      const response = await axios.get<LogResponse>(
        `${API_BASE_URL}/logs/?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setLogs(response.data.logs);
      setTotal(response.data.total);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, levelFilter, loggerFilter, searchQuery]);

  const fetchLevelCounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get<LevelCounts>(
        `${API_BASE_URL}/logs/levels`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setLevelCounts(response.data.levels);
    } catch (err) {
      console.error('Failed to fetch level counts:', err);
    }
  };

  const fetchLoggers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get<{ loggers: string[] }>(
        `${API_BASE_URL}/logs/loggers`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setLoggers(response.data.loggers);
    } catch (err) {
      console.error('Failed to fetch loggers:', err);
    }
  };

  const handleClearLogs = async () => {
    if (!window.confirm('Are you sure you want to clear all logs?')) return;

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/logs/clear`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchLogs();
      fetchLevelCounts();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to clear logs');
    }
  };

  const handleExportLogs = () => {
    const csvContent = [
      ['Timestamp', 'Level', 'Logger', 'Message', 'Module', 'Function', 'Line'].join(','),
      ...logs.map(log => [
        log.timestamp,
        log.level,
        log.logger,
        `"${log.message.replace(/"/g, '""')}"`,
        log.module || '',
        log.function || '',
        log.line || ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  useEffect(() => {
    fetchLogs();
    fetchLevelCounts();
    fetchLoggers();
  }, [fetchLogs]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 5000);
      setRefreshInterval(interval);
      return () => clearInterval(interval);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  }, [autoRefresh, fetchLogs]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Application Logs
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(levelCounts).map(([level, count]) => (
          <Grid item xs={6} sm={3} md={2} key={level}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 1 }}>
                <Chip
                  label={level}
                  color={getLevelColor(level)}
                  size="small"
                  sx={{ mb: 1 }}
                />
                <Typography variant="h5">{count}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Level</InputLabel>
            <Select
              value={levelFilter}
              label="Level"
              onChange={(e) => setLevelFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="DEBUG">DEBUG</MenuItem>
              <MenuItem value="INFO">INFO</MenuItem>
              <MenuItem value="WARNING">WARNING</MenuItem>
              <MenuItem value="ERROR">ERROR</MenuItem>
              <MenuItem value="CRITICAL">CRITICAL</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Logger</InputLabel>
            <Select
              value={loggerFilter}
              label="Logger"
              onChange={(e) => setLoggerFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              {loggers.map(logger => (
                <MenuItem key={logger} value={logger}>{logger}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
            }}
            sx={{ minWidth: 250 }}
          />

          <Box sx={{ flexGrow: 1 }} />

          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto-refresh"
          />

          <Tooltip title="Refresh">
            <IconButton onClick={fetchLogs} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>

          <Tooltip title="Export CSV">
            <IconButton onClick={handleExportLogs}>
              <Download />
            </IconButton>
          </Tooltip>

          <Tooltip title="Clear Logs">
            <IconButton onClick={handleClearLogs} color="error">
              <Delete />
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Logs Table */}
      <Paper>
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell width={180}>Timestamp</TableCell>
                <TableCell width={100}>Level</TableCell>
                <TableCell width={200}>Logger</TableCell>
                <TableCell>Message</TableCell>
                <TableCell width={100}>Location</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No logs found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log, index) => (
                  <TableRow key={index} hover>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.level}
                        color={getLevelColor(log.level)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {log.logger}
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '0.75rem',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word'
                        }}
                      >
                        {log.message}
                        {log.exception && (
                          <Box sx={{ mt: 1, color: 'error.main' }}>
                            {log.exception}
                          </Box>
                        )}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                      {log.module && `${log.module}:${log.line}`}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => {
            setPageSize(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100, 200]}
        />
      </Paper>
    </Box>
  );
};

export default LogViewer;
