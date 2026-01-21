import { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  CircularProgress,
  Chip,
  Grid
} from "@mui/material";

interface ColumnMetadata {
  name: string;
  data_type: string;
  is_nullable?: boolean;
  max_length?: number;
  precision?: number;
  scale?: number;
  is_primary_key?: boolean;
  default_value?: string;
}

interface DatabaseInfo {
  tables: string[];
  schema: string;
  count: number;
  error?: string;
}

interface DatabaseTables {
  sqlserver: {
    databases: { [key: string]: DatabaseInfo };
    status: string;
    error?: string;
  };
  snowflake: {
    databases: { [key: string]: DatabaseInfo };
    status: string;
    error?: string;
  };
}

interface MetadataExtractionProps {
    currentProject?: any;
}

export default function MetadataExtraction(_props: MetadataExtractionProps) {
  const [connection, setConnection] = useState("sqlserver");
  const [database, setDatabase] = useState<string>("");
  const [allTables, setAllTables] = useState<DatabaseTables | null>(null);
  const [selectedTable, setSelectedTable] = useState("");
  const [metadata, setMetadata] = useState<ColumnMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingTables, setLoadingTables] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAllTables();
  }, []);

  // Auto-select database when connection changes
  useEffect(() => {
    if (allTables && connection) {
      const databases = allTables[connection as keyof DatabaseTables]?.databases;
      if (databases) {
        const dbNames = Object.keys(databases);
        // Prefer SampleDW/SAMPLEDW if available, otherwise use first
        const preferredDb = connection === "sqlserver" ? "SampleDW" : "SAMPLEDW";
        if (dbNames.includes(preferredDb)) {
          setDatabase(preferredDb);
        } else if (dbNames.length > 0) {
          setDatabase(dbNames[0]);
        }
      }
      setSelectedTable("");
      setMetadata([]);
    }
  }, [connection, allTables]);

  const fetchAllTables = async () => {
    setLoadingTables(true);
    setError(null);
    setSelectedTable("");
    setMetadata([]);

    try {
      const response = await fetch("http://localhost:8000/metadata/tables/all");
      const data = await response.json();

      if (response.ok) {
        setAllTables(data);

        // Auto-select first database
        if (data.sqlserver?.databases) {
          const dbNames = Object.keys(data.sqlserver.databases);
          if (dbNames.includes("SampleDW")) {
            setDatabase("SampleDW");
          } else if (dbNames.length > 0) {
            setDatabase(dbNames[0]);
          }
        }
      } else {
        setError(data.detail || "Failed to fetch tables");
      }
    } catch (err) {
      setError(`Failed to fetch tables: ${err}`);
    }

    setLoadingTables(false);
  };

  const getAvailableDatabases = () => {
    if (!allTables) return [];
    return Object.keys(allTables[connection as keyof DatabaseTables]?.databases || {});
  };

  const getCurrentTables = () => {
    if (!allTables || !database) return [];
    const connData = allTables[connection as keyof DatabaseTables];
    return connData?.databases?.[database]?.tables || [];
  };

  const extractMetadata = async () => {
    if (!selectedTable) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/metadata/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connection,
          table: selectedTable
        })
      });

      const data = await response.json();

      if (response.ok) {
        setMetadata(data.columns || []);

        // Save to local storage for other modules
        localStorage.setItem(
          "schema",
          JSON.stringify({ source: data.columns || [] })
        );
      } else {
        setError(data.detail || data.error || "Failed to extract metadata");
      }
    } catch (err) {
      setError(`Failed to extract metadata: ${err}`);
    }

    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Metadata Extraction
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Extract and view table schema metadata from your configured databases
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Database Selection
              </Typography>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Connection</InputLabel>
                <Select
                  value={connection}
                  label="Connection"
                  onChange={(e) => setConnection(e.target.value)}
                >
                  <MenuItem value="sqlserver">SQL Server</MenuItem>
                  <MenuItem value="snowflake">Snowflake</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Database</InputLabel>
                <Select
                  value={database}
                  label="Database"
                  onChange={(e) => {
                    setDatabase(e.target.value);
                    setSelectedTable("");
                    setMetadata([]);
                  }}
                  disabled={loadingTables || getAvailableDatabases().length === 0}
                >
                  {getAvailableDatabases().map((db) => (
                    <MenuItem key={db} value={db}>
                      {db}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Table</InputLabel>
                <Select
                  value={selectedTable}
                  label="Table"
                  onChange={(e) => setSelectedTable(e.target.value)}
                  disabled={loadingTables || getCurrentTables().length === 0 || !database}
                >
                  {getCurrentTables().map((table) => (
                    <MenuItem key={table} value={table}>
                      {table}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {loadingTables && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              )}

              {allTables && !loadingTables && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Available Databases
                  </Typography>

                  {/* SQL Server Databases */}
                  <Typography variant="caption" display="block" sx={{ mt: 1, mb: 0.5, fontWeight: 'bold' }}>
                    SQL Server:
                  </Typography>
                  {Object.entries(allTables.sqlserver.databases || {}).map(([dbName, dbInfo]) => (
                    <Alert
                      key={dbName}
                      severity={dbInfo.error ? "warning" : "success"}
                      sx={{ mb: 1, py: 0.5 }}
                    >
                      <strong>{dbName}</strong>: {dbInfo.count || 0} table(s) in {dbInfo.schema}
                      {dbInfo.error && <Typography variant="caption" display="block" color="error">{dbInfo.error}</Typography>}
                    </Alert>
                  ))}

                  {/* Snowflake Databases */}
                  <Typography variant="caption" display="block" sx={{ mt: 1, mb: 0.5, fontWeight: 'bold' }}>
                    Snowflake:
                  </Typography>
                  {Object.entries(allTables.snowflake.databases || {}).map(([dbName, dbInfo]) => (
                    <Alert
                      key={dbName}
                      severity={dbInfo.error ? "warning" : "success"}
                      sx={{ mb: 1, py: 0.5 }}
                    >
                      <strong>{dbName}</strong>: {dbInfo.count || 0} table(s) in {dbInfo.schema}
                      {dbInfo.error && <Typography variant="caption" display="block" color="error">{dbInfo.error}</Typography>}
                    </Alert>
                  ))}
                </Box>
              )}

              <Button
                variant="contained"
                onClick={extractMetadata}
                disabled={loading || !selectedTable}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : "Extract Metadata"}
              </Button>

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Metadata Display */}
        <Grid item xs={12} md={8}>
          {metadata.length > 0 && (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Table: {selectedTable}
                  </Typography>
                  <Chip label={`${metadata.length} columns`} color="primary" />
                </Box>

                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ bgcolor: 'primary.main' }}>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Column Name</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Data Type</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Nullable</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Max Length</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Precision</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Scale</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>PK</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {metadata.map((col, idx) => (
                        <TableRow
                          key={idx}
                          sx={{
                            '&:hover': { bgcolor: 'action.hover' },
                            bgcolor: col.is_primary_key ? 'action.selected' : 'inherit'
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={col.is_primary_key ? 'bold' : 'normal'}>
                              {col.name}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={col.data_type} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>
                            {col.is_nullable ? (
                              <Chip label="YES" size="small" color="warning" />
                            ) : (
                              <Chip label="NO" size="small" color="success" />
                            )}
                          </TableCell>
                          <TableCell>{col.max_length || '-'}</TableCell>
                          <TableCell>{col.precision || '-'}</TableCell>
                          <TableCell>{col.scale || '-'}</TableCell>
                          <TableCell>
                            {col.is_primary_key && <Chip label="PK" size="small" color="primary" />}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    label={`Primary Keys: ${metadata.filter(c => c.is_primary_key).length}`}
                    color="primary"
                    size="small"
                  />
                  <Chip
                    label={`Nullable: ${metadata.filter(c => c.is_nullable).length}`}
                    color="warning"
                    size="small"
                  />
                  <Chip
                    label={`Not Null: ${metadata.filter(c => !c.is_nullable).length}`}
                    color="success"
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          )}

          {metadata.length === 0 && !loading && !error && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" align="center">
                  Select a database and table to view metadata
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
