import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  LinearProgress,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ContentCopy as ContentCopyIcon,
  Download as DownloadIcon,
  CompareArrows as CompareArrowsIcon,
  BugReport as BugReportIcon,
} from '@mui/icons-material';

const BatchReportViewerSimple: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingBugReport, setGeneratingBugReport] = useState(false);

  // Format detail values for proper rendering (especially arrays of objects as tables)
  const formatDetailValue = (_validatorName: string, key: string, value: any): React.ReactNode => {
    const TABLE_KEYS = ['mismatches', 'issues', 'duplicates', 'results', 'details', 'outliers', 'reason', 'comparison'];

    console.log('[formatDetailValue] key:', key, 'isInTableKeys:', TABLE_KEYS.includes(key), 'isArray:', Array.isArray(value), 'length:', value?.length);

    // Show special formatting for arrays of objects (mismatches, issues, duplicates, etc.)
    if (TABLE_KEYS.includes(key) && Array.isArray(value) && value.length > 0) {
      if (typeof value[0] === 'object' && value[0] !== null && !Array.isArray(value[0])) {
        const headers = Object.keys(value[0]);
        return (
          <TableContainer component={Paper} sx={{ mt: 0.5, mb: 1 }}>
            <Table size="small" sx={{ minWidth: 300 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  {headers.map((k) => (
                    <TableCell key={k} sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold', borderBottom: '2px solid #ddd' }}>
                      {k}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {value.slice(0, 20).map((item: any, idx: number) => (
                  <TableRow key={idx} sx={{ '&:hover': { backgroundColor: '#f9f9f9' } }}>
                    {headers.map((header) => (
                      <TableCell key={header} sx={{ py: 0.5, px: 1, fontSize: '0.65rem' }}>
                        {(() => {
                          const v = item[header];
                          if (typeof v === 'number') return v.toLocaleString();
                          if (typeof v === 'boolean') return String(v);
                          if (typeof v === 'object' && v !== null) return JSON.stringify(v);
                          return String(v || '');
                        })()}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        );
      }
    }

    // For regular arrays
    if (Array.isArray(value)) {
      return (
        <Box component="span" sx={{ display: 'block', ml: 1 }}>
          [{value.length} items] {value.length <= 5 ? value.join(', ') : `${value.slice(0, 5).join(', ')}...`}
        </Box>
      );
    }

    // For objects
    if (typeof value === 'object' && value !== null) {
      const str = JSON.stringify(value);
      return (
        <Box component="span" sx={{ display: 'block', ml: 1 }}>
          {str.length > 100 ? str.substring(0, 100) + '...' : str}
        </Box>
      );
    }

    // For regular values
    return <Box component="span" sx={{ display: 'inline' }}>{String(value)}</Box>;
  };

  useEffect(() => {
    fetchReport();
  }, [jobId]);

  const fetchReport = async () => {
    try {
      console.log('[Simple] Fetching report for:', jobId);
      const response = await fetch(`${__API_URL__}/batch/jobs/${jobId}/report`);
      console.log('[Simple] Response:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('[Simple] Got data:', data);
      setReport(data);
      setError(null);
    } catch (err: any) {
      console.error('[Simple] Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Loading report...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Error: {error}</Alert>
        <Button onClick={() => navigate('/batch')} sx={{ mt: 2 }}>
          Back
        </Button>
      </Box>
    );
  }

  if (!report) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No report data</Alert>
        <Button onClick={() => navigate('/batch')} sx={{ mt: 2 }}>
          Back
        </Button>
      </Box>
    );
  }

  const rep = report.report || {};
  const summary = rep.executive_summary || {};
  const metrics = rep.aggregate_metrics || {};
  const pipelines = rep.pipeline_details || [];
  const tables = rep.table_summary || [];
  const failures = rep.failure_analysis || { critical: [], warnings: [] };
  const debugQueries = rep.debugging_queries || [];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const downloadReport = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-report-${jobId}.json`;
    a.click();
  };

  const handleGenerateBugReport = async () => {
    setGeneratingBugReport(true);
    try {
      const response = await fetch(__API_URL__ + '/bug-reports/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          batch_job_id: jobId,
          batch_job_name: report.job_name || `Batch Job ${jobId}`,
          include_sample_data: true,
          max_samples_per_bug: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      console.log('Bug report generated:', result);

      // Navigate to bug report preview page
      navigate(`/bug-report/${result.report_id}`);
    } catch (err: any) {
      console.error('Failed to generate bug report:', err);
      alert(`Failed to generate bug report: ${err.message}`);
    } finally {
      setGeneratingBugReport(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              📊 Batch Validation Report
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {report.job_name} • Job ID: {report.job_id}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              color="error"
              startIcon={<BugReportIcon />}
              onClick={handleGenerateBugReport}
              disabled={generatingBugReport}
            >
              {generatingBugReport ? 'Generating...' : 'Generate Bug Report'}
            </Button>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={downloadReport}
            >
              Download JSON
            </Button>
          </Box>
        </Box>
        <Button variant="outlined" onClick={() => navigate('/batch')} sx={{ mt: 2 }}>
          ← Back to Batch Operations
        </Button>
      </Paper>

      {/* Executive Summary */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>Executive Summary</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2, mt: 2 }}>
          <Box sx={{ p: 2, bgcolor: '#e3f2fd', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Total Pipelines</Typography>
            <Typography variant="h4">{summary.total_pipelines || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#e3f2fd', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Total Validations</Typography>
            <Typography variant="h4">{summary.total_validations || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: summary.passed > 0 ? '#c8e6c9' : '#ffcdd2', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Passed</Typography>
            <Typography variant="h4" color="success.dark">{summary.passed || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: summary.failed > 0 ? '#ffcdd2' : '#c8e6c9', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Failed</Typography>
            <Typography variant="h4" color="error.dark">{summary.failed || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: (summary.pass_rate || 0) >= 70 ? '#c8e6c9' : '#ffcdd2', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Pass Rate</Typography>
            <Typography variant="h4">{(summary.pass_rate || 0).toFixed(1)}%</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#fff9c4', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Overall Status</Typography>
            <Typography variant="h4">{summary.overall_status || 'UNKNOWN'}</Typography>
          </Box>
        </Box>
      </Paper>

      {/* Aggregate Metrics */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>Aggregate Metrics</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 2, mt: 2 }}>
          <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">SQL Server Rows</Typography>
            <Typography variant="h5">{(metrics.row_count_totals?.sql || 0).toLocaleString()}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Snowflake Rows</Typography>
            <Typography variant="h5">{(metrics.row_count_totals?.snowflake || 0).toLocaleString()}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Row Difference</Typography>
            <Typography variant="h5">{metrics.row_count_totals?.diff || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Schema Mismatches</Typography>
            <Typography variant="h5">{metrics.schema_mismatches || 0}</Typography>
          </Box>
          <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary">Orphaned Keys</Typography>
            <Typography variant="h5">{metrics.orphaned_keys_total || 0}</Typography>
          </Box>
        </Box>
      </Paper>

      {/* Pipeline Details with Validations */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>📋 Detailed Validation Results</Typography>
        {pipelines.length === 0 ? (
          <Alert severity="info">No pipeline details available</Alert>
        ) : (
          pipelines.map((pipeline: any, idx: number) => (
            <Accordion key={idx} defaultExpanded={idx === 0} sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', pr: 2 }}>
                  <Typography variant="h6">{pipeline.pipeline_name || `Pipeline ${idx + 1}`}</Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Chip
                      label={pipeline.status || 'UNKNOWN'}
                      color={pipeline.status === 'completed' ? 'success' : 'error'}
                      size="small"
                    />
                    <Chip
                      label={`${((pipeline.duration_ms || 0) / 1000).toFixed(1)}s`}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      icon={<CheckCircleIcon />}
                      label={`${pipeline.pass_count || 0} Passed`}
                      color="success"
                      size="small"
                    />
                    <Chip
                      icon={<ErrorIcon />}
                      label={`${pipeline.fail_count || 0} Failed`}
                      color="error"
                      size="small"
                    />
                  </Box>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Validation Step</strong></TableCell>
                        <TableCell><strong>Status</strong></TableCell>
                        <TableCell><strong>Severity</strong></TableCell>
                        <TableCell><strong>Details & Comparison Data</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(pipeline.validations || []).map((validation: any, vIdx: number) => (
                        <TableRow key={vIdx}>
                          <TableCell>{validation.name || `Step ${vIdx + 1}`}</TableCell>
                          <TableCell>
                            {validation.status === 'PASS' ? (
                              <Chip icon={<CheckCircleIcon />} label="PASS" color="success" size="small" />
                            ) : validation.status === 'FAIL' ? (
                              <Chip icon={<ErrorIcon />} label="FAIL" color="error" size="small" />
                            ) : (
                              <Chip label={validation.status || 'SKIPPED'} size="small" variant="outlined" />
                            )}
                          </TableCell>
                          <TableCell>
                            {validation.severity && validation.severity !== 'NONE' && (
                              <Chip
                                label={validation.severity}
                                size="small"
                                color={validation.severity === 'HIGH' ? 'error' : validation.severity === 'MEDIUM' ? 'warning' : 'default'}
                              />
                            )}
                          </TableCell>
                          <TableCell>
                            {validation.message && (
                              <Typography variant="body2" sx={{ mb: 1 }}>
                                {validation.message}
                              </Typography>
                            )}

                            {/* Display validation details with proper table rendering */}
                            {validation.details && Object.keys(validation.details).length > 0 && (
                              <Box sx={{ mt: 1, p: 1, bgcolor: '#f9f9f9', borderRadius: 1 }}>
                                <Typography variant="caption" fontWeight="bold" display="block" sx={{ mb: 0.5 }}>
                                  Validation Details:
                                </Typography>
                                {Object.entries(validation.details).map(([key, value]: [string, any]) => (
                                  <Box key={key} sx={{ mb: 0.5 }}>
                                    <Typography variant="caption" fontWeight="bold" display="block" sx={{ color: 'primary.main' }}>
                                      {key}:
                                    </Typography>
                                    {formatDetailValue(validation.name, key, value)}
                                  </Box>
                                ))}
                              </Box>
                            )}

                            {/* View Comparison Button - Show for validations with comparison details */}
                            {rep.consolidated_run_id && (validation.comparison_details ||
                              validation.details?.comparison_details ||
                              (validation.sql_row_count !== undefined && validation.snow_row_count !== undefined) ||
                              validation.name?.toLowerCase().includes('comparative') ||
                              validation.name?.toLowerCase().includes('custom_sql') ||
                              validation.name?.toLowerCase().startsWith('query_') ||
                              validation.name?.toLowerCase().includes('total ')) && (
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<CompareArrowsIcon />}
                                onClick={() => navigate(`/comparison/${rep.consolidated_run_id}/${validation.name}`)}
                                sx={{ mb: 1, fontSize: '0.75rem' }}
                              >
                                View Comparison
                              </Button>
                            )}

                            {/* Display comparison data from key_metrics */}
                            {validation.key_metrics && Object.keys(validation.key_metrics).length > 0 && (
                              <Box sx={{ mt: 1, p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                                <Typography variant="caption" fontWeight="bold" display="block" sx={{ mb: 0.5 }}>
                                  Comparison Data:
                                </Typography>
                                {Object.entries(validation.key_metrics).map(([key, value]: [string, any]) => {
                                  // Special rendering for arrays
                                  if (Array.isArray(value)) {
                                    return (
                                      <Typography key={key} variant="caption" display="block" sx={{ ml: 1 }}>
                                        <strong>{key}:</strong> [{value.length} items] {value.length <= 5 ? value.join(', ') : `${value.slice(0, 5).join(', ')}...`}
                                      </Typography>
                                    );
                                  }
                                  // Special rendering for objects
                                  else if (typeof value === 'object' && value !== null) {
                                    return (
                                      <Typography key={key} variant="caption" display="block" sx={{ ml: 1 }}>
                                        <strong>{key}:</strong> {JSON.stringify(value).length > 100 ? JSON.stringify(value).substring(0, 100) + '...' : JSON.stringify(value)}
                                      </Typography>
                                    );
                                  }
                                  // Regular values
                                  return (
                                    <Typography key={key} variant="caption" display="block" sx={{ ml: 1 }}>
                                      <strong>{key}:</strong> {String(value)}
                                    </Typography>
                                  );
                                })}
                              </Box>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          ))
        )}
      </Paper>

      {/* Failure Analysis */}
      {(failures.critical?.length > 0 || failures.warnings?.length > 0) && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>🔍 Failure Analysis</Typography>

          {failures.critical && failures.critical.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" color="error" gutterBottom>
                <ErrorIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Critical Issues ({failures.critical.length})
              </Typography>
              {failures.critical.map((issue: any, idx: number) => (
                <Alert key={idx} severity="error" sx={{ mb: 1 }}>
                  <Typography variant="subtitle2">{issue.validation || issue.message}</Typography>
                  {issue.details && <Typography variant="caption">{issue.details}</Typography>}
                </Alert>
              ))}
            </Box>
          )}

          {failures.warnings && failures.warnings.length > 0 && (
            <Box>
              <Typography variant="h6" color="warning.main" gutterBottom>
                <WarningIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                Warnings ({failures.warnings.length})
              </Typography>
              {failures.warnings.map((warning: any, idx: number) => (
                <Alert key={idx} severity="warning" sx={{ mb: 1 }}>
                  <Typography variant="subtitle2">{warning.validation || warning.message}</Typography>
                  {warning.details && <Typography variant="caption">{warning.details}</Typography>}
                </Alert>
              ))}
            </Box>
          )}
        </Paper>
      )}

      {/* Debugging Queries */}
      {debugQueries && debugQueries.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>🔧 Debugging SQL Queries</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Use these queries to investigate failures and data mismatches
          </Typography>

          {debugQueries.map((queryGroup: any, idx: number) => (
            <Accordion key={idx} sx={{ mb: 1 }} defaultExpanded={idx === 0}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                  <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                    {queryGroup.validation || `Validation ${idx + 1}`}
                  </Typography>
                  <Chip
                    label={queryGroup.table || 'Unknown Table'}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={`${(queryGroup.queries || []).length} queries`}
                    size="small"
                    color="primary"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {queryGroup.issue && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    <strong>Issue:</strong> {queryGroup.issue}
                  </Alert>
                )}

                {(queryGroup.queries || []).map((query: any, qIdx: number) => (
                  <Box key={qIdx} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, color: 'primary.main' }}>
                      {query.purpose || `Query ${qIdx + 1}`}
                    </Typography>
                    <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.secondary' }}>
                      Database: {query.database || 'Both'}
                    </Typography>
                    <Paper sx={{ p: 2, bgcolor: '#263238', color: '#aed581', position: 'relative' }}>
                      <Tooltip title="Copy to clipboard">
                        <IconButton
                          size="small"
                          onClick={() => copyToClipboard(query.query)}
                          sx={{ position: 'absolute', top: 8, right: 8, color: 'white' }}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <pre style={{ margin: 0, overflow: 'auto', maxHeight: '300px', fontSize: '13px' }}>
                        {query.query}
                      </pre>
                    </Paper>
                  </Box>
                ))}
              </AccordionDetails>
            </Accordion>
          ))}
        </Paper>
      )}

      {/* Table Summary */}
      {tables && tables.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>📊 Table-by-Table Summary</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Table</strong></TableCell>
                  <TableCell align="right"><strong>Total Checks</strong></TableCell>
                  <TableCell align="right"><strong>Passed</strong></TableCell>
                  <TableCell align="right"><strong>Failed</strong></TableCell>
                  <TableCell align="right"><strong>Pass Rate</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tables.map((table: any, idx: number) => (
                  <TableRow key={idx}>
                    <TableCell>{table.table_name || table.name || 'Unknown'}</TableCell>
                    <TableCell align="right">{table.total_validations || 0}</TableCell>
                    <TableCell align="right" sx={{ color: 'success.main' }}>{table.passed || 0}</TableCell>
                    <TableCell align="right" sx={{ color: 'error.main' }}>{table.failed || 0}</TableCell>
                    <TableCell align="right">
                      <Chip
                        label={`${(table.pass_rate || 0).toFixed(1)}%`}
                        color={(table.pass_rate || 0) >= 70 ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Debug View (Collapsible) */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">🐛 Raw Data (Debug View)</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, bgcolor: '#f5f5f5', maxHeight: '400px', overflow: 'auto' }}>
            <pre style={{ margin: 0, fontSize: '12px' }}>
              {JSON.stringify(report, null, 2)}
            </pre>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default BatchReportViewerSimple;
