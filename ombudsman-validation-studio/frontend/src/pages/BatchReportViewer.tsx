import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  Alert,
  Divider,
  Stack,
  IconButton,
  Tooltip,
  Tab,
  Tabs,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ArrowBack as ArrowBackIcon,
  Assessment as AssessmentIcon,
  BugReport as BugReportIcon,
  TableChart as TableChartIcon,
  Code as CodeIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const BatchReportViewer: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchReport();
  }, [jobId]);

  const fetchReport = async () => {
    try {
      console.log('[BatchReportViewer] Fetching report for job:', jobId);
      const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}/report`);
      console.log('[BatchReportViewer] Response status:', response.status);
      if (!response.ok) throw new Error('Failed to fetch report');
      const data = await response.json();
      console.log('[BatchReportViewer] Report data received:', data);
      console.log('[BatchReportViewer] Report keys:', Object.keys(data));
      console.log('[BatchReportViewer] Has report object:', 'report' in data);
      setReport(data);
    } catch (err: any) {
      console.error('[BatchReportViewer] Error fetching report:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-report-${jobId}.json`;
    a.click();
  };

  const downloadHTML = () => {
    const htmlContent = generateHTMLReport();
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-report-${jobId}.html`;
    a.click();
  };

  const generateHTMLReport = () => {
    const rep = report.report;
    return `
<!DOCTYPE html>
<html>
<head>
  <title>Batch Validation Report - ${report.job_name}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
    h1 { color: #1976d2; border-bottom: 3px solid #1976d2; padding-bottom: 10px; }
    h2 { color: #424242; margin-top: 30px; }
    .summary-card { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .metric { display: inline-block; margin: 10px 20px 10px 0; }
    .metric-label { font-weight: bold; color: #666; }
    .metric-value { font-size: 24px; color: #1976d2; }
    .pass { color: #4caf50; }
    .fail { color: #f44336; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th { background: #1976d2; color: white; padding: 12px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #ddd; }
    tr:hover { background: #f5f5f5; }
    .code-block { background: #263238; color: #aed581; padding: 15px; border-radius: 4px; overflow-x: auto; }
    .status-badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
    .status-pass { background: #c8e6c9; color: #2e7d32; }
    .status-fail { background: #ffcdd2; color: #c62828; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 Batch Validation Report</h1>
    <p><strong>Job Name:</strong> ${report.job_name}</p>
    <p><strong>Generated:</strong> ${new Date(rep.generated_at).toLocaleString()}</p>

    <div class="summary-card">
      <h2>Executive Summary</h2>
      <div class="metric">
        <div class="metric-label">Total Pipelines</div>
        <div class="metric-value">${rep.executive_summary.total_pipelines}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Total Validations</div>
        <div class="metric-value">${rep.executive_summary.total_validations}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Pass Rate</div>
        <div class="metric-value ${rep.executive_summary.pass_rate >= 70 ? 'pass' : 'fail'}">
          ${rep.executive_summary.pass_rate.toFixed(1)}%
        </div>
      </div>
      <div class="metric">
        <div class="metric-label">Status</div>
        <div class="metric-value ${rep.executive_summary.overall_status === 'PASS' ? 'pass' : 'fail'}">
          ${rep.executive_summary.overall_status}
        </div>
      </div>
    </div>

    <h2>📈 Aggregate Metrics</h2>
    <table>
      <tr>
        <th>Metric</th>
        <th>SQL Server</th>
        <th>Snowflake</th>
        <th>Difference</th>
      </tr>
      <tr>
        <td>Total Row Count</td>
        <td>${rep.aggregate_metrics.row_count_totals.sql.toLocaleString()}</td>
        <td>${rep.aggregate_metrics.row_count_totals.snowflake.toLocaleString()}</td>
        <td>${rep.aggregate_metrics.row_count_totals.diff}</td>
      </tr>
      <tr>
        <td>Schema Mismatches</td>
        <td colspan="3">${rep.aggregate_metrics.schema_mismatches}</td>
      </tr>
      <tr>
        <td>Orphaned Keys</td>
        <td colspan="3">${rep.aggregate_metrics.orphaned_keys_total}</td>
      </tr>
    </table>

    <h2>🔍 Validation Details by Pipeline</h2>
    ${rep.pipelines.map((pipeline: any) => `
      <h3>${pipeline.pipeline_name}</h3>
      <p><strong>Status:</strong> <span class="status-badge status-${pipeline.status.toLowerCase()}">${pipeline.status}</span></p>
      <p><strong>Duration:</strong> ${(pipeline.duration_ms / 1000).toFixed(1)}s</p>
      <p><strong>Results:</strong> ${pipeline.pass_count} passed, ${pipeline.fail_count} failed out of ${pipeline.total_validations} validations</p>

      <table>
        <tr>
          <th>Validation</th>
          <th>Status</th>
          <th>Details</th>
        </tr>
        ${pipeline.validations.slice(0, 10).map((val: any) => `
          <tr>
            <td>${val.name}</td>
            <td><span class="status-badge status-${val.status.toLowerCase()}">${val.status}</span></td>
            <td>${val.message || 'N/A'}</td>
          </tr>
        `).join('')}
      </table>
    `).join('')}
  </div>
</body>
</html>
    `;
  };

  console.log('[BatchReportViewer] Render - loading:', loading, 'error:', error, 'report:', !!report);

  if (loading) {
    console.log('[BatchReportViewer] Rendering loading state');
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Loading Report...</Typography>
        <LinearProgress />
      </Box>
    );
  }

  if (error || !report) {
    console.log('[BatchReportViewer] Rendering error state - error:', error, 'report:', report);
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load report: {error || 'No report data'}</Alert>
        <Button onClick={() => navigate('/batch')} sx={{ mt: 2 }}>
          Back to Batch Operations
        </Button>
      </Box>
    );
  }

  // Check if report has the nested structure
  if (!report.report) {
    console.log('[BatchReportViewer] Report missing nested structure. Keys:', Object.keys(report));
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Invalid report structure - missing report data</Alert>
        <Button onClick={() => navigate('/batch')} sx={{ mt: 2 }}>
          Back to Batch Operations
        </Button>
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption">Debug: {JSON.stringify(Object.keys(report))}</Typography>
        </Box>
      </Box>
    );
  }

  console.log('[BatchReportViewer] Rendering main report view');

  const rep = report.report;
  const summary = rep.executive_summary || {};
  const aggregateMetrics = rep.aggregate_metrics || {
    row_count_totals: { sql: 0, snowflake: 0, diff: 0 },
    schema_mismatches: 0,
    orphaned_keys_total: 0
  };
  const tableSummary = rep.table_summary || [];
  const pipelines = rep.pipeline_details || [];
  const failureAnalysis = rep.failure_analysis || { critical: [], warnings: [] };
  const debuggingQueries = rep.debugging_queries || [];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Box>
            <Stack direction="row" alignItems="center" spacing={2}>
              <IconButton onClick={() => navigate('/batch-operations')}>
                <ArrowBackIcon />
              </IconButton>
              <Box>
                <Typography variant="h4">
                  📊 Batch Validation Report
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {report.job_name} • Generated {new Date(rep.generated_at).toLocaleString()}
                </Typography>
              </Box>
            </Stack>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={downloadJSON}
            >
              JSON
            </Button>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={downloadHTML}
            >
              HTML Report
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Executive Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Pipelines
              </Typography>
              <Typography variant="h3" color="primary">
                {summary.total_pipelines || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total Validations
              </Typography>
              <Typography variant="h3" color="primary">
                {summary.total_validations || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Pass Rate
              </Typography>
              <Typography
                variant="h3"
                color={(summary.pass_rate || 0) >= 70 ? 'success.main' : 'error.main'}
              >
                {(summary.pass_rate || 0).toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={summary.pass_rate || 0}
                color={(summary.pass_rate || 0) >= 70 ? 'success' : 'error'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Overall Status
              </Typography>
              <Chip
                label={summary.overall_status || 'UNKNOWN'}
                color={(summary.overall_status || '').toUpperCase() === 'PASS' ? 'success' : 'error'}
                icon={(summary.overall_status || '').toUpperCase() === 'PASS' ? <CheckCircleIcon /> : <ErrorIcon />}
                sx={{ fontSize: '1.2rem', fontWeight: 'bold', py: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for Different Views */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab icon={<AssessmentIcon />} label="Overview" />
          <Tab icon={<TableChartIcon />} label="Validation Details" />
          <Tab icon={<BugReportIcon />} label="Failure Analysis" />
          <Tab icon={<CodeIcon />} label="Debugging Queries" />
          <Tab icon={<TimelineIcon />} label="Performance" />
        </Tabs>
      </Paper>

      {/* Tab 0: Overview */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          {/* Aggregate Metrics */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                📈 Aggregate Metrics
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Metric</strong></TableCell>
                      <TableCell align="right"><strong>SQL Server</strong></TableCell>
                      <TableCell align="right"><strong>Snowflake</strong></TableCell>
                      <TableCell align="right"><strong>Diff</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Row Count</TableCell>
                      <TableCell align="right">{aggregateMetrics.row_count_totals.sql.toLocaleString()}</TableCell>
                      <TableCell align="right">{aggregateMetrics.row_count_totals.snowflake.toLocaleString()}</TableCell>
                      <TableCell align="right">{aggregateMetrics.row_count_totals.diff}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Schema Mismatches</TableCell>
                      <TableCell align="right" colSpan={3}>{aggregateMetrics.schema_mismatches}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Orphaned Keys</TableCell>
                      <TableCell align="right" colSpan={3}>{aggregateMetrics.orphaned_keys_total}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Null Count</TableCell>
                      <TableCell align="right" colSpan={3}>{aggregateMetrics.null_count_total || 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Duplicate Count</TableCell>
                      <TableCell align="right" colSpan={3}>{aggregateMetrics.duplicate_count_total || 0}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>

          {/* Validation Summary */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                ✅ Validation Summary
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Stack spacing={2}>
                <Box>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">Passed</Typography>
                    <Typography variant="h6" color="success.main">{summary.passed}</Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={(summary.passed / summary.total_validations) * 100}
                    color="success"
                  />
                </Box>
                <Box>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2">Failed</Typography>
                    <Typography variant="h6" color="error.main">{summary.failed}</Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={(summary.failed / summary.total_validations) * 100}
                    color="error"
                  />
                </Box>
                <Divider />
                <Typography variant="body2" color="text.secondary">
                  <strong>Tables Validated:</strong> {summary.tables_validated}
                </Typography>
                <Box>
                  {summary.table_list.map((table: string) => (
                    <Chip key={table} label={table} size="small" sx={{ mr: 1 }} />
                  ))}
                </Box>
              </Stack>
            </Paper>
          </Grid>

          {/* Table Summary */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                🗂️ Table Summary
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Table</strong></TableCell>
                      <TableCell align="center"><strong>Validations</strong></TableCell>
                      <TableCell align="center"><strong>Passed</strong></TableCell>
                      <TableCell align="center"><strong>Failed</strong></TableCell>
                      <TableCell><strong>Critical Issues</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rep.table_summary.map((table: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>{table.table_name}</TableCell>
                        <TableCell align="center">{table.total_validations}</TableCell>
                        <TableCell align="center">
                          <Chip label={table.passed} color="success" size="small" />
                        </TableCell>
                        <TableCell align="center">
                          <Chip label={table.failed} color="error" size="small" />
                        </TableCell>
                        <TableCell>
                          {table.critical_issues.length > 0 ? (
                            <Tooltip title={table.critical_issues.map((i: any) => i.validation).join(', ')}>
                              <Chip
                                label={`${table.critical_issues.length} issues`}
                                color="error"
                                size="small"
                                icon={<ErrorIcon />}
                              />
                            </Tooltip>
                          ) : (
                            <Chip label="None" color="success" size="small" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Tab 1: Validation Details */}
      <TabPanel value={tabValue} index={1}>
        {rep.pipelines.map((pipeline: any, idx: number) => (
          <Accordion key={idx} defaultExpanded={idx === 0}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
                <Typography variant="h6">{pipeline.pipeline_name}</Typography>
                <Chip
                  label={pipeline.status}
                  color={pipeline.status === 'PASS' ? 'success' : 'error'}
                  size="small"
                />
                <Typography variant="body2" color="text.secondary">
                  {pipeline.pass_count}/{pipeline.total_validations} passed • {(pipeline.duration_ms / 1000).toFixed(1)}s
                </Typography>
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Validation</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                      <TableCell><strong>Severity</strong></TableCell>
                      <TableCell><strong>Message</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pipeline.validations.map((validation: any, vidx: number) => (
                      <TableRow key={vidx}>
                        <TableCell>{validation.name}</TableCell>
                        <TableCell>
                          <Chip
                            label={validation.status}
                            color={validation.status === 'PASS' ? 'success' : 'error'}
                            size="small"
                            icon={validation.status === 'PASS' ? <CheckCircleIcon /> : <ErrorIcon />}
                          />
                        </TableCell>
                        <TableCell>
                          {validation.severity && validation.severity !== 'NONE' && (
                            <Chip
                              label={validation.severity}
                              color={validation.severity === 'HIGH' ? 'error' : 'warning'}
                              size="small"
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{validation.message || 'No issues'}</Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </AccordionDetails>
          </Accordion>
        ))}
      </TabPanel>

      {/* Tab 2: Failure Analysis */}
      <TabPanel value={tabValue} index={2}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            🔍 Failure Analysis
          </Typography>
          <Divider sx={{ mb: 2 }} />
          {rep.failure_analysis && Object.keys(rep.failure_analysis).length > 0 ? (
            Object.entries(rep.failure_analysis).map(([category, failures]: [string, any]) => (
              <Accordion key={category}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="subtitle1">{category}</Typography>
                    <Chip label={`${failures.length} failures`} size="small" color="error" />
                  </Stack>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>Validation</strong></TableCell>
                          <TableCell><strong>Table</strong></TableCell>
                          <TableCell><strong>Message</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {failures.map((failure: any, idx: number) => (
                          <TableRow key={idx}>
                            <TableCell>{failure.validation}</TableCell>
                            <TableCell>{failure.table}</TableCell>
                            <TableCell>{failure.message}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>
            ))
          ) : (
            <Alert severity="success">No failures detected!</Alert>
          )}
        </Paper>
      </TabPanel>

      {/* Tab 3: Debugging Queries */}
      <TabPanel value={tabValue} index={3}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            💻 Debugging SQL Queries
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Alert severity="info" sx={{ mb: 2 }}>
            Use these queries to investigate validation failures in your databases
          </Alert>
          {rep.pipelines.map((pipeline: any, idx: number) => (
            <Accordion key={idx}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="subtitle1">{pipeline.pipeline_name}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {pipeline.validations
                  .filter((v: any) => v.status === 'FAIL' && v.details)
                  .map((validation: any, vidx: number) => (
                    <Box key={vidx} sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        {validation.name}
                      </Typography>
                      {validation.details.sql_query && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            SQL Server Query:
                          </Typography>
                          <Paper
                            sx={{
                              p: 2,
                              bgcolor: '#263238',
                              color: '#aed581',
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              overflowX: 'auto',
                              mb: 1,
                            }}
                          >
                            <pre style={{ margin: 0 }}>{validation.details.sql_query}</pre>
                          </Paper>
                        </Box>
                      )}
                      {validation.details.snow_query && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            Snowflake Query:
                          </Typography>
                          <Paper
                            sx={{
                              p: 2,
                              bgcolor: '#263238',
                              color: '#aed581',
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              overflowX: 'auto',
                            }}
                          >
                            <pre style={{ margin: 0 }}>{validation.details.snow_query}</pre>
                          </Paper>
                        </Box>
                      )}
                    </Box>
                  ))}
              </AccordionDetails>
            </Accordion>
          ))}
        </Paper>
      </TabPanel>

      {/* Tab 4: Performance */}
      <TabPanel value={tabValue} index={4}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                ⚡ Pipeline Performance
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Pipeline</strong></TableCell>
                      <TableCell align="center"><strong>Duration</strong></TableCell>
                      <TableCell align="center"><strong>Validations</strong></TableCell>
                      <TableCell align="center"><strong>Avg Time per Validation</strong></TableCell>
                      <TableCell align="center"><strong>Status</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rep.pipelines.map((pipeline: any, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell>{pipeline.pipeline_name}</TableCell>
                        <TableCell align="center">
                          {(pipeline.duration_ms / 1000).toFixed(2)}s
                        </TableCell>
                        <TableCell align="center">{pipeline.total_validations}</TableCell>
                        <TableCell align="center">
                          {(pipeline.duration_ms / pipeline.total_validations / 1000).toFixed(2)}s
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={pipeline.status}
                            color={pipeline.status === 'PASS' ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  );
};

export default BatchReportViewer;
