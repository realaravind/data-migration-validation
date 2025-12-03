import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  ToggleButtonGroup,
  ToggleButton,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  ArrowBack,
  Search,
  Download,
  FilterList,
  CompareArrows,
} from '@mui/icons-material';

interface ComparisonRow {
  row_index: number;
  sql_values: Record<string, string>;
  snowflake_values: Record<string, string>;
  differing_columns: string[];
  only_in?: 'sql' | 'snowflake' | null;
}

interface ComparisonData {
  run_id: string;
  step_name: string;
  status: string;
  difference_type: string;
  summary: {
    total_rows: number;
    differing_rows: number;
    affected_columns: string[];
    message: string;
    sql_row_count?: number;
    snowflake_row_count?: number;
    rows_only_in_sql?: number;
    rows_only_in_snowflake?: number;
  };
  comparison: {
    columns: string[];
    rows: ComparisonRow[];
    shape_mismatch?: boolean;
    sql_row_count?: number;
    snowflake_row_count?: number;
  };
}

const ComparisonViewer: React.FC = () => {
  const { runId, stepName } = useParams<{ runId: string; stepName: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'different'>('all');

  useEffect(() => {
    fetchComparisonData();
  }, [runId, stepName]);

  const fetchComparisonData = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/execution/results/${runId}/step/${stepName}/comparison`
      );
      const result = await response.json();

      if (result.error) {
        setError(result.error);
      } else {
        console.log('[ComparisonViewer] Received data:', result);
        console.log('[ComparisonViewer] Comparison rows:', result.comparison?.rows);
        console.log('[ComparisonViewer] Row count:', result.comparison?.rows?.length);
        setData(result);
        // Auto-select 'different' filter mode if there are differing rows
        // Otherwise default to 'all' to show matching rows
        if (result.summary.differing_rows > 0) {
          setFilterMode('different');
        } else {
          setFilterMode('all');
        }
      }
    } catch (err) {
      setError(`Failed to load comparison data: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const filterRows = () => {
    if (!data) {
      console.log('[filterRows] No data');
      return [];
    }

    if (!data.comparison || !data.comparison.rows) {
      console.log('[filterRows] No comparison.rows', data);
      return [];
    }

    let filtered = data.comparison.rows;
    console.log('[filterRows] Initial rows:', filtered.length);
    console.log('[filterRows] Filter mode:', filterMode);

    // Filter by mode
    if (filterMode === 'different') {
      filtered = filtered.filter((row) => row.differing_columns.length > 0);
      console.log('[filterRows] After different filter:', filtered.length);
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter((row) => {
        const searchLower = searchTerm.toLowerCase();
        return Object.values(row.sql_values).some((val) =>
          val?.toLowerCase().includes(searchLower)
        ) || Object.values(row.snowflake_values).some((val) =>
          val?.toLowerCase().includes(searchLower)
        );
      });
      console.log('[filterRows] After search filter:', filtered.length);
    }

    console.log('[filterRows] Final filtered rows:', filtered.length);
    return filtered;
  };

  const exportToCSV = () => {
    if (!data) return;

    const headers = ['Row', ...data.comparison.columns.flatMap(col => [`${col} (SQL)`, `${col} (Snowflake)`])];
    const rows = filterRows().map(row => [
      row.row_index,
      ...data.comparison.columns.flatMap(col => [
        row.sql_values[col] || '',
        row.snowflake_values[col] || ''
      ])
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison_${runId}_${stepName}.csv`;
    a.click();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box p={3}>
        <Alert severity="error">{error || 'No data available'}</Alert>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate(-1)}
          sx={{ mt: 2 }}
        >
          Back to Results
        </Button>
      </Box>
    );
  }

  const filteredRows = filterRows();

  return (
    <Box p={3}>
      {/* Header */}
      <Stack direction="row" spacing={2} alignItems="center" mb={3}>
        <IconButton onClick={() => navigate(-1)}>
          <ArrowBack />
        </IconButton>
        <Typography variant="h4">Data Comparison Viewer</Typography>
      </Stack>

      {/* Summary Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="h6">Summary</Typography>
              <Chip
                label={data.status}
                color={data.status === 'PASS' ? 'success' : 'error'}
                size="small"
              />
              <Chip
                label={data.difference_type.replace('_', ' ').toUpperCase()}
                variant="outlined"
                size="small"
              />
            </Stack>

            <Typography variant="body2" color="text.secondary">
              <strong>Step:</strong> {data.step_name}
            </Typography>

            {data.comparison.shape_mismatch ? (
              <>
                <Typography variant="body2" color="text.secondary">
                  <strong>SQL Server Rows:</strong> {data.summary.sql_row_count || 0} |{' '}
                  <strong>Snowflake Rows:</strong> {data.summary.snowflake_row_count || 0}
                </Typography>
                {(data.summary.rows_only_in_sql || 0) > 0 && (
                  <Typography variant="body2" color="error.main">
                    <strong>Rows only in SQL Server:</strong> {data.summary.rows_only_in_sql}
                  </Typography>
                )}
                {(data.summary.rows_only_in_snowflake || 0) > 0 && (
                  <Typography variant="body2" color="error.main">
                    <strong>Rows only in Snowflake:</strong> {data.summary.rows_only_in_snowflake}
                  </Typography>
                )}
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">
                <strong>Total Rows:</strong> {data.summary.total_rows} |{' '}
                <strong>Differing Rows:</strong> {data.summary.differing_rows}
              </Typography>
            )}

            <Typography variant="body2" color="text.secondary">
              <strong>Affected Columns:</strong> {data.summary.affected_columns.join(', ')}
            </Typography>

            <Alert severity="info" sx={{ mt: 1 }}>
              {data.summary.message.split('\n')[0]}
            </Alert>
          </Stack>
        </CardContent>
      </Card>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <TextField
            placeholder="Search values..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            size="small"
            sx={{ minWidth: 300 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />

          <ToggleButtonGroup
            value={filterMode}
            exclusive
            onChange={(_, newMode) => newMode && setFilterMode(newMode)}
            size="small"
          >
            <ToggleButton value="all">
              All Rows ({data.comparison.rows.length})
            </ToggleButton>
            <ToggleButton value="different">
              Different Only ({data.summary.differing_rows})
            </ToggleButton>
          </ToggleButtonGroup>

          <Box flex={1} />

          <Button
            startIcon={<Download />}
            onClick={exportToCSV}
            variant="outlined"
            size="small"
          >
            Export CSV
          </Button>
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Showing {filteredRows.length} rows
        </Typography>
      </Paper>

      {/* Comparison Table */}
      <TableContainer component={Paper} sx={{ maxHeight: '70vh' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: 'bold',
                  backgroundColor: 'primary.light',
                  color: 'white',
                  position: 'sticky',
                  left: 0,
                  zIndex: 3,
                }}
              >
                Row #
              </TableCell>
              {data.comparison.columns.map((col) => (
                <React.Fragment key={col}>
                  <TableCell
                    sx={{
                      fontWeight: 'bold',
                      backgroundColor: '#1976d2',
                      color: 'white',
                      borderRight: '1px solid rgba(224, 224, 224, 1)',
                    }}
                  >
                    {col}
                    <br />
                    <Typography variant="caption" sx={{ opacity: 0.8 }}>
                      SQL Server
                    </Typography>
                  </TableCell>
                  <TableCell
                    sx={{
                      fontWeight: 'bold',
                      backgroundColor: '#0288d1',
                      color: 'white',
                      borderRight: '2px solid rgba(224, 224, 224, 1)',
                    }}
                  >
                    {col}
                    <br />
                    <Typography variant="caption" sx={{ opacity: 0.8 }}>
                      Snowflake
                    </Typography>
                  </TableCell>
                </React.Fragment>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredRows.map((row) => {
              const isOnlyInSql = row.only_in === 'sql';
              const isOnlyInSnowflake = row.only_in === 'snowflake';
              const rowBgColor = isOnlyInSql ? 'warning.light' : isOnlyInSnowflake ? 'info.light' : undefined;

              return (
                <TableRow
                  key={row.row_index}
                  sx={{
                    '&:nth-of-type(odd)': { backgroundColor: rowBgColor || 'action.hover' },
                    backgroundColor: rowBgColor,
                  }}
                >
                  <TableCell
                    sx={{
                      fontWeight: 'bold',
                      position: 'sticky',
                      left: 0,
                      backgroundColor: rowBgColor || 'background.paper',
                      zIndex: 1,
                    }}
                  >
                    {row.row_index}
                    {isOnlyInSql && (
                      <Chip
                        label="SQL Only"
                        size="small"
                        color="warning"
                        sx={{ ml: 1, height: 20, fontSize: '0.65rem' }}
                      />
                    )}
                    {isOnlyInSnowflake && (
                      <Chip
                        label="Snowflake Only"
                        size="small"
                        color="info"
                        sx={{ ml: 1, height: 20, fontSize: '0.65rem' }}
                      />
                    )}
                  </TableCell>
                  {data.comparison.columns.map((col) => {
                    const isDifferent = row.differing_columns.includes(col);
                    const sqlValue = row.sql_values[col] || '';
                    const snowValue = row.snowflake_values[col] || '';
                    const isMissing = sqlValue === 'None' || snowValue === 'None';

                    return (
                      <React.Fragment key={col}>
                        <TableCell
                          sx={{
                            backgroundColor: isOnlyInSql
                              ? 'warning.light'
                              : isDifferent
                              ? 'error.light'
                              : 'inherit',
                            color: isOnlyInSql
                              ? 'warning.dark'
                              : isDifferent
                              ? 'error.contrastText'
                              : 'inherit',
                            fontWeight: isDifferent ? 'bold' : 'normal',
                            fontStyle: isMissing ? 'italic' : 'normal',
                            borderRight: '1px solid rgba(224, 224, 224, 1)',
                          }}
                        >
                          {sqlValue === 'None' && isOnlyInSnowflake ? '—' : sqlValue}
                        </TableCell>
                        <TableCell
                          sx={{
                            backgroundColor: isOnlyInSnowflake
                              ? 'info.light'
                              : isDifferent
                              ? 'error.light'
                              : 'inherit',
                            color: isOnlyInSnowflake
                              ? 'info.dark'
                              : isDifferent
                              ? 'error.contrastText'
                              : 'inherit',
                            fontWeight: isDifferent ? 'bold' : 'normal',
                            fontStyle: isMissing ? 'italic' : 'normal',
                            borderRight: '2px solid rgba(224, 224, 224, 1)',
                          }}
                        >
                          {snowValue === 'None' && isOnlyInSql ? '—' : snowValue}
                        </TableCell>
                      </React.Fragment>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {filteredRows.length === 0 && (
        <Box textAlign="center" py={4}>
          <Typography variant="body1" color="text.secondary">
            No rows match your current filters
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ComparisonViewer;
