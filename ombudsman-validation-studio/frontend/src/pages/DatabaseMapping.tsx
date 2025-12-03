import { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    TextField,
    Grid,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Alert,
    CircularProgress,
    Chip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    IconButton
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import mermaid from 'mermaid';

interface DatabaseMappingProps {
    currentProject?: any;
}

export default function DatabaseMapping({ currentProject }: DatabaseMappingProps) {
    const [sqlDatabase, setSqlDatabase] = useState('SampleDW');
    const [snowflakeDatabase, setSnowflakeDatabase] = useState('SAMPLEDW');

    const [availableDatabases, setAvailableDatabases] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [extractionResult, setExtractionResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    // New state for existing mappings and editing
    const [existingMappings, setExistingMappings] = useState<any>(null);
    const [editMode, setEditMode] = useState(false);
    const [overrides, setOverrides] = useState<{[key: string]: string}>({});
    const [editedMappings, setEditedMappings] = useState<any[]>([]);
    const [saving, setSaving] = useState(false);

    // Schema mapping state
    const [availableSchemas, setAvailableSchemas] = useState<any>(null);
    const [schemaMappings, setSchemaMappings] = useState<{[key: string]: string}>({});
    const [schemaEditMode, setSchemaEditMode] = useState(false);
    const [newSqlSchema, setNewSqlSchema] = useState('');
    const [newSnowSchema, setNewSnowSchema] = useState('');

    // Relationship inference state
    const [sqlRelationships, setSqlRelationships] = useState<any>(null);
    const [snowRelationships, setSnowRelationships] = useState<any>(null);
    const [inferring, setInferring] = useState(false);
    const [selectedDatabase, setSelectedDatabase] = useState<'sql' | 'snow'>('sql');
    const [editedRelationships, setEditedRelationships] = useState<any[]>([]);
    const [relationshipEditMode, setRelationshipEditMode] = useState(false);
    const [availableTables, setAvailableTables] = useState<string[]>([]);

    // Computed values based on selected database
    const inferredRelationships = selectedDatabase === 'sql' ? sqlRelationships?.relationships : snowRelationships?.relationships;
    const relationshipMetrics = selectedDatabase === 'sql' ? sqlRelationships?.metrics : snowRelationships?.metrics;
    const mermaidDiagram = selectedDatabase === 'sql' ? sqlRelationships?.diagram : snowRelationships?.diagram;
    const showDiagram = !!(selectedDatabase === 'sql' ? sqlRelationships?.diagram : snowRelationships?.diagram);

    // Table mappings filter state
    const [searchFilter, setSearchFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [mappingEditMode, setMappingEditMode] = useState(false);
    const [editingMappings, setEditingMappings] = useState<any[]>([]);
    const [expandedRow, setExpandedRow] = useState<number | null>(null);
    const [availableSnowflakeTables, setAvailableSnowflakeTables] = useState<string[]>([]);
    const [columnFilter, setColumnFilter] = useState<string>('all'); // all, unmapped, low_confidence
    const [columnEditingTable, setColumnEditingTable] = useState<string | null>(null);
    const [editedColumnMappings, setEditedColumnMappings] = useState<any>({});

    useEffect(() => {
        fetchAvailableDatabases();
        loadExistingMappings();
        loadSchemaMappings();
        // Initialize Mermaid
        mermaid.initialize({ startOnLoad: true, theme: 'default' });

        // Auto-load extraction results if they exist
        const autoLoadExtraction = async () => {
            try {
                const response = await fetch('http://localhost:8000/database-mapping/mappings');
                const data = await response.json();

                if (data.status === 'success' && data.mappings && data.mappings.length > 0) {
                    // Set as extraction result so it displays
                    setExtractionResult({
                        mappings: data.mappings,
                        sql_server: {
                            total_tables_found: data.mappings.filter((m: any) => m.sql_server_table).length
                        },
                        snowflake: {
                            total_tables_found: data.mappings.filter((m: any) => m.snowflake_table).length
                        },
                        yaml_generated: {
                            column_mappings_count: data.column_mappings_count || 0,
                            unmapped_columns_count: 0,
                            relationships_count: 0
                        }
                    });
                    console.log('Loaded existing extraction with', data.mappings.length, 'table mappings');
                }
            } catch (err) {
                console.log('No existing extraction found');
            }
        };

        autoLoadExtraction();
    }, []);

    // Auto-load relationships when a project is loaded
    useEffect(() => {
        if (currentProject && currentProject.config) {
            const loadProjectRelationships = async () => {
                try {
                    const config = currentProject.config;

                    // Load SQL relationships if they exist
                    if (config.sql_relationships) {
                        const sqlRels = {
                            relationships: config.sql_relationships.relationships || [],
                            metrics: config.sql_relationships.metrics || {},
                            diagram: config.sql_relationships.diagram || ''
                        };
                        setSqlRelationships(sqlRels);
                        // Set edited relationships to SQL if that's the selected database
                        if (selectedDatabase === 'sql') {
                            setEditedRelationships(sqlRels.relationships);
                        }
                        console.log('Loaded SQL relationships from project:', sqlRels.relationships.length, 'relationships');
                    }

                    // Load Snowflake relationships if they exist
                    if (config.snow_relationships) {
                        const snowRels = {
                            relationships: config.snow_relationships.relationships || [],
                            metrics: config.snow_relationships.metrics || {},
                            diagram: config.snow_relationships.diagram || ''
                        };
                        setSnowRelationships(snowRels);
                        // Set edited relationships to Snowflake if that's the selected database
                        if (selectedDatabase === 'snow') {
                            setEditedRelationships(snowRels.relationships);
                        }
                        console.log('Loaded Snowflake relationships from project:', snowRels.relationships.length, 'relationships');
                    }
                } catch (err) {
                    console.error('Failed to load project relationships:', err);
                }
            };

            loadProjectRelationships();
        }
    }, [currentProject, selectedDatabase]);

    // Update editedRelationships when switching databases
    useEffect(() => {
        if (selectedDatabase === 'sql' && sqlRelationships) {
            setEditedRelationships(sqlRelationships.relationships || []);
        } else if (selectedDatabase === 'snow' && snowRelationships) {
            setEditedRelationships(snowRelationships.relationships || []);
        }
    }, [selectedDatabase, sqlRelationships, snowRelationships]);

    // Render Mermaid diagram when it changes
    useEffect(() => {
        if (mermaidDiagram && showDiagram) {
            const renderDiagram = async () => {
                try {
                    const element = document.getElementById('mermaid-container');
                    if (element) {
                        // Clear previous content
                        element.removeAttribute('data-processed');
                        element.innerHTML = '';

                        // Add new content
                        element.innerHTML = mermaidDiagram;

                        // Re-initialize and render
                        await mermaid.run({ nodes: [element] });
                    }
                } catch (error) {
                    console.error('Error rendering Mermaid diagram:', error);
                    // Try re-initializing mermaid
                    mermaid.initialize({ startOnLoad: true, theme: 'default' });
                }
            };
            renderDiagram();
        }
    }, [mermaidDiagram, showDiagram, selectedDatabase]);

    const fetchAvailableDatabases = async () => {
        try {
            const response = await fetch('http://localhost:8000/database-mapping/available-databases');
            const data = await response.json();
            setAvailableDatabases(data);
        } catch (err) {
            console.error('Failed to fetch available databases:', err);
        }
    };

    const loadExistingMappings = async () => {
        try {
            const response = await fetch('http://localhost:8000/database-mapping/mappings');
            const data = await response.json();

            if (data.status === 'success') {
                setExistingMappings(data);
                setOverrides(data.overrides || {});
                setEditedMappings(data.mappings || []);

                // Load project config if available
                if (data.project_config) {
                    console.log('[DatabaseMapping] Loading project config:', data.project_config);
                    setSqlDatabase(data.project_config.sql_database || 'SampleDW');
                    setSnowflakeDatabase(data.project_config.snowflake_database || 'SAMPLEDW');
                    if (data.project_config.schema_mappings) {
                        setSchemaMappings(data.project_config.schema_mappings);
                    }
                }
            } else if (data.status === 'no_mappings') {
                setExistingMappings(null);

                // Load project config if available even when no mappings exist
                if (data.project_config) {
                    console.log('[DatabaseMapping] No mappings found, but loading project config:', data.project_config);
                    setSqlDatabase(data.project_config.sql_database || 'SampleDW');
                    setSnowflakeDatabase(data.project_config.snowflake_database || 'SAMPLEDW');
                    if (data.project_config.schema_mappings) {
                        setSchemaMappings(data.project_config.schema_mappings);
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load existing mappings:', err);
        }
    };

    const loadSchemaMappings = async () => {
        try {
            const response = await fetch('http://localhost:8000/database-mapping/schema-mappings');
            const data = await response.json();

            if (data.status === 'success') {
                setSchemaMappings(data.mappings || {});
            }
        } catch (err) {
            console.error('Failed to load schema mappings:', err);
        }
    };

    const fetchAvailableSchemas = async () => {
        try {
            const response = await fetch(
                `http://localhost:8000/database-mapping/available-schemas?sql_database=${sqlDatabase}&snowflake_database=${snowflakeDatabase}`
            );
            const data = await response.json();
            setAvailableSchemas(data);
        } catch (err) {
            console.error('Failed to fetch available schemas:', err);
        }
    };

    const saveSchemaMappings = async () => {
        setSaving(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/database-mapping/schema-mappings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    mappings: schemaMappings
                })
            });

            const data = await response.json();

            if (response.ok) {
                setSchemaEditMode(false);
                await loadSchemaMappings();
                setError(null);
            } else {
                setError(data.detail || 'Failed to save schema mappings');
            }
        } catch (err) {
            setError(`Failed to save schema mappings: ${err}`);
        }

        setSaving(false);
    };

    const addSchemaMapping = () => {
        if (newSqlSchema && newSnowSchema) {
            setSchemaMappings({
                ...schemaMappings,
                [newSqlSchema]: newSnowSchema
            });
            setNewSqlSchema('');
            setNewSnowSchema('');
        }
    };

    const removeSchemaMapping = (sqlSchema: string) => {
        const newMappings = { ...schemaMappings };
        delete newMappings[sqlSchema];
        setSchemaMappings(newMappings);
    };

    const saveMappings = async () => {
        setSaving(true);
        setError(null);

        try {
            // Build overrides from editingMappings
            const newOverrides: {[key: string]: string} = {};
            editingMappings.forEach((m: any) => {
                if (m.is_custom_mapping && m.sql_server_table && m.snowflake_table) {
                    newOverrides[m.sql_server_table] = m.snowflake_table;
                }
            });

            const response = await fetch('http://localhost:8000/database-mapping/mappings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    overrides: newOverrides,
                    mappings: editingMappings
                })
            });

            const data = await response.json();

            if (response.ok) {
                setMappingEditMode(false);
                setEditMode(false);
                await loadExistingMappings(); // Reload to show updated data
                setError(null);
            } else {
                setError(data.detail || 'Failed to save mappings');
            }
        } catch (err) {
            setError(`Failed to save mappings: ${err}`);
        }

        setSaving(false);
    };

    const saveProject = async () => {
        if (!currentProject) {
            setError('No project loaded. Please create or load a project first.');
            return;
        }

        setSaving(true);
        setError(null);

        try {
            const response = await fetch(`http://localhost:8000/projects/${currentProject.project_id}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (response.ok) {
                setError(null);
                alert(`Project "${currentProject.name}" saved successfully!`);
            } else {
                setError(data.detail || 'Failed to save project');
            }
        } catch (err) {
            setError(`Failed to save project: ${err}`);
        }

        setSaving(false);
    };

    const updateSnowflakeTableMapping = (sqlTable: string, newSnowTable: string) => {
        // Update overrides
        const newOverrides = { ...overrides };
        if (newSnowTable) {
            newOverrides[sqlTable] = newSnowTable;
        } else {
            delete newOverrides[sqlTable];
        }
        setOverrides(newOverrides);

        // Update the mapping in editedMappings
        const newMappings = editedMappings.map(mapping => {
            if (mapping.sql_server_table === sqlTable) {
                return {
                    ...mapping,
                    snowflake_table: newSnowTable,
                    is_custom_mapping: true,
                    match_status: newSnowTable ? 'found_in_both' : 'only_in_sql_server'
                };
            }
            return mapping;
        });
        setEditedMappings(newMappings);
    };

    // Initialize editing mappings when extraction result changes
    useEffect(() => {
        if (extractionResult?.mappings) {
            setEditingMappings(extractionResult.mappings);

            // Extract ALL Snowflake tables for dropdown (including unmatched ones)
            const snowflakeTables = new Set<string>();
            const allTables = new Set<string>();

            extractionResult.mappings.forEach((m: any) => {
                if (m.snowflake_table) {
                    snowflakeTables.add(m.snowflake_table);
                }
                // Also add all columns from snowflake_columns in case of SQL-only tables
                if (m.match_status === 'only_in_snowflake') {
                    snowflakeTables.add(m.snowflake_table);
                }

                // For relationship editing, collect all tables based on selected database
                if (selectedDatabase === 'sql' && m.sql_server_table) {
                    allTables.add(m.sql_server_table);
                } else if (selectedDatabase === 'snow' && m.snowflake_table) {
                    allTables.add(m.snowflake_table);
                }
            });

            setAvailableSnowflakeTables(Array.from(snowflakeTables).sort());
            setAvailableTables(Array.from(allTables).sort());
        }
    }, [extractionResult, selectedDatabase]);

    // Also populate dropdown when existing mappings are loaded
    useEffect(() => {
        if (!extractionResult && existingMappings?.mappings) {
            setEditingMappings(existingMappings.mappings);

            // Extract ALL Snowflake tables for dropdown (including unmatched ones)
            const snowflakeTables = new Set<string>();
            existingMappings.mappings.forEach((m: any) => {
                if (m.snowflake_table) {
                    snowflakeTables.add(m.snowflake_table);
                }
                // Also add all columns from snowflake_columns in case of SQL-only tables
                if (m.match_status === 'only_in_snowflake') {
                    snowflakeTables.add(m.snowflake_table);
                }
            });
            setAvailableSnowflakeTables(Array.from(snowflakeTables).sort());
        }
    }, [existingMappings, extractionResult]);

    // Filter mappings based on search and status
    const getFilteredMappings = () => {
        const source = mappingEditMode
            ? editingMappings
            : (extractionResult?.mappings || existingMappings?.mappings || []);

        let filtered = source;

        // Apply search filter
        if (searchFilter) {
            const search = searchFilter.toLowerCase();
            filtered = filtered.filter((m: any) =>
                (m.sql_server_table?.toLowerCase().includes(search)) ||
                (m.snowflake_table?.toLowerCase().includes(search))
            );
        }

        // Apply status filter
        if (statusFilter !== 'all') {
            if (statusFilter === 'issues') {
                filtered = filtered.filter((m: any) =>
                    m.match_status !== 'found_in_both' ||
                    Object.keys(m.sql_columns || {}).length !== Object.keys(m.snowflake_columns || {}).length
                );
            } else {
                filtered = filtered.filter((m: any) => m.match_status === statusFilter);
            }
        }

        return filtered;
    };

    const updateTableMapping = (sqlServerTable: string, snowflakeTable: string) => {
        const updated = editingMappings.map((m: any) => {
            if (m.sql_server_table === sqlServerTable) {
                return {
                    ...m,
                    snowflake_table: snowflakeTable,
                    is_custom_mapping: true
                };
            }
            return m;
        });
        setEditingMappings(updated);
    };

    const inferRelationships = async () => {
        setInferring(true);
        setError(null);

        try {
            // Infer relationships for BOTH SQL and Snowflake
            const [sqlResponse, snowResponse] = await Promise.all([
                fetch('http://localhost:8000/metadata/infer-relationships', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        use_existing_mappings: true,
                        source_database: 'sql'
                    })
                }),
                fetch('http://localhost:8000/metadata/infer-relationships', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        use_existing_mappings: true,
                        source_database: 'snow'
                    })
                })
            ]);

            const [sqlData, snowData] = await Promise.all([
                sqlResponse.json(),
                snowResponse.json()
            ]);

            if (sqlResponse.ok && snowResponse.ok) {
                // Generate diagrams for both
                const [sqlDiagram, snowDiagram] = await Promise.all([
                    generateMermaidDiagram(sqlData.relationships, 'sql'),
                    generateMermaidDiagram(snowData.relationships, 'snow')
                ]);

                const sqlRelData = {
                    relationships: sqlData.relationships,
                    metrics: sqlData.metrics,
                    diagram: sqlDiagram
                };

                const snowRelData = {
                    relationships: snowData.relationships,
                    metrics: snowData.metrics,
                    diagram: snowDiagram
                };

                setSqlRelationships(sqlRelData);
                setSnowRelationships(snowRelData);

                // Set edited relationships to current selection
                setEditedRelationships(selectedDatabase === 'sql' ? sqlData.relationships : snowData.relationships);

                // Auto-save relationships to project if a project is loaded
                if (currentProject) {
                    try {
                        await Promise.all([
                            fetch(`http://localhost:8000/projects/${currentProject.project_id}/relationships/sql`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(sqlRelData)
                            }),
                            fetch(`http://localhost:8000/projects/${currentProject.project_id}/relationships/snow`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(snowRelData)
                            })
                        ]);
                        console.log('Auto-saved relationships to project');
                    } catch (saveErr) {
                        console.error('Failed to auto-save relationships:', saveErr);
                    }
                }
            } else {
                setError(sqlData.detail || snowData.detail || 'Relationship inference failed');
            }
        } catch (err) {
            setError(`Failed to infer relationships: ${err}`);
        }

        setInferring(false);
    };

    const generateMermaidDiagram = async (relationships: any[], sourceDatabase: 'sql' | 'snow'): Promise<string> => {
        try {
            const response = await fetch('http://localhost:8000/mermaid/generate-with-inference', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    inferred_relationships: relationships,
                    show_columns: true,
                    source_database: sourceDatabase
                })
            });

            const data = await response.json();

            if (response.ok) {
                return data.diagram;
            } else {
                console.error('Failed to generate diagram:', data);
                return '';
            }
        } catch (err) {
            console.error('Failed to generate diagram:', err);
            return '';
        }
    };

    const saveInferredRelationships = async () => {
        setSaving(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/metadata/save-relationships', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    relationships: editedRelationships
                })
            });

            const data = await response.json();

            if (response.ok) {
                setRelationshipEditMode(false);
                setError(null);
            } else {
                setError(data.detail || 'Failed to save relationships');
            }
        } catch (err) {
            setError(`Failed to save relationships: ${err}`);
        }

        setSaving(false);
    };

    const removeRelationship = async (index: number) => {
        const newRelationships = editedRelationships.filter((_, i) => i !== index);
        setEditedRelationships(newRelationships);

        // Update the correct state based on selected database
        const updatedData = selectedDatabase === 'sql'
            ? { ...sqlRelationships, relationships: newRelationships }
            : { ...snowRelationships, relationships: newRelationships };

        if (selectedDatabase === 'sql') {
            setSqlRelationships(updatedData);
        } else {
            setSnowRelationships(updatedData);
        }

        // Auto-save to project if one is loaded
        if (currentProject) {
            try {
                await fetch(`http://localhost:8000/projects/${currentProject.project_id}/relationships/${selectedDatabase}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedData)
                });
                console.log(`Auto-saved ${selectedDatabase} relationships after removal`);
            } catch (err) {
                console.error('Failed to auto-save relationships:', err);
            }
        }
    };

    const addNewRelationship = () => {
        const newRel = {
            fact_table: '',
            fk_column: '',
            dim_table: '',
            dim_column: '',
            confidence: 'manual',
            confidence_score: 1.0,
            method: 'manual'
        };
        const updated = [...editedRelationships, newRel];
        setEditedRelationships(updated);
    };

    const updateRelationship = async (index: number, field: string, value: string) => {
        const updated = [...editedRelationships];

        // Mark as manually overridden if it was auto-inferred
        const wasAutoInferred = updated[index].method !== 'manual' && updated[index].method !== 'manual_override';

        updated[index] = {
            ...updated[index],
            [field]: value,
            // Mark as override if it was previously auto-inferred
            method: wasAutoInferred ? 'manual_override' : updated[index].method,
            confidence: wasAutoInferred ? 'manual' : updated[index].confidence,
            confidence_score: wasAutoInferred ? 1.0 : updated[index].confidence_score
        };

        setEditedRelationships(updated);

        // Update the correct state
        const updatedData = selectedDatabase === 'sql'
            ? { ...sqlRelationships, relationships: updated }
            : { ...snowRelationships, relationships: updated };

        if (selectedDatabase === 'sql') {
            setSqlRelationships(updatedData);
        } else {
            setSnowRelationships(updatedData);
        }

        // Auto-save to project if one is loaded
        if (currentProject) {
            try {
                await fetch(`http://localhost:8000/projects/${currentProject.project_id}/relationships/${selectedDatabase}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedData)
                });
                console.log(`Auto-saved ${selectedDatabase} relationships after update`);
            } catch (err) {
                console.error('Failed to auto-save relationships:', err);
            }
        }
    };

    const regenerateDiagram = async () => {
        try {
            const diagram = await generateMermaidDiagram(editedRelationships, selectedDatabase);

            const updatedData = selectedDatabase === 'sql'
                ? { ...sqlRelationships, diagram }
                : { ...snowRelationships, diagram };

            if (selectedDatabase === 'sql') {
                setSqlRelationships(updatedData);
            } else {
                setSnowRelationships(updatedData);
            }

            // Auto-save to project if one is loaded
            if (currentProject) {
                try {
                    await fetch(`http://localhost:8000/projects/${currentProject.project_id}/relationships/${selectedDatabase}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updatedData)
                    });
                    console.log(`Regenerated and saved ${selectedDatabase} diagram`);
                } catch (err) {
                    console.error('Failed to save regenerated diagram:', err);
                }
            }
        } catch (err) {
            console.error('Failed to regenerate diagram:', err);
            setError(`Failed to regenerate diagram: ${err}`);
        }
    };

    // Helper function to get columns for a specific table
    const getColumnsForTable = (tableName: string): string[] => {
        const mappings = extractionResult?.mappings || existingMappings?.mappings || [];

        for (const mapping of mappings) {
            // Check if this is the SQL table (when selectedDatabase is 'sql')
            if (selectedDatabase === 'sql' && mapping.sql_server_table === tableName) {
                return Object.keys(mapping.sql_columns || {});
            }
            // Check if this is the Snowflake table (when selectedDatabase is 'snow')
            if (selectedDatabase === 'snow' && mapping.snowflake_table === tableName) {
                return Object.keys(mapping.snowflake_columns || {});
            }
        }

        return [];
    };

    const extractMetadata = async () => {
        setLoading(true);
        setError(null);
        setExtractionResult(null);

        try {
            // Use schema mappings
            const requestSchemaMappings = Object.keys(schemaMappings).length > 0
                ? schemaMappings
                : { 'dbo': 'PUBLIC' }; // Default fallback

            const response = await fetch('http://localhost:8000/database-mapping/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sql_server_database: sqlDatabase,
                    sql_server_schema: 'dbo', // Will be overridden by schema_mappings
                    snowflake_database: snowflakeDatabase,
                    snowflake_schema: 'PUBLIC', // Will be overridden by schema_mappings
                    table_patterns: ['%'], // Extract all tables
                    schema_mappings: requestSchemaMappings
                })
            });

            const data = await response.json();

            if (response.ok) {
                setExtractionResult(data);
                // Reload existing mappings to show the newly created ones
                await loadExistingMappings();
            } else {
                setError(data.detail || 'Metadata extraction failed');
            }
        } catch (err) {
            setError(`Failed to extract metadata: ${err}`);
        }

        setLoading(false);
    };

    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        Database & Schema Mapping
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Configure database and schema mappings for metadata extraction and validation
                    </Typography>
                </Box>
                {currentProject && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ textAlign: 'right' }}>
                            <Chip label={currentProject.name} color="primary" />
                            <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                                Last updated: {new Date(currentProject.updated_at).toLocaleString()}
                            </Typography>
                        </Box>
                        <Button
                            variant="contained"
                            color="success"
                            startIcon={<SaveIcon />}
                            onClick={saveProject}
                            disabled={saving}
                        >
                            {saving ? <CircularProgress size={20} /> : 'Save Project'}
                        </Button>
                    </Box>
                )}
            </Box>

            {/* KPI Metrics */}
            {existingMappings && existingMappings.status === 'success' && (
                <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h4" color="primary">
                                    {existingMappings.total_mappings}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Total Tables
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h4" color="success.main">
                                    {existingMappings.mappings?.filter((m: any) => m.match_status === 'found_in_both').length || 0}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Matched Tables
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h4" color="warning.main">
                                    {existingMappings.mappings?.filter((m: any) => m.match_status === 'only_in_sql_server').length || 0}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    SQL Server Only
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                    <Grid item xs={3}>
                        <Card>
                            <CardContent>
                                <Typography variant="h4" color="info.main">
                                    {existingMappings.mappings?.filter((m: any) => m.match_status === 'only_in_snowflake').length || 0}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Snowflake Only
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                </Grid>
            )}

            {/* Schema Mappings Section */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6">
                            Schema Mappings ({Object.keys(schemaMappings).length})
                        </Typography>
                        <Box>
                            <Button
                                variant="outlined"
                                onClick={fetchAvailableSchemas}
                                sx={{ mr: 1 }}
                                size="small"
                            >
                                Discover Schemas
                            </Button>
                            {!schemaEditMode && (
                                <Button
                                    variant="outlined"
                                    onClick={() => setSchemaEditMode(true)}
                                    sx={{ mr: 1 }}
                                >
                                    Edit Schema Mappings
                                </Button>
                            )}
                            {schemaEditMode && (
                                <>
                                    <Button
                                        variant="outlined"
                                        onClick={() => {
                                            setSchemaEditMode(false);
                                            loadSchemaMappings(); // Reset changes
                                        }}
                                        sx={{ mr: 1 }}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="contained"
                                        onClick={saveSchemaMappings}
                                        disabled={saving}
                                    >
                                        {saving ? <CircularProgress size={20} /> : 'Save Schema Mappings'}
                                    </Button>
                                </>
                            )}
                        </Box>
                    </Box>

                    <Alert severity="info" sx={{ mb: 2 }}>
                        <strong>Schema Mapping:</strong> Map SQL Server schemas to Snowflake schemas (e.g., "dimension" → "dim", "facttable" → "fact").
                        This allows extraction from multiple schemas at once.
                    </Alert>

                    {/* Available Schemas */}
                    {availableSchemas && (
                        <Grid container spacing={2} sx={{ mb: 2 }}>
                            <Grid item xs={6}>
                                <Alert severity="success">
                                    <Typography variant="subtitle2">SQL Server Schemas</Typography>
                                    {availableSchemas.sql_server?.map((schema: string) => (
                                        <Chip key={schema} label={schema} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
                                    ))}
                                </Alert>
                            </Grid>
                            <Grid item xs={6}>
                                <Alert severity="success">
                                    <Typography variant="subtitle2">Snowflake Schemas</Typography>
                                    {availableSchemas.snowflake?.map((schema: string) => (
                                        <Chip key={schema} label={schema} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
                                    ))}
                                </Alert>
                            </Grid>
                        </Grid>
                    )}

                    {/* Current Schema Mappings */}
                    <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell><strong>SQL Server Schema</strong></TableCell>
                                    <TableCell><strong>Snowflake Schema</strong></TableCell>
                                    {schemaEditMode && <TableCell><strong>Actions</strong></TableCell>}
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {Object.entries(schemaMappings).map(([sqlSchema, snowSchema]) => (
                                    <TableRow key={sqlSchema}>
                                        <TableCell>{sqlSchema}</TableCell>
                                        <TableCell>{snowSchema}</TableCell>
                                        {schemaEditMode && (
                                            <TableCell>
                                                <Button
                                                    size="small"
                                                    color="error"
                                                    onClick={() => removeSchemaMapping(sqlSchema)}
                                                >
                                                    Remove
                                                </Button>
                                            </TableCell>
                                        )}
                                    </TableRow>
                                ))}
                                {Object.keys(schemaMappings).length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={schemaEditMode ? 3 : 2} align="center">
                                            <Typography variant="body2" color="text.secondary">
                                                No schema mappings configured. Will use default schema from configuration.
                                            </Typography>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>

                    {/* Add Schema Mapping */}
                    {schemaEditMode && (
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <TextField
                                size="small"
                                label="SQL Server Schema"
                                value={newSqlSchema}
                                onChange={(e) => setNewSqlSchema(e.target.value)}
                                placeholder="e.g., dimension"
                            />
                            <Typography>→</Typography>
                            <TextField
                                size="small"
                                label="Snowflake Schema"
                                value={newSnowSchema}
                                onChange={(e) => setNewSnowSchema(e.target.value)}
                                placeholder="e.g., dim"
                            />
                            <Button
                                variant="outlined"
                                onClick={addSchemaMapping}
                                disabled={!newSqlSchema || !newSnowSchema}
                            >
                                Add Mapping
                            </Button>
                        </Box>
                    )}
                </CardContent>
            </Card>

            {/* Extract Metadata Action */}
            <Card sx={{ mb: 3 }}>
                <CardContent>
                    <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} md={3}>
                            <FormControl fullWidth>
                                <InputLabel>SQL Server Database</InputLabel>
                                <Select
                                    value={sqlDatabase}
                                    label="SQL Server Database"
                                    onChange={(e) => setSqlDatabase(e.target.value)}
                                >
                                    {availableDatabases?.sql_server?.map((db: string) => (
                                        <MenuItem key={db} value={db}>{db}</MenuItem>
                                    ))}
                                    {!availableDatabases && <MenuItem value="SampleDW">SampleDW</MenuItem>}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} md={3}>
                            <FormControl fullWidth>
                                <InputLabel>Snowflake Database</InputLabel>
                                <Select
                                    value={snowflakeDatabase}
                                    label="Snowflake Database"
                                    onChange={(e) => setSnowflakeDatabase(e.target.value)}
                                >
                                    {availableDatabases?.snowflake?.map((db: string) => (
                                        <MenuItem key={db} value={db}>{db}</MenuItem>
                                    ))}
                                    {!availableDatabases && <MenuItem value="SAMPLEDW">SAMPLEDW</MenuItem>}
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Button
                                variant="contained"
                                onClick={extractMetadata}
                                disabled={loading || Object.keys(schemaMappings).length === 0}
                                fullWidth
                                size="large"
                            >
                                {loading ? <CircularProgress size={24} /> : 'Extract & Map Metadata'}
                            </Button>
                        </Grid>
                    </Grid>

                    {error && (
                        <Alert severity="error" sx={{ mt: 2 }}>
                            {error}
                        </Alert>
                    )}

                    <Alert severity="info" sx={{ mt: 2 }}>
                        Extraction will use the schema mappings configured above to extract tables from multiple schemas.
                    </Alert>
                </CardContent>
            </Card>

            <Grid container spacing={3}>

                {/* Results Panel - Compact */}
                {extractionResult && (
                    <Grid item xs={12}>
                        <Alert severity="success">
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
                                <Typography variant="body2">
                                    <strong>Extraction Complete:</strong>
                                </Typography>
                                <Chip
                                    label={`SQL Server: ${extractionResult.sql_server?.total_tables_found || 0} tables`}
                                    color="primary"
                                    size="small"
                                />
                                <Chip
                                    label={`Snowflake: ${extractionResult.snowflake?.total_tables_found || 0} tables`}
                                    color="info"
                                    size="small"
                                />
                                <Chip
                                    label={`Mapped: ${extractionResult.mappings?.length || 0} tables`}
                                    color="success"
                                    size="small"
                                />
                                {extractionResult.yaml_generated && (
                                    <>
                                        <Chip
                                            label={`Columns: ${extractionResult.yaml_generated.column_mappings_count || 0} mapped`}
                                            color="success"
                                            size="small"
                                        />
                                        {extractionResult.yaml_generated.unmapped_columns_count > 0 && (
                                            <Chip
                                                label={`${extractionResult.yaml_generated.unmapped_columns_count} unmapped cols`}
                                                color="warning"
                                                size="small"
                                            />
                                        )}
                                        <Chip
                                            label={`Relationships: ${extractionResult.yaml_generated.relationships_count || 0}`}
                                            color="secondary"
                                            size="small"
                                        />
                                    </>
                                )}
                            </Box>
                        </Alert>
                    </Grid>
                )}

                {/* Enhanced Table Mappings - Show extraction results OR existing mappings */}
                {(extractionResult?.mappings || existingMappings?.mappings) && (
                    <Grid item xs={12}>
                        <Card>
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography variant="h6">
                                        Table Mappings ({getFilteredMappings().length} / {(extractionResult?.mappings || existingMappings?.mappings)?.length || 0})
                                        {!extractionResult && existingMappings && (
                                            <Chip label="Loaded from YAML" size="small" color="info" sx={{ ml: 1 }} />
                                        )}
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <TextField
                                            size="small"
                                            placeholder="Search tables..."
                                            value={searchFilter}
                                            onChange={(e) => setSearchFilter(e.target.value)}
                                            sx={{ width: 200 }}
                                        />
                                        <FormControl size="small" sx={{ minWidth: 150 }}>
                                            <InputLabel>Filter</InputLabel>
                                            <Select
                                                value={statusFilter}
                                                label="Filter"
                                                onChange={(e) => setStatusFilter(e.target.value)}
                                            >
                                                <MenuItem value="all">All Tables</MenuItem>
                                                <MenuItem value="issues">Issues Only</MenuItem>
                                                <MenuItem value="found_in_both">Matched</MenuItem>
                                                <MenuItem value="only_in_sql_server">SQL Server Only</MenuItem>
                                                <MenuItem value="only_in_snowflake">Snowflake Only</MenuItem>
                                            </Select>
                                        </FormControl>
                                        {!mappingEditMode && (
                                            <Button variant="outlined" onClick={() => setMappingEditMode(true)}>
                                                Edit Mappings
                                            </Button>
                                        )}
                                        {mappingEditMode && (
                                            <>
                                                <Button
                                                    variant="outlined"
                                                    onClick={() => {
                                                        setMappingEditMode(false);
                                                        // Reset to original mappings
                                                        if (extractionResult?.mappings) {
                                                            setEditingMappings(extractionResult.mappings);
                                                        }
                                                    }}
                                                >
                                                    Cancel
                                                </Button>
                                                <Button variant="contained" onClick={saveMappings} disabled={saving}>
                                                    {saving ? <CircularProgress size={20} /> : 'Save'}
                                                </Button>
                                            </>
                                        )}
                                    </Box>
                                </Box>

                                <Box>
                                    {/* Header Row */}
                                    <Paper variant="outlined" sx={{ p: 1.5, mb: 1, backgroundColor: '#f5f5f5' }}>
                                        <Grid container spacing={2} alignItems="center">
                                            <Grid item xs={3}>
                                                <Typography variant="subtitle2"><strong>SQL Server (Source)</strong></Typography>
                                            </Grid>
                                            <Grid item xs={3}>
                                                <Typography variant="subtitle2"><strong>Snowflake (Target)</strong></Typography>
                                            </Grid>
                                            <Grid item xs={2}>
                                                <Typography variant="subtitle2" align="center"><strong>Status</strong></Typography>
                                            </Grid>
                                            <Grid item xs={1.5}>
                                                <Typography variant="subtitle2" align="center"><strong>SQL Cols</strong></Typography>
                                            </Grid>
                                            <Grid item xs={1.5}>
                                                <Typography variant="subtitle2" align="center"><strong>Snow Cols</strong></Typography>
                                            </Grid>
                                            <Grid item xs={1}>
                                                <Typography variant="subtitle2" align="center"><strong>Mapping</strong></Typography>
                                            </Grid>
                                        </Grid>
                                    </Paper>

                                    {getFilteredMappings().map((mapping: any, index: number) => {
                                        const hasIssue = mapping.match_status !== 'found_in_both' ||
                                            Object.keys(mapping.sql_columns || {}).length !== Object.keys(mapping.snowflake_columns || {}).length;
                                        const isExpanded = expandedRow === index;

                                        return (
                                            <Accordion
                                                key={index}
                                                expanded={isExpanded}
                                                onChange={() => setExpandedRow(isExpanded ? null : index)}
                                                sx={{
                                                    backgroundColor: hasIssue ? '#fff3e0' : 'inherit',
                                                    mb: 1,
                                                    '&:before': { display: 'none' }
                                                }}
                                            >
                                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                                    <Grid container spacing={2} alignItems="center">
                                                        <Grid item xs={3}>
                                                            <Box>
                                                                {mapping.schema && (
                                                                    <Chip label={mapping.schema} size="small" sx={{ mr: 0.5 }} />
                                                                )}
                                                                <strong>{mapping.sql_server_table || '-'}</strong>
                                                            </Box>
                                                        </Grid>
                                                        <Grid item xs={3}>
                                                            {mappingEditMode ? (
                                                                <FormControl size="small" fullWidth onClick={(e) => e.stopPropagation()}>
                                                                    <Select
                                                                        value={mapping.snowflake_table || ''}
                                                                        onChange={(e) => {
                                                                            e.stopPropagation();
                                                                            updateTableMapping(mapping.sql_server_table, e.target.value);
                                                                        }}
                                                                        displayEmpty
                                                                    >
                                                                        <MenuItem value="">
                                                                            <em>Select table...</em>
                                                                        </MenuItem>
                                                                        {availableSnowflakeTables.map((table) => (
                                                                            <MenuItem key={table} value={table}>{table}</MenuItem>
                                                                        ))}
                                                                    </Select>
                                                                </FormControl>
                                                            ) : (
                                                                <Box>
                                                                    {mapping.schema && (
                                                                        <Chip label={mapping.schema} size="small" sx={{ mr: 0.5 }} />
                                                                    )}
                                                                    <strong>{mapping.snowflake_table || '-'}</strong>
                                                                </Box>
                                                            )}
                                                        </Grid>
                                                        <Grid item xs={2}>
                                                            <Chip
                                                                label={mapping.match_status === 'found_in_both' ? 'Matched' :
                                                                       mapping.match_status === 'only_in_sql_server' ? 'SQL Only' :
                                                                       'Snow Only'}
                                                                size="small"
                                                                color={
                                                                    mapping.match_status === 'found_in_both' ? 'success' :
                                                                    mapping.match_status === 'only_in_sql_server' ? 'warning' : 'info'
                                                                }
                                                            />
                                                        </Grid>
                                                        <Grid item xs={1.5}>
                                                            <Typography variant="body2" align="center">
                                                                {Object.keys(mapping.sql_columns || {}).length} cols
                                                            </Typography>
                                                        </Grid>
                                                        <Grid item xs={1.5}>
                                                            <Typography variant="body2" align="center">
                                                                {Object.keys(mapping.snowflake_columns || {}).length} cols
                                                            </Typography>
                                                        </Grid>
                                                        <Grid item xs={1}>
                                                            <Chip
                                                                label={mapping.is_custom_mapping ? 'Manual' : 'Auto'}
                                                                size="small"
                                                                variant={mapping.is_custom_mapping ? 'filled' : 'outlined'}
                                                                color={mapping.is_custom_mapping ? 'secondary' : 'default'}
                                                            />
                                                        </Grid>
                                                    </Grid>
                                                </AccordionSummary>
                                                <AccordionDetails>
                                                    {/* Show message for unmapped tables */}
                                                    {mapping.match_status === 'only_in_sql_server' && !mapping.snowflake_table && (
                                                        <Alert severity="warning" sx={{ mb: 2 }}>
                                                            <strong>No Snowflake table mapped.</strong> Click "Edit Mappings" above and select a Snowflake table from the dropdown to create a mapping.
                                                        </Alert>
                                                    )}
                                                    {mapping.match_status === 'only_in_snowflake' && (
                                                        <Alert severity="info" sx={{ mb: 2 }}>
                                                            <strong>Snowflake-only table.</strong> This table exists in Snowflake but has no corresponding SQL Server table.
                                                        </Alert>
                                                    )}

                                                    {/* Column Mapping Stats */}
                                                    {mapping.column_mappings && mapping.column_mappings.mappings && mapping.column_mappings.mappings.length > 0 && (
                                                        <Box sx={{ mb: 2 }}>
                                                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                                                <Box sx={{ display: 'flex', gap: 1 }}>
                                                                    <Chip
                                                                        label={`${mapping.column_mappings.stats?.mapped || 0} Mapped`}
                                                                        color="success"
                                                                        size="small"
                                                                    />
                                                                    <Chip
                                                                        label={`${mapping.column_mappings.stats?.unmatched_source_count || 0} Unmapped`}
                                                                        color="warning"
                                                                        size="small"
                                                                    />
                                                                    <Chip
                                                                        label={`${mapping.column_mappings.stats?.mapping_percentage || 0}% Complete`}
                                                                        color="info"
                                                                        size="small"
                                                                    />
                                                                </Box>
                                                                <Box sx={{ display: 'flex', gap: 1 }}>
                                                                    <FormControl size="small" sx={{ minWidth: 150 }}>
                                                                        <Select
                                                                            value={columnFilter}
                                                                            onChange={(e) => setColumnFilter(e.target.value)}
                                                                        >
                                                                            <MenuItem value="all">All Columns</MenuItem>
                                                                            <MenuItem value="unmapped">Unmapped Only</MenuItem>
                                                                            <MenuItem value="low_confidence">Low Confidence</MenuItem>
                                                                        </Select>
                                                                    </FormControl>
                                                                    {columnEditingTable !== mapping.sql_server_table && (
                                                                        <Button
                                                                            variant="outlined"
                                                                            size="small"
                                                                            onClick={() => {
                                                                                setColumnEditingTable(mapping.sql_server_table);
                                                                                setEditedColumnMappings({
                                                                                    ...editedColumnMappings,
                                                                                    [mapping.sql_server_table]: [...mapping.column_mappings.mappings]
                                                                                });
                                                                            }}
                                                                        >
                                                                            Edit Column Mappings
                                                                        </Button>
                                                                    )}
                                                                    {columnEditingTable === mapping.sql_server_table && (
                                                                        <>
                                                                            <Button
                                                                                variant="outlined"
                                                                                size="small"
                                                                                onClick={() => {
                                                                                    setColumnEditingTable(null);
                                                                                    setEditedColumnMappings({
                                                                                        ...editedColumnMappings,
                                                                                        [mapping.sql_server_table]: undefined
                                                                                    });
                                                                                }}
                                                                            >
                                                                                Cancel
                                                                            </Button>
                                                                            <Button
                                                                                variant="contained"
                                                                                size="small"
                                                                                onClick={async () => {
                                                                                    // Save column mappings
                                                                                    try {
                                                                                        const response = await fetch('http://localhost:8000/database-mapping/column-mappings', {
                                                                                            method: 'PUT',
                                                                                            headers: { 'Content-Type': 'application/json' },
                                                                                            body: JSON.stringify({
                                                                                                sql_table: mapping.sql_server_table,
                                                                                                snow_table: mapping.snowflake_table,
                                                                                                column_mappings: editedColumnMappings[mapping.sql_server_table]
                                                                                            })
                                                                                        });
                                                                                        if (response.ok) {
                                                                                            setColumnEditingTable(null);
                                                                                            // Reload mappings
                                                                                            await loadExistingMappings();
                                                                                        }
                                                                                    } catch (err) {
                                                                                        console.error('Failed to save column mappings:', err);
                                                                                    }
                                                                                }}
                                                                            >
                                                                                Save
                                                                            </Button>
                                                                        </>
                                                                    )}
                                                                </Box>
                                                            </Box>

                                                            {/* Column Mappings Table */}
                                                            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                                                                <Table size="small" stickyHeader>
                                                                    <TableHead>
                                                                        <TableRow>
                                                                            <TableCell><strong>Source Column (SQL Server)</strong></TableCell>
                                                                            <TableCell><strong>Source Type</strong></TableCell>
                                                                            <TableCell><strong>→</strong></TableCell>
                                                                            <TableCell><strong>Target Column (Snowflake)</strong></TableCell>
                                                                            <TableCell><strong>Target Type</strong></TableCell>
                                                                            <TableCell align="center"><strong>Confidence</strong></TableCell>
                                                                            <TableCell align="center"><strong>Status</strong></TableCell>
                                                                        </TableRow>
                                                                    </TableHead>
                                                                    <TableBody>
                                                                        {(editedColumnMappings[mapping.sql_server_table] || mapping.column_mappings.mappings)
                                                                            ?.filter((cm: any) => {
                                                                                if (columnFilter === 'unmapped') return false;
                                                                                if (columnFilter === 'low_confidence') return cm.confidence < 70;
                                                                                return true;
                                                                            })
                                                                            .map((cm: any, cmIndex: number) => {
                                                                                // Get the current target column (use edited if available)
                                                                                const currentTarget = editedColumnMappings[mapping.sql_server_table]?.[cmIndex]?.target || cm.target;

                                                                                return (
                                                                                    <TableRow
                                                                                        key={cmIndex}
                                                                                        sx={{
                                                                                            backgroundColor: cm.confidence < 70 ? '#fff3e0' :
                                                                                                           cm.confidence < 90 ? '#fffde7' : 'inherit'
                                                                                        }}
                                                                                    >
                                                                                        <TableCell>{cm.source}</TableCell>
                                                                                        <TableCell>
                                                                                            <Chip label={mapping.sql_columns[cm.source]} size="small" variant="outlined" />
                                                                                        </TableCell>
                                                                                        <TableCell align="center">→</TableCell>
                                                                                        <TableCell>
                                                                                            {columnEditingTable === mapping.sql_server_table ? (
                                                                                                <FormControl size="small" fullWidth>
                                                                                                    <Select
                                                                                                        value={currentTarget}
                                                                                                        onChange={(e) => {
                                                                                                            // Update the edited column mappings state
                                                                                                            const currentTableMappings = editedColumnMappings[mapping.sql_server_table] || [...mapping.column_mappings.mappings];
                                                                                                            const updatedMappings = [...currentTableMappings];
                                                                                                            updatedMappings[cmIndex] = {
                                                                                                                ...updatedMappings[cmIndex],
                                                                                                                target: e.target.value,
                                                                                                                auto_mapped: false  // Mark as manually edited
                                                                                                            };

                                                                                                            setEditedColumnMappings({
                                                                                                                ...editedColumnMappings,
                                                                                                                [mapping.sql_server_table]: updatedMappings
                                                                                                            });
                                                                                                        }}
                                                                                                    >
                                                                                                        {Object.keys(mapping.snowflake_columns || {}).map((col) => (
                                                                                                            <MenuItem key={col} value={col}>{col}</MenuItem>
                                                                                                        ))}
                                                                                                    </Select>
                                                                                                </FormControl>
                                                                                            ) : (
                                                                                                currentTarget
                                                                                            )}
                                                                                        </TableCell>
                                                                                        <TableCell>
                                                                                            <Chip label={mapping.snowflake_columns[currentTarget]} size="small" variant="outlined" />
                                                                                        </TableCell>
                                                                                        <TableCell align="center">
                                                                                            <Chip
                                                                                                label={`${cm.confidence}%`}
                                                                                                size="small"
                                                                                                color={
                                                                                                    cm.confidence >= 90 ? 'success' :
                                                                                                    cm.confidence >= 70 ? 'warning' : 'error'
                                                                                                }
                                                                                            />
                                                                                        </TableCell>
                                                                                        <TableCell align="center">
                                                                                            <Chip
                                                                                                label={cm.auto_mapped ? 'Auto' : 'Manual'}
                                                                                                size="small"
                                                                                                variant={cm.auto_mapped ? 'outlined' : 'filled'}
                                                                                            />
                                                                                        </TableCell>
                                                                                    </TableRow>
                                                                                );
                                                                            })}
                                                                        {mapping.column_mappings.unmatched_source
                                                                            ?.filter(() => columnFilter === 'all' || columnFilter === 'unmapped')
                                                                            .map((col: string) => (
                                                                            <TableRow key={col} sx={{ backgroundColor: '#ffebee' }}>
                                                                                <TableCell>{col}</TableCell>
                                                                                <TableCell>
                                                                                    <Chip label={mapping.sql_columns[col]} size="small" variant="outlined" />
                                                                                </TableCell>
                                                                                <TableCell align="center">✗</TableCell>
                                                                                <TableCell>
                                                                                    <em style={{ color: '#999' }}>No mapping</em>
                                                                                </TableCell>
                                                                                <TableCell>-</TableCell>
                                                                                <TableCell align="center">
                                                                                    <Chip label="0%" size="small" color="error" />
                                                                                </TableCell>
                                                                                <TableCell align="center">
                                                                                    <Chip label="Unmapped" size="small" color="error" />
                                                                                </TableCell>
                                                                            </TableRow>
                                                                        ))}
                                                                    </TableBody>
                                                                </Table>
                                                            </TableContainer>
                                                        </Box>
                                                    )}
                                                </AccordionDetails>
                                            </Accordion>
                                        );
                                    })}
                                    {getFilteredMappings().length === 0 && (
                                        <Alert severity="info">
                                            No tables match the current filter
                                        </Alert>
                                    )}
                                </Box>

                                <Alert severity="info" sx={{ mt: 2 }}>
                                    <strong>Tip:</strong> Click any row to expand and view AI-generated column mappings with confidence scores.
                                    Use filters to find unmapped columns or low-confidence mappings. Color-coded rows highlight mapping quality:
                                    <strong style={{ color: '#4caf50' }}> Green</strong> = High confidence (≥90%),
                                    <strong style={{ color: '#ff9800' }}> Orange</strong> = Medium confidence (70-89%),
                                    <strong style={{ color: '#f44336' }}> Red</strong> = Low confidence or unmapped (&lt;70%).
                                </Alert>
                            </CardContent>
                        </Card>
                    </Grid>
                )}
            </Grid>

            {/* Relationship Inference Section */}
            {extractionResult && (
                <Box sx={{ mt: 3 }}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                <Typography variant="h6">
                                    Relationship Inference & ER Diagram
                                </Typography>
                                <Box>
                                    {!sqlRelationships && !snowRelationships && (
                                        <Button
                                            variant="contained"
                                            onClick={inferRelationships}
                                            disabled={inferring}
                                        >
                                            {inferring ? <CircularProgress size={20} /> : 'Infer Relationships (Both Databases)'}
                                        </Button>
                                    )}
                                    {(sqlRelationships || snowRelationships) && (
                                        <>
                                            {!relationshipEditMode && (
                                                <Button
                                                    variant="outlined"
                                                    onClick={() => setRelationshipEditMode(true)}
                                                    sx={{ mr: 1 }}
                                                >
                                                    Edit Relationships
                                                </Button>
                                            )}
                                            {relationshipEditMode && (
                                                <>
                                                    <Button
                                                        variant="contained"
                                                        color="primary"
                                                        onClick={addNewRelationship}
                                                        sx={{ mr: 1 }}
                                                    >
                                                        Add Relationship
                                                    </Button>
                                                    <Button
                                                        variant="outlined"
                                                        onClick={() => {
                                                            setRelationshipEditMode(false);
                                                            setEditedRelationships(inferredRelationships);
                                                        }}
                                                        sx={{ mr: 1 }}
                                                    >
                                                        Cancel
                                                    </Button>
                                                </>
                                            )}
                                            <Button
                                                variant="outlined"
                                                onClick={regenerateDiagram}
                                            >
                                                Regenerate Diagram
                                            </Button>
                                        </>
                                    )}
                                </Box>
                            </Box>

                            <Alert severity="info" sx={{ mb: 2 }}>
                                <strong>AI-Powered Relationship Detection:</strong> The system infers relationships for both SQL Server
                                and Snowflake from your extracted metadata. Use the selector below to switch between database views.
                            </Alert>

                            {/* Database Selection for Viewing */}
                            {(sqlRelationships || snowRelationships) && (
                                <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
                                    <FormControl sx={{ minWidth: 250 }}>
                                        <InputLabel>View Database</InputLabel>
                                        <Select
                                            value={selectedDatabase}
                                            label="View Database"
                                            onChange={(e) => {
                                                const newDb = e.target.value as 'sql' | 'snow';
                                                setSelectedDatabase(newDb);
                                                setEditedRelationships(
                                                    newDb === 'sql' ? sqlRelationships?.relationships : snowRelationships?.relationships
                                                );
                                            }}
                                        >
                                            <MenuItem value="sql">SQL Server</MenuItem>
                                            <MenuItem value="snow">Snowflake</MenuItem>
                                        </Select>
                                    </FormControl>
                                    <Chip
                                        label={`Showing ${selectedDatabase === 'sql' ? 'SQL Server' : 'Snowflake'} relationships`}
                                        color="primary"
                                        size="small"
                                    />
                                </Box>
                            )}

                            {/* Metrics */}
                            {relationshipMetrics && (
                                <Grid container spacing={2} sx={{ mb: 3 }}>
                                    <Grid item xs={12} md={3}>
                                        <Card variant="outlined">
                                            <CardContent>
                                                <Typography variant="h4" color="primary">
                                                    {relationshipMetrics.total_relationships}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    Total Relationships Found
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                    <Grid item xs={12} md={3}>
                                        <Card variant="outlined">
                                            <CardContent>
                                                <Typography variant="h4" color="success.main">
                                                    {relationshipMetrics.high_confidence}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    High Confidence (≥85%)
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                    <Grid item xs={12} md={3}>
                                        <Card variant="outlined">
                                            <CardContent>
                                                <Typography variant="h4" color="warning.main">
                                                    {relationshipMetrics.medium_confidence}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    Medium Confidence (65-85%)
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                    <Grid item xs={12} md={3}>
                                        <Card variant="outlined">
                                            <CardContent>
                                                <Typography variant="h4" color="error.main">
                                                    {relationshipMetrics.low_confidence}
                                                </Typography>
                                                <Typography variant="body2" color="text.secondary">
                                                    Low Confidence (&lt;65%)
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                </Grid>
                            )}

                            {/* Mermaid Diagram */}
                            {showDiagram && mermaidDiagram && (
                                <Box sx={{ mb: 3 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                                        <Typography variant="h6">
                                            Entity-Relationship Diagram
                                        </Typography>
                                        <Chip
                                            label={`${relationshipMetrics?.source_db_label || 'SQL Server'} Tables`}
                                            color="primary"
                                            size="small"
                                        />
                                    </Box>
                                    <Paper
                                        variant="outlined"
                                        sx={{
                                            p: 3,
                                            backgroundColor: '#f5f5f5',
                                            overflow: 'auto',
                                            maxHeight: 600
                                        }}
                                    >
                                        <Box
                                            id="mermaid-container"
                                            className="mermaid"
                                            sx={{ display: 'flex', justifyContent: 'center' }}
                                        >
                                            {/* Mermaid diagram will be rendered here by the useEffect hook */}
                                        </Box>
                                    </Paper>
                                    <Alert severity="info" sx={{ mt: 1 }}>
                                        <Typography variant="caption">
                                            <strong>Diagram Legend:</strong> Solid lines = High confidence, Dotted lines = Medium confidence, Weak lines = Low confidence
                                        </Typography>
                                    </Alert>
                                </Box>
                            )}

                            {/* Relationship List */}
                            {editedRelationships && editedRelationships.length > 0 && (
                                <Box>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                        <Typography variant="h6">
                                            Inferred Relationships ({editedRelationships.length})
                                        </Typography>
                                        <Box sx={{ display: 'flex', gap: 1 }}>
                                            <Chip
                                                label={`${editedRelationships.filter((r: any) => r.method !== 'manual' && r.method !== 'manual_override').length} Auto-inferred`}
                                                size="small"
                                                color="default"
                                                variant="outlined"
                                            />
                                            <Chip
                                                label={`${editedRelationships.filter((r: any) => r.method === 'manual_override').length} Overridden`}
                                                size="small"
                                                color="warning"
                                            />
                                            <Chip
                                                label={`${editedRelationships.filter((r: any) => r.method === 'manual').length} Manual`}
                                                size="small"
                                                color="secondary"
                                            />
                                        </Box>
                                    </Box>

                                    {relationshipEditMode && (
                                        <Alert severity="info" sx={{ mb: 2 }}>
                                            <Typography variant="body2">
                                                <strong>How to override:</strong> Select from dropdowns to change tables or columns.
                                                Column dropdowns populate based on the selected table.
                                                Changed relationships will be marked as "Overridden" (orange chip).
                                                Use "Regenerate Diagram" to update the visual after changes.
                                            </Typography>
                                        </Alert>
                                    )}

                                    <TableContainer component={Paper} variant="outlined">
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell><strong>Fact Table</strong></TableCell>
                                                    <TableCell><strong>FK Column</strong></TableCell>
                                                    <TableCell><strong>Dimension Table</strong></TableCell>
                                                    <TableCell><strong>Dim Column</strong></TableCell>
                                                    <TableCell><strong>Confidence</strong></TableCell>
                                                    <TableCell><strong>Method</strong></TableCell>
                                                    {relationshipEditMode && <TableCell><strong>Actions</strong></TableCell>}
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {editedRelationships.map((rel: any, index: number) => (
                                                    <TableRow
                                                        key={index}
                                                        sx={{
                                                            backgroundColor: rel.method === 'manual_override' ? 'warning.light' : 'inherit',
                                                            '&:hover': { backgroundColor: rel.method === 'manual_override' ? 'warning.main' : 'action.hover' }
                                                        }}
                                                    >
                                                        <TableCell>
                                                            {relationshipEditMode ? (
                                                                <Select
                                                                    value={rel.fact_table}
                                                                    onChange={(e) => updateRelationship(index, 'fact_table', e.target.value)}
                                                                    size="small"
                                                                    fullWidth
                                                                >
                                                                    {availableTables.map(table => (
                                                                        <MenuItem key={table} value={table}>{table}</MenuItem>
                                                                    ))}
                                                                </Select>
                                                            ) : (
                                                                rel.fact_table
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            {relationshipEditMode ? (
                                                                <Select
                                                                    value={rel.fk_column}
                                                                    onChange={(e) => updateRelationship(index, 'fk_column', e.target.value)}
                                                                    size="small"
                                                                    fullWidth
                                                                    displayEmpty
                                                                >
                                                                    {rel.fact_table && getColumnsForTable(rel.fact_table).length > 0 ? (
                                                                        getColumnsForTable(rel.fact_table).map(col => (
                                                                            <MenuItem key={col} value={col}>{col}</MenuItem>
                                                                        ))
                                                                    ) : (
                                                                        <MenuItem value={rel.fk_column || ''}>{rel.fk_column || 'Select fact table first'}</MenuItem>
                                                                    )}
                                                                </Select>
                                                            ) : (
                                                                <Chip label={rel.fk_column} size="small" />
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            {relationshipEditMode ? (
                                                                <Select
                                                                    value={rel.dim_table}
                                                                    onChange={(e) => updateRelationship(index, 'dim_table', e.target.value)}
                                                                    size="small"
                                                                    fullWidth
                                                                >
                                                                    {availableTables.map(table => (
                                                                        <MenuItem key={table} value={table}>{table}</MenuItem>
                                                                    ))}
                                                                </Select>
                                                            ) : (
                                                                rel.dim_table
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            {relationshipEditMode ? (
                                                                <Select
                                                                    value={rel.dim_column}
                                                                    onChange={(e) => updateRelationship(index, 'dim_column', e.target.value)}
                                                                    size="small"
                                                                    fullWidth
                                                                    displayEmpty
                                                                >
                                                                    {rel.dim_table && getColumnsForTable(rel.dim_table).length > 0 ? (
                                                                        getColumnsForTable(rel.dim_table).map(col => (
                                                                            <MenuItem key={col} value={col}>{col}</MenuItem>
                                                                        ))
                                                                    ) : (
                                                                        <MenuItem value={rel.dim_column || ''}>{rel.dim_column || 'Select dim table first'}</MenuItem>
                                                                    )}
                                                                </Select>
                                                            ) : (
                                                                <Chip label={rel.dim_column} size="small" />
                                                            )}
                                                        </TableCell>
                                                        <TableCell>
                                                            <Chip
                                                                label={`${rel.confidence} (${(rel.confidence_score * 100).toFixed(0)}%)`}
                                                                size="small"
                                                                color={
                                                                    rel.confidence === 'high' ? 'success' :
                                                                    rel.confidence === 'medium' ? 'warning' : 'error'
                                                                }
                                                            />
                                                        </TableCell>
                                                        <TableCell>
                                                            <Chip
                                                                label={
                                                                    rel.method === 'manual_override' ? 'Overridden' :
                                                                    rel.method === 'manual' ? 'Manual' :
                                                                    rel.method
                                                                }
                                                                size="small"
                                                                variant={rel.method === 'manual_override' ? 'filled' : 'outlined'}
                                                                color={
                                                                    rel.method === 'manual_override' ? 'warning' :
                                                                    rel.method === 'manual' ? 'secondary' :
                                                                    'default'
                                                                }
                                                            />
                                                        </TableCell>
                                                        {relationshipEditMode && (
                                                            <TableCell>
                                                                <IconButton
                                                                    size="small"
                                                                    color="error"
                                                                    onClick={() => removeRelationship(index)}
                                                                    title="Delete relationship"
                                                                >
                                                                    <DeleteIcon fontSize="small" />
                                                                </IconButton>
                                                            </TableCell>
                                                        )}
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
                                </Box>
                            )}

                            {inferredRelationships && inferredRelationships.length === 0 && (
                                <Alert severity="warning">
                                    No relationships detected. This usually means either:
                                    <ul>
                                        <li>No fact tables were identified (tables with multiple FK columns)</li>
                                        <li>Column naming doesn't follow FK patterns (e.g., customer_id, dim_1_id)</li>
                                        <li>No dimension tables were found</li>
                                    </ul>
                                </Alert>
                            )}
                        </CardContent>
                    </Card>
                </Box>
            )}

            {/* Information Box */}
            <Box sx={{ mt: 3 }}>
                <Alert severity="info">
                    <Typography variant="body2">
                        <strong>How it works:</strong> This feature extracts metadata from both SQL Server and Snowflake databases,
                        creates table mappings, and generates YAML configuration files that the Ombudsman Core engine uses for validations.
                        The generated files (tables.yaml and relationships.yaml) will be saved to the core's config directory.
                    </Typography>
                </Alert>
            </Box>
        </Box>
    );
}
