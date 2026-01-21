import React, { useState, useEffect } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Collapse,
  TablePagination,
  Snackbar,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Refresh,
  Download,
  Search,
  ExpandMore,
  ExpandLess,
  FilterList,
  Close,
  ContentCopy,
} from '@mui/icons-material';
import axios from 'axios';

// Type Definitions
interface AuditLog {
  id: string;
  timestamp: string;
  level: string;
  category: string;
  action: string;
  user_id?: string;
  username?: string;
  ip_address?: string;
  user_agent?: string;
  resource_type?: string;
  resource_id?: string;
  details?: any;
  request_id?: string;
  duration_ms?: number;
  status_code?: number;
  error_message?: string;
}

interface AuditLogFilter {
  start_date?: string;
  end_date?: string;
  level?: string;
  category?: string;
  user_id?: string;
  username?: string;
  action?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

interface SummaryStats {
  total_count: number;
  by_level: Record<string, number>;
  by_category: Record<string, number>;
  recent_errors_count: number;
}

const API_BASE_URL = 'http://localhost:8000';

const AuditLogs: React.FC = () => {
  // State Management
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info'>('info');

  // Filter State
  const [showFilters, setShowFilters] = useState(true);
  const [filters, setFilters] = useState<AuditLogFilter>({
    limit: 100,
    offset: 0,
  });
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchText, setSearchText] = useState('');
  const [userFilter, setUserFilter] = useState('');

  // Pagination State
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [totalLogs, setTotalLogs] = useState(0);

  // Summary State
  const [summary, setSummary] = useState<SummaryStats | null>(null);

  // Detail Dialog State
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // Available Options
  const [levels, setLevels] = useState<string[]>(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']);
  const [categories, setCategories] = useState<string[]>([]);

  // Initial Load
  useEffect(() => {
    fetchLogs();
    fetchSummary();
    fetchCategories();
    fetchLevels();
  }, []);

  // Fetch logs when pagination changes
  useEffect(() => {
    const newFilters = {
      ...filters,
      limit: rowsPerPage,
      offset: page * rowsPerPage,
    };
    setFilters(newFilters);
    fetchLogsWithFilters(newFilters);
  }, [page, rowsPerPage]);

  // API Functions
  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/audit/logs/recent`, {
        params: { limit: 100 }
      });
      setLogs(response.data.logs || []);
      setTotalLogs(response.data.total || response.data.logs?.length || 0);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch logs:', err);
      setError(err.response?.data?.detail || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogsWithFilters = async (filterParams: AuditLogFilter) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/audit/logs/query`, filterParams);
      setLogs(response.data.logs || []);
      setTotalLogs(response.data.total || response.data.logs?.length || 0);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch logs with filters:', err);
      setError(err.response?.data?.detail || 'Failed to load filtered logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/audit/logs/summary`);
      setSummary(response.data);
    } catch (err: any) {
      console.error('Failed to fetch summary:', err);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/audit/categories`);
      setCategories(response.data.categories || []);
    } catch (err: any) {
      console.error('Failed to fetch categories:', err);
    }
  };

  const fetchLevels = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/audit/levels`);
      setLevels(response.data.levels || ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']);
    } catch (err: any) {
      console.error('Failed to fetch levels:', err);
    }
  };

  // Handler Functions
  const handleApplyFilters = () => {
    const newFilters: AuditLogFilter = {
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      level: selectedLevel || undefined,
      category: selectedCategory || undefined,
      username: userFilter || undefined,
      search: searchText || undefined,
      limit: rowsPerPage,
      offset: 0,
    };
    setFilters(newFilters);
    setPage(0);
    fetchLogsWithFilters(newFilters);
  };

  const handleResetFilters = () => {
    setStartDate('');
    setEndDate('');
    setSelectedLevel('');
    setSelectedCategory('');
    setSearchText('');
    setUserFilter('');
    setPage(0);
    const newFilters = { limit: rowsPerPage, offset: 0 };
    setFilters(newFilters);
    fetchLogsWithFilters(newFilters);
  };

  const handleRefresh = () => {
    fetchLogsWithFilters(filters);
    fetchSummary();
    showSnackbar('Logs refreshed', 'success');
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/audit/logs/export`,
        { ...filters, format },
        { responseType: 'blob' }
      );

      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/json'
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString()}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);

      showSnackbar(`Logs exported as ${format.toUpperCase()}`, 'success');
    } catch (err: any) {
      console.error('Export failed:', err);
      showSnackbar('Failed to export logs', 'error');
    }
  };

  const handleRowClick = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailDialogOpen(true);
  };

  const handleCopyRequestId = () => {
    if (selectedLog?.request_id) {
      navigator.clipboard.writeText(selectedLog.request_id);
      showSnackbar('Request ID copied to clipboard', 'success');
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const getLevelColor = (level: string): 'default' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success' => {
    switch (level.toUpperCase()) {
      case 'DEBUG': return 'default';
      case 'INFO': return 'info';
      case 'WARNING': return 'warning';
      case 'ERROR': return 'error';
      case 'CRITICAL': return 'error';
      default: return 'default';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Render Functions
  if (loading && logs.length === 0) {
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
        <Typography variant="h4">Audit Logs</Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={() => handleExport('csv')}
          >
            Export CSV
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={() => handleExport('json')}
          >
            Export JSON
          </Button>
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Summary Statistics */}
      {summary && (
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  {summary.total_count.toLocaleString()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Logs
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="error">
                  {summary.recent_errors_count}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Recent Errors
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  By Level
                </Typography>
                <Stack spacing={0.5}>
                  {Object.entries(summary.by_level).map(([level, count]) => (
                    <Box key={level} display="flex" justifyContent="space-between">
                      <Chip
                        label={level}
                        size="small"
                        color={getLevelColor(level)}
                        sx={{ minWidth: 80 }}
                      />
                      <Typography variant="body2">{count}</Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  By Category
                </Typography>
                <Stack spacing={0.5}>
                  {Object.entries(summary.by_category).slice(0, 5).map(([category, count]) => (
                    <Box key={category} display="flex" justifyContent="space-between">
                      <Typography variant="body2" noWrap sx={{ maxWidth: 120 }}>
                        {category}
                      </Typography>
                      <Typography variant="body2">{count}</Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filter Panel */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" display="flex" alignItems="center">
              <FilterList sx={{ mr: 1 }} /> Filters
            </Typography>
            <IconButton onClick={() => setShowFilters(!showFilters)}>
              {showFilters ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Stack>

          <Collapse in={showFilters}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  label="Start Date"
                  type="datetime-local"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  label="End Date"
                  type="datetime-local"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Level</InputLabel>
                  <Select
                    value={selectedLevel}
                    onChange={(e) => setSelectedLevel(e.target.value)}
                    label="Level"
                  >
                    <MenuItem value="">All</MenuItem>
                    {levels.map((level) => (
                      <MenuItem key={level} value={level}>
                        {level}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    label="Category"
                  >
                    <MenuItem value="">All</MenuItem>
                    {categories.map((category) => (
                      <MenuItem key={category} value={category}>
                        {category}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                <TextField
                  label="Search"
                  placeholder="Search in logs..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  fullWidth
                  size="small"
                  InputProps={{
                    startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />,
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={4}>
                <TextField
                  label="User"
                  placeholder="Filter by username"
                  value={userFilter}
                  onChange={(e) => setUserFilter(e.target.value)}
                  fullWidth
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={12} md={4}>
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    onClick={handleApplyFilters}
                    fullWidth
                  >
                    Apply Filters
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleResetFilters}
                    fullWidth
                  >
                    Reset
                  </Button>
                </Stack>
              </Grid>
            </Grid>
          </Collapse>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Paper>
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Timestamp
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Level
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Category
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Action
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  User
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  IP Address
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Status
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold', backgroundColor: 'primary.light', color: 'white' }}>
                  Duration
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography variant="body2" color="text.secondary" py={4}>
                      No audit logs found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow
                    key={log.id}
                    hover
                    onClick={() => handleRowClick(log)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Typography variant="caption">
                        {formatTimestamp(log.timestamp)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.level}
                        size="small"
                        color={getLevelColor(log.level)}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.category}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.action}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{log.username || '-'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{log.ip_address || '-'}</Typography>
                    </TableCell>
                    <TableCell>
                      {log.status_code && (
                        <Chip
                          label={log.status_code}
                          size="small"
                          color={log.status_code < 300 ? 'success' : log.status_code < 500 ? 'warning' : 'error'}
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {formatDuration(log.duration_ms)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        <TablePagination
          component="div"
          count={totalLogs}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>

      {/* Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Audit Log Details</Typography>
            <IconButton onClick={() => setDetailDialogOpen(false)}>
              <Close />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          {selectedLog && (
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  ID
                </Typography>
                <Typography variant="body2">{selectedLog.id}</Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Timestamp
                </Typography>
                <Typography variant="body2">
                  {formatTimestamp(selectedLog.timestamp)}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Level
                </Typography>
                <Chip
                  label={selectedLog.level}
                  size="small"
                  color={getLevelColor(selectedLog.level)}
                />
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Category
                </Typography>
                <Typography variant="body2">{selectedLog.category}</Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Action
                </Typography>
                <Typography variant="body2">{selectedLog.action}</Typography>
              </Box>

              {selectedLog.username && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    User
                  </Typography>
                  <Typography variant="body2">
                    {selectedLog.username} {selectedLog.user_id && `(${selectedLog.user_id})`}
                  </Typography>
                </Box>
              )}

              {selectedLog.ip_address && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    IP Address
                  </Typography>
                  <Typography variant="body2">{selectedLog.ip_address}</Typography>
                </Box>
              )}

              {selectedLog.user_agent && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    User Agent
                  </Typography>
                  <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                    {selectedLog.user_agent}
                  </Typography>
                </Box>
              )}

              {selectedLog.resource_type && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Resource
                  </Typography>
                  <Typography variant="body2">
                    {selectedLog.resource_type}
                    {selectedLog.resource_id && ` / ${selectedLog.resource_id}`}
                  </Typography>
                </Box>
              )}

              {selectedLog.status_code && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Status Code
                  </Typography>
                  <Chip
                    label={selectedLog.status_code}
                    size="small"
                    color={
                      selectedLog.status_code < 300
                        ? 'success'
                        : selectedLog.status_code < 500
                        ? 'warning'
                        : 'error'
                    }
                  />
                </Box>
              )}

              {selectedLog.duration_ms !== undefined && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Duration
                  </Typography>
                  <Typography variant="body2">
                    {formatDuration(selectedLog.duration_ms)}
                  </Typography>
                </Box>
              )}

              {selectedLog.request_id && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Request ID
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}
                    >
                      {selectedLog.request_id}
                    </Typography>
                    <Tooltip title="Copy Request ID">
                      <IconButton size="small" onClick={handleCopyRequestId}>
                        <ContentCopy fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              )}

              {selectedLog.error_message && (
                <Box>
                  <Typography variant="subtitle2" color="error">
                    Error Message
                  </Typography>
                  <Alert severity="error" sx={{ mt: 1 }}>
                    {selectedLog.error_message}
                  </Alert>
                </Box>
              )}

              {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Additional Details
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 2,
                      backgroundColor: 'grey.50',
                      maxHeight: 300,
                      overflow: 'auto',
                    }}
                  >
                    <pre style={{ margin: 0, fontSize: '0.85rem' }}>
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
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

export default AuditLogs;
