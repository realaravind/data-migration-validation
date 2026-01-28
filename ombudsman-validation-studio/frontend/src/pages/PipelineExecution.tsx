import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as yaml from 'js-yaml';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItemText,
  ListItemButton,
  Divider,
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
  LinearProgress
} from "@mui/material";
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import QuerySuggestions from '../components/QuerySuggestions';

export default function PipelineExecution({ currentProject }: any) {
  const navigate = useNavigate();
  const [savedPipelines, setSavedPipelines] = useState<any[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<any>(null);
  const [pipelineRuns, setPipelineRuns] = useState<any[]>([]);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [showQuerySuggestions, setShowQuerySuggestions] = useState(false);

  useEffect(() => {
    // Load pipelines on mount and when project changes
    loadSavedPipelines();
  }, [currentProject]);

  useEffect(() => {
    // Auto-refresh runs every 3 seconds
    const interval = setInterval(() => {
      if (currentProject?.project_id) {
        loadAllRuns();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [currentProject]);

  const loadSavedPipelines = async () => {
    // Try to get project from prop, sessionStorage, or fallback to 'default_project'
    let projectId = currentProject?.project_id;

    if (!projectId) {
      const sessionProject = sessionStorage.getItem('currentProject');
      if (sessionProject) {
        try {
          const project = JSON.parse(sessionProject);
          projectId = project.project_id;
        } catch (e) {
          console.error('Failed to parse session project:', e);
        }
      }
    }

    projectId = projectId || 'default_project';
    console.log('[PipelineExecution] Loading pipelines for project:', projectId);

    try {
      // Get auth token
      const token = localStorage.getItem('auth_token');
      const headers: any = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const url = `${__API_URL__}/pipelines/custom/project/${projectId}`;
      console.log('[PipelineExecution] Fetching from:', url);
      const response = await fetch(url, { headers });
      const data = await response.json();
      console.log('[PipelineExecution] Response:', data);

      if (response.ok) {
        console.log('[PipelineExecution] Setting pipelines:', data.pipelines?.length || 0);
        setSavedPipelines(data.pipelines || []);
      } else {
        console.error('[PipelineExecution] Response not ok:', response.status, data);
      }
    } catch (err) {
      console.error('[PipelineExecution] Failed to load saved pipelines:', err);
    }
  };

  const loadAllRuns = async () => {
    try {
      const response = await fetch(__API_URL__ + "/pipelines/list");
      const data = await response.json();

      // Fetch full details for each run
      const runsWithDetails = await Promise.all(
        (data.pipelines || []).map(async (run: any) => {
          try {
            const detailsResponse = await fetch(`${__API_URL__}/pipelines/status/${run.run_id}`);
            const details = await detailsResponse.json();
            return details;
          } catch {
            return run;
          }
        })
      );

      setPipelineRuns(runsWithDetails);
    } catch (error) {
      console.error("Failed to load pipeline runs:", error);
    }
  };

  const loadPipelineContent = async (pipelineName: string) => {
    if (!currentProject?.project_id) return null;

    try {
      const response = await fetch(
        `${__API_URL__}/pipelines/custom/project/${currentProject.project_id}/${pipelineName}`
      );
      const data = await response.json();

      if (response.ok) {
        return data.content;
      }
    } catch (err) {
      console.error('Failed to load pipeline content:', err);
    }
    return null;
  };

  const handleSelectPipeline = async (pipeline: any) => {
    setSelectedPipeline(pipeline);
    setError(null);
    setSuccess(null);
  };

  const handleExecutePipeline = async () => {
    if (!selectedPipeline) {
      setError('Please select a pipeline first');
      return;
    }

    setExecuting(true);
    setError(null);
    setSuccess(null);

    try {
      // Load pipeline content
      const yamlContent = await loadPipelineContent(selectedPipeline.pipeline_name);

      if (!yamlContent) {
        setError('Failed to load pipeline content');
        setExecuting(false);
        return;
      }

      // Inject project's connection configuration into the YAML
      let enrichedYaml = yamlContent;
      console.log('[PIPELINE EXEC] Starting config injection');
      console.log('[PIPELINE EXEC] currentProject:', currentProject);
      console.log('[PIPELINE EXEC] currentProject.config:', currentProject?.config);
      console.log('[PIPELINE EXEC] currentProject.config.snowflake:', currentProject?.config?.snowflake);

      if (currentProject?.config?.snowflake) {
        console.log('[PIPELINE EXEC] Snowflake config exists, parsing YAML');
        // Parse YAML to check if connections already present
        const yamlParsed = yaml.load(yamlContent) as any;
        console.log('[PIPELINE EXEC] Parsed YAML:', yamlParsed);
        console.log('[PIPELINE EXEC] Has connections?', !!yamlParsed.connections);
        console.log('[PIPELINE EXEC] Has snowflake?', !!yamlParsed.snowflake);

        if (!yamlParsed.connections && !yamlParsed.snowflake) {
          console.log('[PIPELINE EXEC] Injecting snowflake config:', currentProject.config.snowflake);

          // IMPORTANT: Don't use yaml.dump() as it may strip custom_queries!
          // Instead, append snowflake config as YAML string to preserve original content
          const snowflakeYaml = yaml.dump({ snowflake: currentProject.config.snowflake });
          enrichedYaml = yamlContent + '\n' + snowflakeYaml;

          console.log('[PIPELINE EXEC] Enriched YAML (appended snowflake):', enrichedYaml);
        } else {
          console.log('[PIPELINE EXEC] YAML already has connections/snowflake, skipping injection');
        }
      } else {
        console.log('[PIPELINE EXEC] No snowflake config in currentProject, using original YAML');
      }

      // Execute pipeline
      // Get auth token
      const token = localStorage.getItem('auth_token');
      const headers: any = { "Content-Type": "application/json" };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const requestBody = {
        pipeline_yaml: enrichedYaml,
        pipeline_name: selectedPipeline.pipeline_name,
        project_id: currentProject?.project_id || null
      };
      console.log('[PIPELINE EXEC] Sending request to backend:', requestBody);
      console.log('[PIPELINE EXEC] YAML being sent:', enrichedYaml);

      const response = await fetch(__API_URL__ + "/pipelines/execute", {
        method: "POST",
        headers,
        body: JSON.stringify(requestBody)
      });

      const result = await response.json();

      if (response.ok) {
        setSuccess(`Pipeline started successfully! Run ID: ${result.run_id}. Watch execution history below for status updates.`);
        // Reload runs list
        await loadAllRuns();
        // Auto-expand the new run
        setExpandedRun(result.run_id);
      } else {
        setError(result.detail || 'Failed to start pipeline');
      }
    } catch (err) {
      setError(`Error executing pipeline: ${err}`);
    } finally {
      setExecuting(false);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear all pipeline execution history? This cannot be undone.')) {
      return;
    }

    try {
      // Get auth token
      const token = localStorage.getItem('auth_token');
      const headers: any = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Delete all runs
      const deletePromises = pipelineRuns.map(run =>
        fetch(`${__API_URL__}/pipelines/${run.run_id}`, {
          method: 'DELETE',
          headers
        })
      );

      await Promise.all(deletePromises);

      // Clear local state
      setPipelineRuns([]);
      setSuccess('Pipeline execution history cleared successfully');

      // Reload runs
      await loadAllRuns();
    } catch (error) {
      setError(`Failed to clear history: ${error}`);
    }
  };

  const handleQuerySuggestionsSelect = async (queries: any[]) => {
    if (!selectedPipeline) {
      setError('Please select a pipeline first to add queries to');
      return;
    }

    try {
      // Load current pipeline content
      const yamlContent = await loadPipelineContent(selectedPipeline.pipeline_name);

      if (!yamlContent) {
        setError('Failed to load pipeline content');
        return;
      }

      // Parse YAML and add custom queries
      // Note: This is a simplified approach - in production you'd want proper YAML parsing
      let updatedYaml = yamlContent;

      // Add custom_queries section if not present
      if (!yamlContent.includes('custom_queries:')) {
        updatedYaml += '\n\ncustom_queries:\n';
      }

      // Add each selected query
      queries.forEach(query => {
        updatedYaml += `  - name: "${query.name}"\n`;
        updatedYaml += `    comparison_type: "${query.comparison_type}"\n`;
        updatedYaml += `    sql_query: |\n`;
        updatedYaml += `      ${query.sql_query.replace(/\n/g, '\n      ')}\n`;
        updatedYaml += `    snow_query: |\n`;
        updatedYaml += `      ${query.snow_query.replace(/\n/g, '\n      ')}\n`;
        if (query.tolerance) {
          updatedYaml += `    tolerance: ${query.tolerance}\n`;
        }
        if (query.limit) {
          updatedYaml += `    limit: ${query.limit}\n`;
        }
        updatedYaml += '\n';
      });

      // Save updated pipeline
      const token = localStorage.getItem('auth_token');
      const headers: any = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const saveResponse = await fetch(
        `${__API_URL__}/pipelines/custom/save`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            project_id: currentProject.project_id,
            pipeline_name: selectedPipeline.pipeline_name,
            pipeline_yaml: updatedYaml,
            description: selectedPipeline.description || '',
            tags: []
          })
        }
      );

      if (saveResponse.ok) {
        setSuccess(`Added ${queries.length} intelligent queries to ${selectedPipeline.pipeline_name}!`);
        await loadSavedPipelines();
      } else {
        const errorData = await saveResponse.json();
        setError(errorData.detail || 'Failed to update pipeline');
      }
    } catch (err) {
      setError(`Error adding queries: ${err}`);
    }
  };

  const getStatusColor = (status: string) => {
    if (status === "completed") return "success";
    if (status === "failed") return "error";
    if (status === "running") return "warning";
    return "default";
  };

  const getStatusIcon = (status: string) => {
    if (status === "PASS") return <CheckCircleIcon fontSize="small" color="success" />;
    if (status === "FAIL") return <ErrorIcon fontSize="small" color="error" />;
    if (status === "SKIPPED") return <InfoIcon fontSize="small" color="disabled" />;
    if (status === "ERROR") return <WarningIcon fontSize="small" color="warning" />;
    return <InfoIcon fontSize="small" />;
  };

  const getSeverityColor = (severity: string) => {
    if (severity === "HIGH") return "error";
    if (severity === "MEDIUM") return "warning";
    if (severity === "LOW") return "info";
    return "default";
  };

  const getSummaryMessage = (_validatorName: string, details: any): string | null => {
    // Handle errors/exceptions specially
    if (details.exception) {
      // Clean up Python error messages
      let error = String(details.exception);

      // Handle datetime representation errors
      if (error.includes('datetime.date(')) {
        return 'Date formatting error - validator needs to convert dates to strings';
      }

      // Handle other common errors
      if (error.includes('division by zero')) {
        return 'Division by zero error - check for null or zero values in data';
      }

      if (error.includes('KeyError') || error.includes('not found')) {
        return `Missing required data: ${error.replace('KeyError:', '').trim()}`;
      }

      // Return cleaned error
      return `Error: ${error.substring(0, 100)}${error.length > 100 ? '...' : ''}`;
    }

    // Generate human-readable summary based on validator type and results

    if (_validatorName === 'validate_record_counts') {
      const diff = Math.abs((details.sql_count || 0) - (details.snow_count || 0));
      return `Row count mismatch: SQL has ${details.sql_count?.toLocaleString()} rows, Snowflake has ${details.snow_count?.toLocaleString()} rows (difference: ${diff.toLocaleString()})`;
    }

    if (_validatorName === 'validate_schema_columns') {
      const missing = details.mismatch_count || (details.missing_in_sql?.length || 0) + (details.missing_in_snow?.length || 0);
      if (missing > 0) {
        const parts = [];
        if (details.missing_in_snow?.length > 0) parts.push(`${details.missing_in_snow.length} columns missing in Snowflake`);
        if (details.missing_in_sql?.length > 0) parts.push(`${details.missing_in_sql.length} columns missing in SQL Server`);
        return parts.join(', ');
      }
      return 'All columns match between systems';
    }

    if (_validatorName === 'validate_schema_datatypes') {
      const count = details.mismatch_count || details.mismatches?.length || 0;
      if (count > 0) {
        return `${count} column${count > 1 ? 's have' : ' has'} different data types between SQL Server and Snowflake`;
      }
      return 'All data types match';
    }

    if (_validatorName === 'validate_schema_nullability') {
      const count = details.mismatch_count || details.mismatches?.length || 0;
      if (count > 0) {
        return `${count} column${count > 1 ? 's have' : ' has'} different nullability constraints`;
      }
      return 'All nullability constraints match';
    }

    if (_validatorName === 'validate_metric_sums') {
      const count = details.issues?.length || 0;
      if (count > 0) {
        return `${count} metric column${count > 1 ? 's have' : ' has'} different sum values between systems`;
      }
      return 'All metric sums match';
    }

    if (_validatorName === 'validate_ts_duplicates') {
      const count = details.duplicate_count || details.duplicates?.length || 0;
      if (count > 0) {
        return `Found ${count} duplicate timestamp${count > 1 ? 's' : ''}`;
      }
      return 'No duplicate timestamps';
    }

    if (_validatorName === 'validate_ts_continuity') {
      const missing = details.missing_count || 0;
      if (missing > 0) {
        return `${missing} date${missing > 1 ? 's are' : ' is'} missing in the time series (${details.min_date} to ${details.max_date})`;
      }
      return 'Complete time series with no gaps';
    }

    if (_validatorName === 'validate_ts_rolling_drift') {
      const count = details.issues?.length || 0;
      if (count > 0) {
        return `Found ${count} rolling window drift issue${count > 1 ? 's' : ''} across 7-day and 30-day windows`;
      }
      return 'No rolling window drift detected';
    }

    if (_validatorName === 'validate_period_over_period') {
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
    // Handle these FIRST before checking for large arrays
    if ((key === 'mismatches' || key === 'issues' || key === 'duplicates' || key === 'results' || key === 'details' || key === 'outliers') && Array.isArray(value) && value.length > 0) {
      // Check if array contains objects
      if (typeof value[0] === 'object' && value[0] !== null && !Array.isArray(value[0])) {
        const headers = Object.keys(value[0]);
        const showCount = 20; // Show more items

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

      // Handle arrays of arrays (like duplicates from validate_ts_duplicates)
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

    // Skip showing raw data for large arrays (after checking for special formatting above)
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

    // For small arrays, show inline (but not if they contain objects)
    if (Array.isArray(value) && value.length <= 10 && value.length > 0) {
      // Check if array contains objects - if so, don't show inline
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

    // For objects, show count
    if (typeof value === 'object') {
      const count = Object.keys(value).length;
      return <Chip label={`${count} properties`} size="small" sx={{ height: 18, fontSize: '0.65rem' }} />;
    }

    return String(value);
  };

  const getRunSummary = (run: any) => {
    if (!run.results || run.results.length === 0) {
      return { total: 0, pass: 0, fail: 0, error: 0, skipped: 0 };
    }

    return {
      total: run.results.length,
      pass: run.results.filter((r: any) => r.status === 'PASS').length,
      fail: run.results.filter((r: any) => r.status === 'FAIL').length,
      error: run.results.filter((r: any) => r.status === 'ERROR').length,
      skipped: run.results.filter((r: any) => r.status === 'SKIPPED').length,
    };
  };

  const getRunsForSelectedPipeline = () => {
    if (!selectedPipeline) return pipelineRuns;

    return pipelineRuns.filter(
      (run: any) => run.pipeline_name === selectedPipeline.pipeline_name ||
                    run.pipeline_name === selectedPipeline.pipeline_name.replace(/\s+/g, '_')
    ).sort((a: any, b: any) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Pipeline Execution</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            startIcon={<AutoAwesomeIcon />}
            onClick={() => setShowQuerySuggestions(true)}
            size="small"
            disabled={!selectedPipeline}
            sx={{
              background: 'linear-gradient(45deg, #9c27b0 30%, #673ab7 90%)',
              '&:hover': {
                background: 'linear-gradient(45deg, #7b1fa2 30%, #512da8 90%)',
              }
            }}
          >
            Suggest Custom Queries
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => { loadSavedPipelines(); loadAllRuns(); }}
            size="small"
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteSweepIcon />}
            onClick={clearHistory}
            size="small"
            disabled={pipelineRuns.length === 0}
          >
            Clear History
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 1.5 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Grid container spacing={2}>
        {/* Left Side - Saved Pipelines */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <FolderIcon fontSize="small" /> Saved Pipelines
                </Typography>
                <IconButton
                  size="small"
                  onClick={loadSavedPipelines}
                  title="Refresh pipelines"
                  sx={{ p: 0.5 }}
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </Box>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                {savedPipelines.length} pipeline{savedPipelines.length !== 1 ? 's' : ''}
              </Typography>

              <Divider sx={{ my: 1 }} />

              {savedPipelines.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  No saved pipelines.
                </Typography>
              ) : (
                <List dense sx={{ p: 0 }}>
                  {savedPipelines.map((pipeline) => (
                    <ListItemButton
                      key={pipeline.pipeline_name}
                      selected={selectedPipeline?.pipeline_name === pipeline.pipeline_name}
                      onClick={() => handleSelectPipeline(pipeline)}
                      sx={{
                        borderRadius: 1,
                        mb: 0.25,
                        py: 0.5,
                        px: 1,
                        '&.Mui-selected': {
                          bgcolor: 'primary.light',
                          '&:hover': {
                            bgcolor: 'primary.light',
                          }
                        }
                      }}
                    >
                      <DescriptionIcon fontSize="small" sx={{ mr: 0.75, color: 'primary.main', fontSize: 16 }} />
                      <ListItemText
                        primary={pipeline.pipeline_name}
                        secondary={pipeline.description || 'No description'}
                        primaryTypographyProps={{ variant: 'caption', fontWeight: 500 }}
                        secondaryTypographyProps={{ variant: 'caption', fontSize: '0.7rem' }}
                      />
                    </ListItemButton>
                  ))}
                </List>
              )}

              {selectedPipeline && (
                <Box sx={{ mt: 1.5 }}>
                  <Button
                    variant="contained"
                    fullWidth
                    size="small"
                    startIcon={executing ? <CircularProgress size={14} /> : <PlayArrowIcon />}
                    onClick={handleExecutePipeline}
                    disabled={executing}
                  >
                    {executing ? 'Executing...' : 'Execute Pipeline'}
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right Side - Execution History with Details */}
        <Grid item xs={12} md={9}>
          <Card>
            <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography variant="subtitle2" gutterBottom sx={{ mb: 1 }}>
                {selectedPipeline ? `Execution History: ${selectedPipeline.pipeline_name}` : 'All Executions'}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
                {getRunsForSelectedPipeline().length} execution{getRunsForSelectedPipeline().length !== 1 ? 's' : ''}
              </Typography>

              <Divider sx={{ mb: 1.5 }} />

              {getRunsForSelectedPipeline().length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="caption" color="text.secondary">
                    {selectedPipeline ? 'No executions yet for this pipeline.' : 'No executions yet.'}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ maxHeight: 600, overflow: 'auto' }}>
                  {getRunsForSelectedPipeline().map((run) => (
                    <Accordion
                      key={run.run_id}
                      expanded={expandedRun === run.run_id}
                      onChange={() => setExpandedRun(expandedRun === run.run_id ? null : run.run_id)}
                      sx={{ mb: 1, '&:before': { display: 'none' } }}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 36, py: 0.5, '& .MuiAccordionSummary-content': { my: 0 } }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', overflow: 'hidden' }}>
                          <Chip label={run.status} color={getStatusColor(run.status)} size="small" sx={{ height: 18, fontSize: '0.6rem', minWidth: 65, fontWeight: 'bold', flexShrink: 0 }} />
                          <Typography variant="caption" noWrap sx={{ fontSize: '0.7rem', fontWeight: 600, flexShrink: 0, maxWidth: 200 }}>{run.pipeline_name}</Typography>
                          {(() => {
                            const summary = getRunSummary(run);
                            return summary.total > 0 ? (
                              <Typography variant="caption" noWrap sx={{ fontSize: '0.6rem', color: 'text.secondary', flexShrink: 0 }}>
                                ({summary.total}:{' '}
                                {summary.pass > 0 && <Box component="span" sx={{ color: 'success.main', fontWeight: 600 }}>✓{summary.pass}</Box>}
                                {summary.pass > 0 && (summary.fail > 0 || summary.error > 0) && ' '}
                                {summary.fail > 0 && <Box component="span" sx={{ color: 'warning.main', fontWeight: 600 }}>✗{summary.fail}</Box>}
                                {summary.fail > 0 && summary.error > 0 && ' '}
                                {summary.error > 0 && <Box component="span" sx={{ color: 'error.main', fontWeight: 600 }}>⚠{summary.error}</Box>}
                                )
                              </Typography>
                            ) : null;
                          })()}
                          <Typography variant="caption" color="text.secondary" noWrap sx={{ fontSize: '0.6rem', ml: 'auto', flexShrink: 0 }}>{new Date(run.started_at).toLocaleString()}</Typography>
                          <Tooltip title="Open in Full Window">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/results/${run.run_id}`);
                              }}
                              sx={{ ml: 1, flexShrink: 0 }}
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails sx={{ pt: 0, pb: 1 }}>
                        {run.error && (
                          <Alert severity="error" sx={{ mb: 1, py: 0.5 }}>
                            <Typography variant="caption" fontWeight="bold">Error:</Typography>
                            <Typography variant="caption" display="block">{run.error}</Typography>
                          </Alert>
                        )}

                        {run.results && run.results.length > 0 ? (
                          <Box>
                            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                              <Table size="small" stickyHeader>
                                <TableHead>
                                  <TableRow>
                                    <TableCell sx={{ py: 0.75, fontSize: '0.7rem', fontWeight: 600 }}>Step</TableCell>
                                    <TableCell sx={{ py: 0.75, fontSize: '0.7rem', fontWeight: 600 }}>Status</TableCell>
                                    <TableCell sx={{ py: 0.75, fontSize: '0.7rem', fontWeight: 600 }}>Severity</TableCell>
                                    <TableCell sx={{ py: 0.75, fontSize: '0.7rem', fontWeight: 600 }}>Details</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {run.results.map((result: any, idx: number) => (
                                    <TableRow key={idx} hover>
                                      <TableCell sx={{ py: 0.75, fontSize: '0.7rem' }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                          {getStatusIcon(result.status)}
                                          <Typography variant="caption" fontWeight={500}>
                                            {result.name}
                                          </Typography>
                                        </Box>
                                      </TableCell>
                                      <TableCell sx={{ py: 0.75, fontSize: '0.7rem' }}>
                                        <Chip
                                          label={result.status}
                                          size="small"
                                          color={result.status === "PASS" ? "success" : result.status === "FAIL" ? "error" : "default"}
                                          sx={{ height: 18, fontSize: '0.65rem' }}
                                        />
                                      </TableCell>
                                      <TableCell sx={{ py: 0.75, fontSize: '0.7rem' }}>
                                        {result.severity && result.severity !== "NONE" && (
                                          <Chip
                                            label={result.severity}
                                            size="small"
                                            color={getSeverityColor(result.severity)}
                                            sx={{ height: 18, fontSize: '0.65rem' }}
                                          />
                                        )}
                                      </TableCell>
                                      <TableCell sx={{ py: 0.75, fontSize: '0.7rem' }}>
                                        {result.details && Object.keys(result.details).length > 0 ? (
                                          <Box sx={{ maxWidth: 600 }}>
                                            {/* Show summary message first if available */}
                                            {getSummaryMessage(result.name, result.details) && (
                                              <Alert
                                                severity={result.status === 'PASS' ? 'success' : result.status === 'FAIL' ? 'warning' : 'info'}
                                                sx={{ mb: 1, py: 0, fontSize: '0.7rem' }}
                                              >
                                                {getSummaryMessage(result.name, result.details)}
                                              </Alert>
                                            )}

                                            {/* View Comparison Button - Show for all comparative validations */}
                                            {(result.details?.comparison_details || result.comparison_details ||
                                              (result.details?.sql_row_count !== undefined && result.details?.snow_row_count !== undefined) ||
                                              result.name?.toLowerCase().includes('comparative') ||
                                              result.name?.toLowerCase().includes('custom_sql') ||
                                              result.name?.toLowerCase().startsWith('query_')) && (
                                              <Button
                                                size="small"
                                                variant="outlined"
                                                startIcon={<CompareArrowsIcon />}
                                                onClick={() => navigate(`/comparison/${run.run_id}/${result.name}`)}
                                                sx={{ mb: 1, fontSize: '0.65rem', height: 24 }}
                                              >
                                                View Comparison
                                              </Button>
                                            )}

                                            {/* Show key metrics */}
                                            {Object.entries(result.details)
                                              .filter(([key]) => !['mismatches', 'issues', 'duplicates', 'missing_in_sql', 'missing_in_snow', 'exception', 'error', 'comparison_details', 'affected_columns', 'differing_rows_count', 'difference_type'].includes(key))
                                              .map(([key, value]: any) => (
                                                <Box key={key} sx={{ mb: 0.5 }}>
                                                  <Typography variant="caption" component="span" sx={{ fontSize: '0.65rem', fontWeight: 'bold', mr: 0.5 }}>
                                                    {key}:
                                                  </Typography>
                                                  <Typography variant="caption" component="span" sx={{ fontSize: '0.65rem' }}>
                                                    {formatDetailValue(result.name, key, value)}
                                                  </Typography>
                                                </Box>
                                              ))}

                                            {/* Show detailed data in expandable section if exists */}
                                            {(result.details.mismatches?.length > 0 ||
                                              result.details.issues?.length > 0 ||
                                              result.details.outliers?.length > 0 ||
                                              result.details.results?.length > 0 ||
                                              result.details.details?.length > 0 ||
                                              result.details.duplicates?.length > 0 ||
                                              result.details.missing_in_sql?.length > 0 ||
                                              result.details.missing_in_snow?.length > 0 ||
                                              result.details.exception) && (
                                              <Accordion sx={{ mt: 0.5, boxShadow: 'none', '&:before': { display: 'none' } }}>
                                                <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: 'auto', p: 0.5 }}>
                                                  <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 'bold' }}>
                                                    {result.details.exception ? '⚠️ View Error Details' : '📋 View Details'}
                                                  </Typography>
                                                </AccordionSummary>
                                                <AccordionDetails sx={{ p: 0.5 }}>
                                                  {result.details.exception && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Alert severity="error" sx={{ py: 0.5, fontSize: '0.65rem' }}>
                                                        <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                          Exception:
                                                        </Typography>
                                                        <Typography variant="caption" sx={{ fontSize: '0.65rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                                                          {String(result.details.exception)}
                                                        </Typography>
                                                      </Alert>
                                                    </Box>
                                                  )}
                                                  {result.details.mismatches?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Mismatches ({result.details.mismatches.length}):
                                                      </Typography>
                                                      {formatDetailValue(result.name, 'mismatches', result.details.mismatches)}
                                                    </Box>
                                                  )}
                                                  {result.details.issues?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Issues ({result.details.issues.length}):
                                                      </Typography>
                                                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                                                        {formatDetailValue(result.name, 'issues', result.details.issues)}
                                                      </Box>
                                                    </Box>
                                                  )}
                                                  {result.details.duplicates?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Duplicates ({result.details.duplicates.length}):
                                                      </Typography>
                                                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                                                        {formatDetailValue(result.name, 'duplicates', result.details.duplicates)}
                                                      </Box>
                                                    </Box>
                                                  )}
                                                  {result.details.missing_in_sql?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Missing in SQL Server ({result.details.missing_in_sql.length}):
                                                      </Typography>
                                                      {formatDetailValue(result.name, 'missing_in_sql', result.details.missing_in_sql)}
                                                    </Box>
                                                  )}
                                                  {result.details.missing_in_snow?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Missing in Snowflake ({result.details.missing_in_snow.length}):
                                                      </Typography>
                                                      {formatDetailValue(result.name, 'missing_in_snow', result.details.missing_in_snow)}
                                                    </Box>
                                                  )}
                                                  {result.details.outliers?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Outliers ({result.details.outliers.length}):
                                                      </Typography>
                                                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                                                        {formatDetailValue(result.name, 'outliers', result.details.outliers)}
                                                      </Box>
                                                    </Box>
                                                  )}
                                                  {result.details.results?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Distribution Results ({result.details.results.length}):
                                                      </Typography>
                                                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                                                        {formatDetailValue(result.name, 'results', result.details.results)}
                                                      </Box>
                                                    </Box>
                                                  )}
                                                  {result.details.details?.length > 0 && (
                                                    <Box sx={{ mb: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.65rem', display: 'block', mb: 0.5 }}>
                                                        Ratio Details ({result.details.details.length}):
                                                      </Typography>
                                                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                                                        {formatDetailValue(result.name, 'details', result.details.details)}
                                                      </Box>
                                                    </Box>
                                                  )}
                                                  {result.details.explain && (
                                                    <Box sx={{ mb: 1, mt: 2, p: 1, backgroundColor: '#f0f7ff', borderRadius: 1 }}>
                                                      <Typography variant="caption" sx={{ fontWeight: 'bold', fontSize: '0.7rem', display: 'block', mb: 1, color: '#1976d2' }}>
                                                        🔍 Explain - Root Cause Analysis
                                                      </Typography>
                                                      {Object.entries(result.details.explain).map(([column, data]: [string, any]) => (
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
                                                                  {Object.entries(data.sql_distribution).map(([bucket, count]) => (
                                                                    <Typography key={bucket} variant="caption" sx={{ fontSize: '0.6rem', display: 'block' }}>
                                                                      {bucket}: {count as React.ReactNode}
                                                                    </Typography>
                                                                  ))}
                                                                </Box>
                                                                <Box sx={{ flex: 1 }}>
                                                                  <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#666' }}>Snowflake:</Typography>
                                                                  {Object.entries(data.snow_distribution).map(([bucket, count]) => (
                                                                    <Typography key={bucket} variant="caption" sx={{ fontSize: '0.6rem', display: 'block' }}>
                                                                      {bucket}: {count as React.ReactNode}
                                                                    </Typography>
                                                                  ))}
                                                                </Box>
                                                              </Box>
                                                            </Box>
                                                          )}

                                                          {/* Sample Data Comparison */}
                                                          {data.sql_samples && data.snow_samples && (
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
                                                                {Object.entries(data.queries).map(([qType, query]) => (
                                                                  <Box key={qType} sx={{ mb: 0.5 }}>
                                                                    <Typography variant="caption" sx={{ fontSize: '0.55rem', fontWeight: 'bold', color: '#666' }}>{qType}:</Typography>
                                                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{query as React.ReactNode}</pre>
                                                                  </Box>
                                                                ))}
                                                              </Box>
                                                            </Box>
                                                          )}
                                                        </Box>
                                                      ))}
                                                    </Box>
                                                  )}
                                                </AccordionDetails>
                                              </Accordion>
                                            )}
                                          </Box>
                                        ) : (
                                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                            No details
                                          </Typography>
                                        )}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Box>
                        ) : (
                          <Box>
                            {run.status === 'running' || run.status === 'pending' ? (
                              <Box sx={{ width: '100%', p: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                  <Typography variant="body2" color="text.secondary">
                                    {run.current_step_name || 'Starting pipeline...'}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    Step {run.current_step || 0}/{run.total_steps || 0}
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={run.total_steps > 0 ? (run.current_step / run.total_steps) * 100 : 0}
                                  sx={{ height: 8, borderRadius: 1 }}
                                />
                                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                                  {run.status === 'running' ? 'Executing...' : 'Pending...'}
                                </Typography>
                              </Box>
                            ) : (
                              <Alert severity="info" sx={{ py: 0.5 }}>
                                <Typography variant="caption">
                                  No results
                                </Typography>
                              </Alert>
                            )}
                          </Box>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Query Suggestions Dialog */}
      <QuerySuggestions
        open={showQuerySuggestions}
        onClose={() => setShowQuerySuggestions(false)}
        onSelectQueries={handleQuerySuggestionsSelect}
        selectedPipeline={selectedPipeline}
      />
    </Box>
  );
}
