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
  ToggleButton,
  ToggleButtonGroup,
  Stack
} from "@mui/material";
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import RefreshIcon from '@mui/icons-material/Refresh';
import DownloadIcon from '@mui/icons-material/Download';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SchemaIcon from '@mui/icons-material/AccountTree';
import DataQualityIcon from '@mui/icons-material/VerifiedUser';
import BusinessIcon from '@mui/icons-material/BusinessCenter';
import TimeSeriesIcon from '@mui/icons-material/Timeline';
import IntegrityIcon from '@mui/icons-material/Link';

// Category mapping for validation types
const CATEGORY_MAP: Record<string, { label: string; icon: any; color: string }> = {
  schema: { label: 'Schema Validation', icon: SchemaIcon, color: '#1976d2' },
  dq: { label: 'Data Quality', icon: DataQualityIcon, color: '#2e7d32' },
  business: { label: 'Business Metrics', icon: BusinessIcon, color: '#ed6c02' },
  timeseries: { label: 'Time Series Analysis', icon: TimeSeriesIcon, color: '#9c27b0' },
  ri: { label: 'Referential Integrity', icon: IntegrityIcon, color: '#d32f2f' }
};

export default function ResultsViewer() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

  useEffect(() => {
    if (runId) {
      fetchResults();
    }
  }, [runId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      setError(null);

      // First try to get from the status endpoint
      let response = await fetch(`http://localhost:8000/pipelines/status/${runId}`);
      if (!response.ok) {
        // If that fails, try the execution results endpoint
        response = await fetch(`http://localhost:8000/execution/results?run_id=${runId}`);
      }

      if (!response.ok) throw new Error('Failed to fetch results');
      const data = await response.json();

      console.log('Fetched results:', data);
      setResults(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
      case 'SUCCESS':
      case 'COMPLETED':
        return 'success';
      case 'FAIL':
      case 'FAILED':
      case 'ERROR':
        return 'error';
      case 'SKIPPED':
        return 'warning';
      case 'RUNNING':
      case 'IN_PROGRESS':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
      case 'SUCCESS':
      case 'COMPLETED':
        return <CheckCircleIcon color="success" />;
      case 'FAIL':
      case 'FAILED':
      case 'ERROR':
        return <ErrorIcon color="error" />;
      case 'SKIPPED':
        return <WarningIcon color="warning" />;
      case 'RUNNING':
      case 'IN_PROGRESS':
        return <CircularProgress size={20} />;
      default:
        return <InfoIcon />;
    }
  };

  const getStepCategory = (stepName: string, stepDef?: any): string => {
    // If we have pipeline definition, use the type from there
    if (stepDef?.type) {
      return stepDef.type;
    }

    // Otherwise, infer from step name
    const name = stepName.toLowerCase();
    if (name.includes('schema')) return 'schema';
    if (name.includes('data_quality') || name.includes('statistical') || name.includes('distribution') || name.includes('outlier')) return 'dq';
    if (name.includes('business') || name.includes('metric')) return 'business';
    if (name.includes('time') || name.includes('period') || name.includes('rolling') || name.includes('temporal')) return 'timeseries';
    if (name.includes('referential') || name.includes('foreign') || name.includes('conformance')) return 'ri';
    return 'dq'; // default
  };

  const getStepDefinition = (stepName: string) => {
    if (!results?.pipeline_def?.pipeline?.steps) return null;
    return results.pipeline_def.pipeline.steps.find((s: any) => s.name === stepName);
  };

  const handleCategoryFilter = (_event: React.MouseEvent<HTMLElement>, newCategories: string[]) => {
    setSelectedCategories(newCategories);
  };

  const downloadResults = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `pipeline-results-${runId}.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const getSummaryMessage = (validatorName: string, details: any): string | null => {
    // Handle errors/exceptions specially
    if (details.exception) {
      let error = String(details.exception);
      if (error.includes('datetime.date(')) {
        return 'Date formatting error - validator needs to convert dates to strings';
      }
      if (error.includes('division by zero')) {
        return 'Division by zero error - check for null or zero values in data';
      }
      if (error.includes('KeyError') || error.includes('not found')) {
        return `Missing required data: ${error.replace('KeyError:', '').trim()}`;
      }
      return `Error: ${error.substring(0, 100)}${error.length > 100 ? '...' : ''}`;
    }

    // Generate human-readable summary based on validator type and results
    if (validatorName === 'validate_record_counts') {
      const diff = Math.abs((details.sql_count || 0) - (details.snow_count || 0));
      return `Row count mismatch: SQL has ${details.sql_count?.toLocaleString()} rows, Snowflake has ${details.snow_count?.toLocaleString()} rows (difference: ${diff.toLocaleString()})`;
    }

    if (validatorName === 'validate_schema_columns') {
      const missing = details.mismatch_count || (details.missing_in_sql?.length || 0) + (details.missing_in_snow?.length || 0);
      if (missing > 0) {
        const parts = [];
        if (details.missing_in_snow?.length > 0) parts.push(`${details.missing_in_snow.length} columns missing in Snowflake`);
        if (details.missing_in_sql?.length > 0) parts.push(`${details.missing_in_sql.length} columns missing in SQL Server`);
        return parts.join(', ');
      }
      return 'All columns match between systems';
    }

    if (validatorName === 'validate_schema_datatypes') {
      const count = details.mismatch_count || details.mismatches?.length || 0;
      if (count > 0) {
        return `${count} column${count > 1 ? 's have' : ' has'} different data types between SQL Server and Snowflake`;
      }
      return 'All data types match';
    }

    if (validatorName === 'validate_schema_nullability') {
      const count = details.mismatch_count || details.mismatches?.length || 0;
      if (count > 0) {
        return `${count} column${count > 1 ? 's have' : ' has'} different nullability constraints`;
      }
      return 'All nullability constraints match';
    }

    if (validatorName === 'validate_metric_sums') {
      const count = details.issues?.length || 0;
      if (count > 0) {
        return `${count} metric column${count > 1 ? 's have' : ' has'} different sum values between systems`;
      }
      return 'All metric sums match';
    }

    if (validatorName === 'validate_ts_duplicates') {
      const count = details.duplicate_count || details.duplicates?.length || 0;
      if (count > 0) {
        return `Found ${count} duplicate timestamp${count > 1 ? 's' : ''}`;
      }
      return 'No duplicate timestamps';
    }

    if (validatorName === 'validate_ts_continuity') {
      const missing = details.missing_count || 0;
      if (missing > 0) {
        return `${missing} date${missing > 1 ? 's are' : ' is'} missing in the time series (${details.min_date} to ${details.max_date})`;
      }
      return 'Complete time series with no gaps';
    }

    if (validatorName === 'validate_ts_rolling_drift') {
      const count = details.issues?.length || 0;
      if (count > 0) {
        return `Found ${count} rolling window drift issue${count > 1 ? 's' : ''} across 7-day and 30-day windows`;
      }
      return 'No rolling window drift detected';
    }

    if (validatorName === 'validate_period_over_period') {
      const count = details.issues?.length || 0;
      if (count > 0) {
        return `Found ${count} period-over-period comparison issue${count > 1 ? 's' : ''} (WoW/MoM/YoY)`;
      }
      return 'All period-over-period comparisons match';
    }

    return null;
  };

  const formatDetailValue = (_validatorName: string, key: string, value: any): React.ReactNode => {
    // Show special formatting for arrays of objects (mismatches, issues, etc.)
    if ((key === 'mismatches' || key === 'issues' || key === 'duplicates' || key === 'results' || key === 'details' || key === 'outliers' || key === 'reason') && Array.isArray(value) && value.length > 0) {
      if (typeof value[0] === 'object' && value[0] !== null && !Array.isArray(value[0])) {
        const headers = Object.keys(value[0]);
        const showCount = 20;

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
                {value.slice(0, showCount).map((item: any, idx: number) => (
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
            {value.length > showCount && (
              <Typography variant="caption" sx={{ p: 0.5, display: 'block', fontSize: '0.6rem', color: 'text.secondary', textAlign: 'center', backgroundColor: '#f5f5f5' }}>
                Showing {showCount} of {value.length} items
              </Typography>
            )}
          </TableContainer>
        );
      }

      // Handle arrays of arrays
      if (Array.isArray(value[0])) {
        const showCount = 20;
        return (
          <TableContainer component={Paper} sx={{ mt: 0.5, mb: 1 }}>
            <Table size="small" sx={{ minWidth: 300 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  {value[0].map((_: any, idx: number) => (
                    <TableCell key={idx} sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold', borderBottom: '2px solid #ddd' }}>
                      Column {idx + 1}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {value.slice(0, showCount).map((row: any, rowIdx: number) => (
                  <TableRow key={rowIdx} sx={{ '&:hover': { backgroundColor: '#f9f9f9' } }}>
                    {row.map((cell: any, cellIdx: number) => (
                      <TableCell key={cellIdx} sx={{ py: 0.5, px: 1, fontSize: '0.65rem' }}>
                        {typeof cell === 'number' ? cell.toLocaleString() : String(cell || '')}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {value.length > showCount && (
              <Typography variant="caption" sx={{ p: 0.5, display: 'block', fontSize: '0.6rem', color: 'text.secondary', textAlign: 'center', backgroundColor: '#f5f5f5' }}>
                Showing {showCount} of {value.length} items
              </Typography>
            )}
          </TableContainer>
        );
      }
    }

    // Handle objects (like reason objects with ratio/metric data)
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      const entries = Object.entries(value);
      if (entries.length === 0) return <em style={{color: '#999'}}>empty</em>;

      // Check if this looks like ratio/metric data (has numerator_column, denominator_column, or column fields)
      const isRatioOrMetricData = entries.some(([_k, v]: any) =>
        v && typeof v === 'object' && (v.numerator_column || v.denominator_column || v.column)
      );

      if (isRatioOrMetricData) {
        // Display as table
        return (
          <TableContainer component={Paper} sx={{ mt: 0.5, mb: 1 }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold' }}>Item</TableCell>
                  <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold' }}>Numerator Column</TableCell>
                  <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold' }}>Denominator Column</TableCell>
                  <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontWeight: 'bold' }}>Column</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {entries.map(([k, v]: any) => (
                  <TableRow key={k} sx={{ '&:hover': { backgroundColor: '#f9f9f9' } }}>
                    <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem', fontFamily: 'monospace' }}>
                      {k}
                    </TableCell>
                    <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem' }}>
                      {v?.numerator_column || '-'}
                    </TableCell>
                    <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem' }}>
                      {v?.denominator_column || '-'}
                    </TableCell>
                    <TableCell sx={{ py: 0.5, px: 1, fontSize: '0.65rem' }}>
                      {v?.column || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        );
      }

      // Check for SQL queries
      const hasSQLFields = entries.some(([k, v]) =>
        k.toLowerCase().includes('sql') ||
        k.toLowerCase().includes('query') ||
        (typeof v === 'string' && v.trim().toUpperCase().startsWith('SELECT'))
      );

      if (hasSQLFields) {
        return (
          <Box>
            {entries.map(([k, v]: any) => {
              const isSQL = k.toLowerCase().includes('sql') ||
                           k.toLowerCase().includes('query') ||
                           (typeof v === 'string' && v.trim().toUpperCase().startsWith('SELECT'));

              if (isSQL && v) {
                return (
                  <Box key={k} sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                      {k.replace(/_/g, ' ').toUpperCase()}:
                    </Typography>
                    <Box sx={{
                      fontFamily: 'Courier New, monospace',
                      fontSize: '0.65rem',
                      whiteSpace: 'pre-wrap',
                      bgcolor: '#1e1e1e',
                      color: '#d4d4d4',
                      p: 1,
                      borderRadius: 1,
                      overflowX: 'auto',
                      maxHeight: '150px',
                      overflowY: 'auto'
                    }}>
                      {String(v)}
                    </Box>
                  </Box>
                );
              }

              return (
                <Typography key={k} variant="body2" sx={{ fontSize: '0.7rem', mb: 0.5 }}>
                  <strong>{k.replace(/_/g, ' ')}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </Typography>
              );
            })}
          </Box>
        );
      }

      // Default: show as chip count
      return <Chip label={`${entries.length} properties`} size="small" sx={{ height: 18, fontSize: '0.65rem' }} />;
    }

    // Skip showing raw data for large arrays
    if (Array.isArray(value) && value.length > 10) {
      return (
        <Chip
          label={`${value.length} items`}
          size="small"
          color="info"
          sx={{ height: 18, fontSize: '0.65rem' }}
        />
      );
    }

    // Handle null/undefined
    if (value === null || value === undefined) return <em style={{color: '#999'}}>null</em>;

    // Handle primitives
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    if (typeof value === 'number') return value.toLocaleString();
    if (typeof value === 'string') return value;

    // For small arrays, show inline
    if (Array.isArray(value) && value.length <= 10 && value.length > 0) {
      if (typeof value[0] === 'object' && value[0] !== null) {
        return (
          <Chip
            label={`${value.length} items`}
            size="small"
            color="info"
            sx={{ height: 18, fontSize: '0.65rem' }}
          />
        );
      }
      return value.join(', ');
    }

    return String(value);
  };

  const renderStepResults = (stepName: string, stepResults: any) => {
    if (!stepResults) return null;

    // Get step definition from pipeline
    const stepDef = getStepDefinition(stepName);
    const category = getStepCategory(stepName, stepDef);
    const categoryInfo = CATEGORY_MAP[category] || CATEGORY_MAP['dq'];
    const CategoryIcon = categoryInfo.icon;

    // Handle different result formats
    const status = stepResults.status || 'UNKNOWN';

    // Filter by selected categories
    if (selectedCategories.length > 0 && !selectedCategories.includes(category)) {
      return null;
    }

    const summaryMessage = getSummaryMessage(stepName, stepResults.details || {});

    return (
      <Accordion key={stepName} defaultExpanded={status === 'FAIL' || status === 'ERROR'}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={2} width="100%">
            {getStatusIcon(status)}
            <CategoryIcon sx={{ color: categoryInfo.color }} />
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                {stepName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </Typography>
              {summaryMessage && (
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', mt: 0.5 }}>
                  {summaryMessage}
                </Typography>
              )}
              {!summaryMessage && stepDef?.description && (
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', mt: 0.5 }}>
                  {stepDef.description}
                </Typography>
              )}
            </Box>
            <Chip
              label={categoryInfo.label}
              size="small"
              sx={{
                bgcolor: categoryInfo.color + '20',
                color: categoryInfo.color,
                fontWeight: 'medium',
                fontSize: '0.7rem'
              }}
            />
            <Chip
              label={status}
              color={getStatusColor(status) as any}
              size="small"
              sx={{ fontSize: '0.7rem' }}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            {/* Error/Exception */}
            {stepResults.exception && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Error:</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {stepResults.exception}
                </Typography>
              </Alert>
            )}

            {/* Message */}
            {stepResults.message && (
              <Alert severity="info" sx={{ mb: 2 }}>
                {stepResults.message}
              </Alert>
            )}

            {/* Validation Checks (from step definition) */}
            {stepDef?.checks && stepDef.checks.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Validation Checks:</Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
                  {stepDef.checks.map((check: string, idx: number) => (
                    <Chip
                      key={idx}
                      label={check.replace(/_/g, ' ')}
                      size="small"
                      variant="outlined"
                      sx={{ fontFamily: 'monospace' }}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Show summary message first if available */}
            {summaryMessage && (
              <Alert
                severity={status === 'PASS' ? 'success' : status === 'FAIL' ? 'warning' : 'info'}
                sx={{ mb: 1, py: 0, fontSize: '0.7rem' }}
              >
                {summaryMessage}
              </Alert>
            )}

            {/* Show key metrics */}
            {stepResults.details && (
              <Box sx={{ mb: 2 }}>
                {Object.entries(stepResults.details)
                  .filter(([key]) => !['mismatches', 'issues', 'duplicates', 'missing_in_sql', 'missing_in_snow', 'exception', 'error', 'outliers', 'results', 'details', 'explain', 'reason'].includes(key))
                  .map(([key, value]: any) => (
                    <Box key={key} sx={{ mb: 0.5 }}>
                      <Typography variant="caption" component="span" sx={{ fontSize: '0.65rem', fontWeight: 'bold', mr: 0.5 }}>
                        {key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}:
                      </Typography>
                      <Typography variant="caption" component="span" sx={{ fontSize: '0.65rem' }}>
                        {formatDetailValue(stepName, key, value)}
                      </Typography>
                    </Box>
                  ))}
              </Box>
            )}

            {/* Show detailed data in expandable section if exists */}
            {stepResults.details && (() => {
              const hasDetailedData = (
                (stepResults.details.mismatches?.length > 0) ||
                (stepResults.details.issues?.length > 0) ||
                (stepResults.details.outliers?.length > 0) ||
                (stepResults.details.results?.length > 0) ||
                (stepResults.details.details?.length > 0) ||
                (stepResults.details.duplicates?.length > 0) ||
                (stepResults.details.missing_in_sql?.length > 0) ||
                (stepResults.details.missing_in_snow?.length > 0) ||
                stepResults.details.reason ||
                stepResults.details.explain ||
                stepResults.details.exception
              );

              return hasDetailedData ? (
              <Box>
                {stepResults.details.exception && (
                  <Box sx={{ mb: 1 }}>
                    <Alert severity="error" sx={{ py: 0.5, fontSize: '0.65rem' }}>
                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                        Exception:
                      </Typography>
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                        {String(stepResults.details.exception)}
                      </Typography>
                    </Alert>
                  </Box>
                )}
                {stepResults.details.mismatches?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Mismatches ({stepResults.details.mismatches.length}):
                    </Typography>
                    {formatDetailValue(stepName, 'mismatches', stepResults.details.mismatches)}
                  </Box>
                )}
                {stepResults.details.issues?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Issues ({stepResults.details.issues.length}):
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'issues', stepResults.details.issues)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.duplicates?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Duplicates ({stepResults.details.duplicates.length}):
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'duplicates', stepResults.details.duplicates)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.missing_in_sql?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Missing in SQL Server ({stepResults.details.missing_in_sql.length}):
                    </Typography>
                    {formatDetailValue(stepName, 'missing_in_sql', stepResults.details.missing_in_sql)}
                  </Box>
                )}
                {stepResults.details.missing_in_snow?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Missing in Snowflake ({stepResults.details.missing_in_snow.length}):
                    </Typography>
                    {formatDetailValue(stepName, 'missing_in_snow', stepResults.details.missing_in_snow)}
                  </Box>
                )}
                {stepResults.details.outliers?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Outliers ({stepResults.details.outliers.length}):
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'outliers', stepResults.details.outliers)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.results?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Distribution Results ({stepResults.details.results.length}):
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'results', stepResults.details.results)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.details?.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Ratio Details ({stepResults.details.details.length}):
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'details', stepResults.details.details)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.reason && typeof stepResults.details.reason === 'object' && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                      Validation Details:
                    </Typography>
                    <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                      {formatDetailValue(stepName, 'reason', stepResults.details.reason)}
                    </Box>
                  </Box>
                )}
                {stepResults.details.explain && (
                  <Box sx={{ mb: 1, mt: 2, p: 1, backgroundColor: '#f0f7ff', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.7rem', display: 'block', mb: 1, color: '#1976d2' }}>
                      🔍 Explain - Root Cause Analysis
                    </Typography>
                    {Object.entries(stepResults.details.explain).map(([column, data]: [string, any]) => (
                      <Box key={column} sx={{ mb: 2, p: 1, backgroundColor: 'white', borderRadius: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 1 }}>
                          Column: {column}
                        </Typography>

                        {/* Distribution Comparison */}
                        {data.sql_distribution && data.snow_distribution && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.6rem', display: 'block', mb: 0.5, fontWeight: 'bold' }}>
                              Value Distribution:
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#666' }}>SQL Server:</Typography>
                                {Object.entries(data.sql_distribution).map(([bucket, count]: [string, any]) => (
                                  <Typography key={bucket} variant="caption" sx={{ fontSize: '0.6rem', display: 'block' }}>
                                    {bucket}: {String(count)}
                                  </Typography>
                                ))}
                              </Box>
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#666' }}>Snowflake:</Typography>
                                {Object.entries(data.snow_distribution).map(([bucket, count]: [string, any]) => (
                                  <Typography key={bucket} variant="caption" sx={{ fontSize: '0.6rem', display: 'block' }}>
                                    {bucket}: {String(count)}
                                  </Typography>
                                ))}
                              </Box>
                            </Box>
                          </Box>
                        )}

                        {/* Sample Data Comparison */}
                        {data.sql_samples && data.snow_samples && Array.isArray(data.sql_samples) && Array.isArray(data.snow_samples) && data.sql_samples.length > 0 && data.snow_samples.length > 0 && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.6rem', display: 'block', mb: 0.5, fontWeight: 'bold' }}>
                              Sample Data (First 10 rows):
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2 }}>
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#666', mb: 0.5, display: 'block' }}>SQL Server:</Typography>
                                <TableContainer component={Paper} sx={{ maxHeight: 200 }}>
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                                        {data.sql_samples[0] && Object.keys(data.sql_samples[0]).map((key: string) => (
                                          <TableCell key={key} sx={{ py: 0.3, px: 0.5, fontSize: '0.6rem', fontWeight: 'bold' }}>{key}</TableCell>
                                        ))}
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {data.sql_samples.slice(0, 10).map((row: any, idx: number) => (
                                        <TableRow key={idx}>
                                          {Object.values(row).map((val: any, i: number) => (
                                            <TableCell key={i} sx={{ py: 0.3, px: 0.5, fontSize: '0.6rem' }}>
                                              {typeof val === 'number' ? val.toLocaleString() : String(val || '')}
                                            </TableCell>
                                          ))}
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              </Box>
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#666', mb: 0.5, display: 'block' }}>Snowflake:</Typography>
                                <TableContainer component={Paper} sx={{ maxHeight: 200 }}>
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                                        {data.snow_samples[0] && Object.keys(data.snow_samples[0]).map((key: string) => (
                                          <TableCell key={key} sx={{ py: 0.3, px: 0.5, fontSize: '0.6rem', fontWeight: 'bold' }}>{key}</TableCell>
                                        ))}
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {data.snow_samples.slice(0, 10).map((row: any, idx: number) => (
                                        <TableRow key={idx}>
                                          {Object.values(row).map((val: any, i: number) => (
                                            <TableCell key={i} sx={{ py: 0.3, px: 0.5, fontSize: '0.6rem' }}>
                                              {typeof val === 'number' ? val.toLocaleString() : String(val || '')}
                                            </TableCell>
                                          ))}
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              </Box>
                            </Box>
                          </Box>
                        )}

                        {/* SQL Queries */}
                        {data.queries && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.6rem', display: 'block', mb: 0.5, fontWeight: 'bold' }}>
                              Debug Queries:
                            </Typography>
                            <Box sx={{ p: 0.5, backgroundColor: '#f5f5f5', borderRadius: 0.5, fontFamily: 'monospace', fontSize: '0.55rem', overflow: 'auto' }}>
                              {Object.entries(data.queries).map(([qType, query]: [string, any]) => (
                                <Box key={qType} sx={{ mb: 0.5 }}>
                                  <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 'bold', color: '#666' }}>{qType}:</Typography>
                                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{String(query)}</pre>
                                </Box>
                              ))}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    ))}
                  </Box>
                )}
              </Box>
            ) : null;
            })()}

            {/* Results Array */}
            {stepResults.results && Array.isArray(stepResults.results) && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Results ({stepResults.results.length}):</Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        {stepResults.results[0] && Object.keys(stepResults.results[0]).map((key) => (
                          <TableCell key={key} sx={{ fontWeight: 'bold' }}>{key}</TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {stepResults.results.slice(0, 100).map((row: any, idx: number) => (
                        <TableRow key={idx}>
                          {Object.values(row).map((val: any, valIdx: number) => (
                            <TableCell key={valIdx}>
                              {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
                {stepResults.results.length > 100 && (
                  <Alert severity="info" sx={{ mt: 1 }}>
                    Showing first 100 of {stepResults.results.length} results
                  </Alert>
                )}
              </Box>
            )}

            {/* Summary */}
            {stepResults.summary && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Summary:</Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                  <pre style={{ margin: 0, fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>
                    {typeof stepResults.summary === 'object'
                      ? JSON.stringify(stepResults.summary, null, 2)
                      : stepResults.summary}
                  </pre>
                </Paper>
              </Box>
            )}

            {/* Raw JSON fallback for other fields */}
            {!stepResults.details && !stepResults.results && !stepResults.summary && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Raw Result:</Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                  <pre style={{ margin: 0, fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(stepResults, null, 2)}
                  </pre>
                </Paper>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  };

  const calculateOverallStats = () => {
    // Handle both step_results (object) and results (array) formats
    const stepData = results?.step_results || {};
    const resultsArray = results?.results || [];

    const stats = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      errors: 0
    };

    // If we have step_results as an object
    if (Object.keys(stepData).length > 0) {
      Object.values(stepData).forEach((result: any) => {
        stats.total++;
        const status = result.status?.toUpperCase();
        if (status === 'PASS' || status === 'SUCCESS') stats.passed++;
        else if (status === 'FAIL' || status === 'FAILED') stats.failed++;
        else if (status === 'SKIPPED') stats.skipped++;
        else if (status === 'ERROR') stats.errors++;
      });
    }
    // If we have results as an array
    else if (resultsArray.length > 0) {
      resultsArray.forEach((result: any) => {
        stats.total++;
        const status = result.status?.toUpperCase();
        if (status === 'PASS' || status === 'SUCCESS') stats.passed++;
        else if (status === 'FAIL' || status === 'FAILED') stats.failed++;
        else if (status === 'SKIPPED') stats.skipped++;
        else if (status === 'ERROR') stats.errors++;
      });
    }

    return stats.total > 0 ? stats : null;
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
          <Typography variant="h6">Error Loading Results</Typography>
          <Typography>{error}</Typography>
        </Alert>
        <Button onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Box>
    );
  }

  if (!results) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No results found for run ID: {runId}</Alert>
        <Button onClick={() => navigate(-1)} sx={{ mt: 2 }}>
          Go Back
        </Button>
      </Box>
    );
  }

  const stats = calculateOverallStats();

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <AssessmentIcon sx={{ fontSize: 40, color: 'primary.main' }} />
            <Box>
              <Typography variant="h4">
                Pipeline Results
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Run ID: {runId}
              </Typography>
            </Box>
          </Box>
          <Box display="flex" gap={1}>
            <Tooltip title="Refresh Results">
              <IconButton onClick={fetchResults} color="primary">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Download Results">
              <IconButton onClick={downloadResults} color="primary">
                <DownloadIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton onClick={() => navigate(-1)}>
                <CloseIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Paper>

      {/* Overall Statistics */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Steps
                </Typography>
                <Typography variant="h4">{stats.total}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ bgcolor: 'success.light' }}>
              <CardContent>
                <Typography color="success.dark" gutterBottom>
                  Passed
                </Typography>
                <Typography variant="h4" color="success.dark">{stats.passed}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ bgcolor: 'error.light' }}>
              <CardContent>
                <Typography color="error.dark" gutterBottom>
                  Failed
                </Typography>
                <Typography variant="h4" color="error.dark">{stats.failed}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ bgcolor: 'warning.light' }}>
              <CardContent>
                <Typography color="warning.dark" gutterBottom>
                  Skipped
                </Typography>
                <Typography variant="h4" color="warning.dark">{stats.skipped}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2.4}>
            <Card sx={{ bgcolor: 'grey.300' }}>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Errors
                </Typography>
                <Typography variant="h4">{stats.errors}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Pipeline Status */}
      {results.status && (
        <Alert
          severity={getStatusColor(results.status) as any}
          sx={{ mb: 3 }}
          icon={getStatusIcon(results.status)}
        >
          <Typography variant="h6">
            Pipeline Status: {results.status}
          </Typography>
          {results.message && <Typography>{results.message}</Typography>}
        </Alert>
      )}

      {/* Category Filter */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Filter by Category
        </Typography>
        <ToggleButtonGroup
          value={selectedCategories}
          onChange={handleCategoryFilter}
          aria-label="category filter"
          sx={{ flexWrap: 'wrap', gap: 1 }}
        >
          {Object.entries(CATEGORY_MAP).map(([key, info]) => {
            const Icon = info.icon;
            return (
              <ToggleButton
                key={key}
                value={key}
                aria-label={info.label}
                sx={{
                  border: `2px solid ${info.color}`,
                  '&.Mui-selected': {
                    bgcolor: info.color + '30',
                    borderColor: info.color,
                    '&:hover': {
                      bgcolor: info.color + '40',
                    }
                  }
                }}
              >
                <Icon sx={{ mr: 1, color: info.color }} />
                {info.label}
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>
        {selectedCategories.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Showing {selectedCategories.length} of {Object.keys(CATEGORY_MAP).length} categories
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Step Results */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h5" gutterBottom>
          Step Results
        </Typography>
        <Divider sx={{ mb: 2 }} />
        {(() => {
          // Handle step_results as an object (key-value pairs)
          if (results.step_results && Object.keys(results.step_results).length > 0) {
            return (
              <Box>
                {Object.entries(results.step_results).map(([stepName, stepResults]) =>
                  renderStepResults(stepName, stepResults)
                )}
              </Box>
            );
          }
          // Handle results as an array
          else if (results.results && Array.isArray(results.results) && results.results.length > 0) {
            return (
              <Box>
                {results.results.map((result: any, idx: number) =>
                  renderStepResults(result.name || `Step ${idx + 1}`, result)
                )}
              </Box>
            );
          }
          // No results found
          else {
            return <Alert severity="info">No step results available</Alert>;
          }
        })()}
      </Paper>

      {/* Execution Info */}
      {(results.start_time || results.end_time || results.duration) && (
        <Paper sx={{ p: 2, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Execution Information
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            {results.start_time && (
              <Grid item xs={12} sm={4}>
                <Typography variant="body2" color="text.secondary">Start Time</Typography>
                <Typography variant="body1">{new Date(results.start_time).toLocaleString()}</Typography>
              </Grid>
            )}
            {results.end_time && (
              <Grid item xs={12} sm={4}>
                <Typography variant="body2" color="text.secondary">End Time</Typography>
                <Typography variant="body1">{new Date(results.end_time).toLocaleString()}</Typography>
              </Grid>
            )}
            {results.duration && (
              <Grid item xs={12} sm={4}>
                <Typography variant="body2" color="text.secondary">Duration</Typography>
                <Typography variant="body1">{results.duration}s</Typography>
              </Grid>
            )}
          </Grid>
        </Paper>
      )}
    </Box>
  );
}
