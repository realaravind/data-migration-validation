import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  FormControlLabel,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from "@mui/material";
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import BugReportIcon from '@mui/icons-material/BugReport';
import DownloadIcon from '@mui/icons-material/Download';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import FilterListIcon from '@mui/icons-material/FilterList';

// Type definitions
interface Bug {
  bug_id: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  status: string;
  batch_job_id: string;
  run_id?: string;
  step_name: string;
  validation_type: string;
  table_name?: string;
  column_name?: string;
  error_message?: string;
  expected_value?: string;
  actual_value?: string;
  row_count?: number;
  failure_count?: number;
  failure_percentage?: number;
  sample_data?: any[];
  work_item_id?: number;
  work_item_url?: string;
  created_at: string;
  reviewed_at?: string;
  tags: string[];
}

interface BugReportSummary {
  total_bugs: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  schema_failures: number;
  data_quality_failures: number;
  referential_integrity_failures: number;
  dimension_failures: number;
  fact_failures: number;
  metric_failures: number;
  timeseries_failures: number;
  custom_failures: number;
  pending_review: number;
  approved: number;
  rejected: number;
  created_in_azure: number;
  failed_to_create: number;
}

interface BugReport {
  report_id: string;
  batch_job_id: string;
  batch_job_name: string;
  project_id: string;
  project_name: string;
  title: string;
  description?: string;
  generated_at: string;
  generated_by?: string;
  bugs: Bug[];
  summary: BugReportSummary;
  group_by?: string;
  grouped_bugs?: Record<string, Bug[]>;
  include_sample_data: boolean;
  max_samples_per_bug: number;
  approved_count: number;
  submitted_to_azure: boolean;
  azure_submission_timestamp?: string;
  tags: string[];
}

const SEVERITY_COLORS = {
  critical: '#d32f2f',
  high: '#f57c00',
  medium: '#fbc02d',
  low: '#388e3c',
  info: '#1976d2'
};

const CATEGORY_ICONS: Record<string, string> = {
  schema: '📋',
  data_quality: '✓',
  referential_integrity: '🔗',
  dimension: '📊',
  fact: '📈',
  metric: '📉',
  timeseries: '⏱️',
  custom: '⚙️'
};

export default function BugReportPreview() {
  const { reportId } = useParams();
  const navigate = useNavigate();

  const [report, setReport] = useState<BugReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBugs, setSelectedBugs] = useState<Set<string>>(new Set());
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [groupBy, setGroupBy] = useState<string>('none');
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [submittingToAzure, setSubmittingToAzure] = useState(false);

  useEffect(() => {
    if (reportId) {
      fetchReport();
    }
  }, [reportId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${__API_URL__}/bug-reports/${reportId}`);
      if (!response.ok) throw new Error('Failed to fetch bug report');
      const data = await response.json();
      setReport(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBugSelection = (bugId: string) => {
    const newSelection = new Set(selectedBugs);
    if (newSelection.has(bugId)) {
      newSelection.delete(bugId);
    } else {
      newSelection.add(bugId);
    }
    setSelectedBugs(newSelection);
  };

  const handleSelectAll = () => {
    if (!report) return;
    const filteredBugs = getFilteredBugs();
    if (selectedBugs.size === filteredBugs.length) {
      setSelectedBugs(new Set());
    } else {
      setSelectedBugs(new Set(filteredBugs.map(bug => bug.bug_id)));
    }
  };

  const handleReviewBugs = async (approve: boolean) => {
    if (!reportId || selectedBugs.size === 0) return;

    try {
      const payload = approve
        ? { report_id: reportId, approved_bug_ids: Array.from(selectedBugs), rejected_bug_ids: [] }
        : { report_id: reportId, approved_bug_ids: [], rejected_bug_ids: Array.from(selectedBugs) };

      const response = await fetch(`${__API_URL__}/bug-reports/${reportId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to review bugs');

      const updatedReport = await response.json();
      setReport(updatedReport);
      setSelectedBugs(new Set());
      setReviewDialogOpen(false);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDownload = async (format: 'pdf' | 'json' | 'excel' | 'csv') => {
    if (!reportId) return;

    try {
      setDownloadingFormat(format);
      const response = await fetch(`${__API_URL__}/bug-reports/${reportId}/download/${format}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const extensions = { pdf: 'pdf', json: 'json', excel: 'xlsx', csv: 'csv' };
      link.download = `bug_report_${reportId}.${extensions[format]}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleSubmitToAzureDevOps = async () => {
    if (!reportId || selectedBugs.size === 0) return;

    try {
      setSubmittingToAzure(true);

      // Step 1: Approve the selected bugs
      const approvePayload = {
        report_id: reportId,
        approved_bug_ids: Array.from(selectedBugs),
        rejected_bug_ids: []
      };

      const reviewResponse = await fetch(`${__API_URL__}/bug-reports/${reportId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(approvePayload)
      });

      if (!reviewResponse.ok) throw new Error('Failed to approve bugs');

      // Step 2: Submit approved bugs to Azure DevOps
      const submitResponse = await fetch(`${__API_URL__}/bug-reports/${reportId}/submit-to-azure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!submitResponse.ok) throw new Error('Failed to submit to Azure DevOps');

      const result = await submitResponse.json();
      alert(`Successfully submitted ${result.created} bugs to Azure DevOps!`);

      // Clear selection and refresh
      setSelectedBugs(new Set());
      fetchReport();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmittingToAzure(false);
    }
  };

  const getFilteredBugs = (): Bug[] => {
    if (!report) return [];

    return report.bugs.filter(bug => {
      // Severity filter
      if (severityFilter.length > 0 && !severityFilter.includes(bug.severity)) {
        return false;
      }

      // Category filter
      if (categoryFilter.length > 0 && !categoryFilter.includes(bug.category)) {
        return false;
      }

      // Status filter
      if (statusFilter !== 'all' && bug.status !== statusFilter) {
        return false;
      }

      return true;
    });
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon sx={{ color: SEVERITY_COLORS.critical }} />;
      case 'high':
        return <WarningIcon sx={{ color: SEVERITY_COLORS.high }} />;
      case 'medium':
        return <InfoIcon sx={{ color: SEVERITY_COLORS.medium }} />;
      case 'low':
        return <CheckCircleIcon sx={{ color: SEVERITY_COLORS.low }} />;
      default:
        return <InfoIcon sx={{ color: SEVERITY_COLORS.info }} />;
    }
  };

  const getStatusColor = (status: string): "default" | "success" | "error" | "warning" | "info" => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'created_in_azure':
        return 'info';
      case 'failed_to_create':
        return 'error';
      default:
        return 'default';
    }
  };

  const renderBugCard = (bug: Bug) => {
    const isSelected = selectedBugs.has(bug.bug_id);

    return (
      <Accordion key={bug.bug_id}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={2} width="100%">
            <Checkbox
              checked={isSelected}
              onChange={() => handleBugSelection(bug.bug_id)}
              onClick={(e) => e.stopPropagation()}
              disabled={bug.status === 'created_in_azure'}
            />
            {getSeverityIcon(bug.severity)}
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                {bug.title}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
                {bug.step_name} • {bug.table_name || 'N/A'}
              </Typography>
            </Box>
            <Chip
              label={CATEGORY_ICONS[bug.category] + ' ' + bug.category.replace(/_/g, ' ')}
              size="small"
              sx={{ fontSize: '0.7rem' }}
            />
            <Chip
              label={bug.severity.toUpperCase()}
              size="small"
              sx={{
                bgcolor: SEVERITY_COLORS[bug.severity as keyof typeof SEVERITY_COLORS] + '30',
                color: SEVERITY_COLORS[bug.severity as keyof typeof SEVERITY_COLORS],
                fontWeight: 'bold',
                fontSize: '0.7rem'
              }}
            />
            <Chip
              label={bug.status.replace(/_/g, ' ').toUpperCase()}
              color={getStatusColor(bug.status)}
              size="small"
              sx={{ fontSize: '0.7rem' }}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            {/* Description */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Description:</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {bug.description}
              </Typography>
            </Box>

            {/* Bug Details */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              {bug.error_message && (
                <Grid item xs={12}>
                  <Alert severity="error" sx={{ py: 0.5 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block' }}>
                      Error Message:
                    </Typography>
                    <Typography variant="caption">{bug.error_message}</Typography>
                  </Alert>
                </Grid>
              )}
              {bug.expected_value && (
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Expected:</Typography>
                  <Typography variant="body2">{bug.expected_value}</Typography>
                </Grid>
              )}
              {bug.actual_value && (
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Actual:</Typography>
                  <Typography variant="body2">{bug.actual_value}</Typography>
                </Grid>
              )}
              {bug.failure_count !== undefined && bug.failure_count !== null && (
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Failures:</Typography>
                  <Typography variant="body2">
                    {bug.failure_count.toLocaleString()}
                    {bug.failure_percentage !== undefined && ` (${bug.failure_percentage.toFixed(2)}%)`}
                  </Typography>
                </Grid>
              )}
              {bug.row_count !== undefined && bug.row_count !== null && (
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">Total Rows:</Typography>
                  <Typography variant="body2">{bug.row_count.toLocaleString()}</Typography>
                </Grid>
              )}
            </Grid>

            {/* Sample Data */}
            {bug.sample_data && bug.sample_data.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Sample Data ({bug.sample_data.length}):</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                        {Object.keys(bug.sample_data[0]).map(key => (
                          <TableCell key={key} sx={{ fontWeight: 'bold', fontSize: '0.7rem' }}>
                            {key}
                          </TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {bug.sample_data.map((row, idx) => (
                        <TableRow key={idx}>
                          {Object.values(row).map((val: any, valIdx) => (
                            <TableCell key={valIdx} sx={{ fontSize: '0.7rem' }}>
                              {typeof val === 'number' ? val.toLocaleString() : String(val || '')}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            {/* Azure DevOps Link */}
            {bug.work_item_url && (
              <Box sx={{ mb: 2 }}>
                <Alert severity="info" sx={{ py: 0.5 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block' }}>
                    Azure DevOps Work Item:
                  </Typography>
                  <Typography variant="caption">
                    <a href={bug.work_item_url} target="_blank" rel="noopener noreferrer">
                      #{bug.work_item_id}
                    </a>
                  </Typography>
                </Alert>
              </Box>
            )}

            {/* Tags */}
            {bug.tags && bug.tags.length > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Tags:
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ gap: 0.5 }}>
                  {bug.tags.map((tag, idx) => (
                    <Chip key={idx} label={tag} size="small" variant="outlined" sx={{ fontSize: '0.65rem' }} />
                  ))}
                </Stack>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          <Typography variant="h6">Error Loading Bug Report</Typography>
          <Typography>{error}</Typography>
        </Alert>
        <Button onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Box>
    );
  }

  if (!report) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">Bug report not found: {reportId}</Alert>
        <Button onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Box>
    );
  }

  const filteredBugs = getFilteredBugs();
  const approvedBugs = report.bugs.filter(b => b.status === 'approved');

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <BugReportIcon sx={{ fontSize: 40, color: 'error.main' }} />
            <Box>
              <Typography variant="h4">{report.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                {report.project_name} • Generated {new Date(report.generated_at).toLocaleString()}
              </Typography>
            </Box>
          </Box>
          <Box display="flex" gap={1}>
            <Tooltip title="Refresh">
              <IconButton onClick={fetchReport} color="primary">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton onClick={() => navigate(-1)}>
                <CloseIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        {report.description && (
          <Typography variant="body2" sx={{ mt: 1 }}>
            {report.description}
          </Typography>
        )}
      </Paper>

      {/* Summary Statistics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom sx={{ fontSize: '0.85rem' }}>
                Total Bugs
              </Typography>
              <Typography variant="h4">{report.summary.total_bugs}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3} lg={1.5}>
          <Card sx={{ bgcolor: SEVERITY_COLORS.critical + '20' }}>
            <CardContent>
              <Typography color="text.secondary" gutterBottom sx={{ fontSize: '0.75rem' }}>
                Critical
              </Typography>
              <Typography variant="h5" sx={{ color: SEVERITY_COLORS.critical }}>
                {report.summary.critical_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3} lg={1.5}>
          <Card sx={{ bgcolor: SEVERITY_COLORS.high + '20' }}>
            <CardContent>
              <Typography color="text.secondary" gutterBottom sx={{ fontSize: '0.75rem' }}>
                High
              </Typography>
              <Typography variant="h5" sx={{ color: SEVERITY_COLORS.high }}>
                {report.summary.high_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3} lg={1.5}>
          <Card sx={{ bgcolor: SEVERITY_COLORS.medium + '20' }}>
            <CardContent>
              <Typography color="text.secondary" gutterBottom sx={{ fontSize: '0.75rem' }}>
                Medium
              </Typography>
              <Typography variant="h5" sx={{ color: SEVERITY_COLORS.medium }}>
                {report.summary.medium_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3} lg={1.5}>
          <Card sx={{ bgcolor: SEVERITY_COLORS.low + '20' }}>
            <CardContent>
              <Typography color="text.secondary" gutterBottom sx={{ fontSize: '0.75rem' }}>
                Low
              </Typography>
              <Typography variant="h5" sx={{ color: SEVERITY_COLORS.low }}>
                {report.summary.low_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ bgcolor: 'success.light' }}>
            <CardContent>
              <Typography color="success.dark" gutterBottom sx={{ fontSize: '0.85rem' }}>
                Approved
              </Typography>
              <Typography variant="h4" color="success.dark">{report.summary.approved}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Action Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Actions
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
              <Button
                variant="contained"
                color="primary"
                startIcon={submittingToAzure ? <CircularProgress size={16} /> : <CloudUploadIcon />}
                onClick={handleSubmitToAzureDevOps}
                disabled={selectedBugs.size === 0 || submittingToAzure}
                sx={{ fontWeight: 'bold' }}
              >
                Submit to Azure DevOps ({selectedBugs.size})
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<ThumbDownIcon />}
                disabled={selectedBugs.size === 0}
                onClick={() => handleReviewBugs(false)}
              >
                Reject Selected ({selectedBugs.size})
              </Button>
              <Button
                variant="outlined"
                onClick={handleSelectAll}
              >
                {selectedBugs.size === filteredBugs.length ? 'Deselect All' : 'Select All'}
              </Button>
            </Stack>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Export
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
              <Button
                variant="outlined"
                startIcon={downloadingFormat === 'json' ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownload('json')}
                disabled={!!downloadingFormat}
              >
                JSON
              </Button>
              <Button
                variant="outlined"
                startIcon={downloadingFormat === 'excel' ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownload('excel')}
                disabled={!!downloadingFormat}
              >
                Excel
              </Button>
              <Button
                variant="outlined"
                startIcon={downloadingFormat === 'csv' ? <CircularProgress size={16} /> : <DownloadIcon />}
                onClick={() => handleDownload('csv')}
                disabled={!!downloadingFormat}
              >
                CSV
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Paper>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <FilterListIcon />
          <Typography variant="h6">Filters</Typography>
        </Box>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="pending_review">Pending Review</MenuItem>
                <MenuItem value="approved">Approved</MenuItem>
                <MenuItem value="rejected">Rejected</MenuItem>
                <MenuItem value="created_in_azure">Created in Azure</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Severity
            </Typography>
            <ToggleButtonGroup
              value={severityFilter}
              onChange={(_e, newValue) => setSeverityFilter(newValue)}
              size="small"
            >
              <ToggleButton value="critical">Critical</ToggleButton>
              <ToggleButton value="high">High</ToggleButton>
              <ToggleButton value="medium">Medium</ToggleButton>
              <ToggleButton value="low">Low</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Category
            </Typography>
            <ToggleButtonGroup
              value={categoryFilter}
              onChange={(_e, newValue) => setCategoryFilter(newValue)}
              size="small"
            >
              <ToggleButton value="schema">Schema</ToggleButton>
              <ToggleButton value="data_quality">DQ</ToggleButton>
              <ToggleButton value="referential_integrity">RI</ToggleButton>
            </ToggleButtonGroup>
          </Grid>
        </Grid>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Showing {filteredBugs.length} of {report.summary.total_bugs} bugs
        </Typography>
      </Paper>

      {/* Bug List */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h5" gutterBottom>
          Bugs ({filteredBugs.length})
        </Typography>
        <Divider sx={{ mb: 2 }} />
        {filteredBugs.length === 0 ? (
          <Alert severity="info">No bugs match the current filters</Alert>
        ) : (
          <Box>{filteredBugs.map(bug => renderBugCard(bug))}</Box>
        )}
      </Paper>

      {/* Review Dialog */}
      <Dialog open={reviewDialogOpen} onClose={() => setReviewDialogOpen(false)}>
        <DialogTitle>Review Bugs</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {selectedBugs.size > 0 ? 'approve' : 'reject'} {selectedBugs.size} bug(s)?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialogOpen(false)}>Cancel</Button>
          <Button onClick={() => handleReviewBugs(true)} color="success" variant="contained">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
