import { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Box,
    Typography,
    Checkbox,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Chip,
    Alert,
    CircularProgress,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Paper
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

interface QuerySuggestion {
    name: string;
    category: string;
    priority: string;
    comparison_type: string;
    sql_query: string;
    snow_query: string;
    description?: string;
    tolerance?: number;
    limit?: number;
}

interface QuerySuggestionsProps {
    open: boolean;
    onClose: () => void;
    onSelectQueries: (queries: QuerySuggestion[]) => void;
    selectedPipeline?: any;  // Optional: to extract fact table context
}

export default function QuerySuggestions({ open, onClose, onSelectQueries, selectedPipeline }: QuerySuggestionsProps) {
    const [suggestions, setSuggestions] = useState<QuerySuggestion[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedQueries, setSelectedQueries] = useState<Set<string>>(new Set());
    const [categorizedSuggestions, setCategorizedSuggestions] = useState<{[key: string]: QuerySuggestion[]}>({});

    useEffect(() => {
        if (open) {
            loadSuggestions();
        }
    }, [open]);

    const loadSuggestions = async () => {
        setLoading(true);
        setError(null);

        try {
            // Extract fact table from pipeline name or detect from metadata
            let factTable = null;
            if (selectedPipeline?.pipeline_name) {
                // Try to extract from pipeline name (e.g., "validate_fact_sales" -> "fact_sales")
                const match = selectedPipeline.pipeline_name.match(/fact[_\s](\w+)/i);
                if (match) {
                    factTable = `FACT.fact_${match[1].toLowerCase()}`;
                }
            }

            const response = await fetch('http://localhost:8000/custom-queries/intelligent-suggest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fact_table: factTable
                })
            });
            const data = await response.json();

            if (data.status === 'success') {
                // Map backend field names to frontend format
                const mappedSuggestions = (data.all_suggestions || []).map((q: any) => ({
                    ...q,
                    sql_query: q.sql_server_query || q.sql_query,
                    snow_query: q.snowflake_query || q.snow_query,
                    comparison_type: q.comparison_type || 'aggregation'
                }));

                setSuggestions(mappedSuggestions);

                // Also map categorized suggestions
                const mappedCategorized: {[key: string]: QuerySuggestion[]} = {};
                Object.keys(data.suggestions_by_category || {}).forEach(category => {
                    mappedCategorized[category] = (data.suggestions_by_category[category] || []).map((q: any) => ({
                        ...q,
                        sql_query: q.sql_server_query || q.sql_query,
                        snow_query: q.snowflake_query || q.snow_query,
                        comparison_type: q.comparison_type || 'aggregation'
                    }));
                });
                setCategorizedSuggestions(mappedCategorized);

                // Auto-select HIGH priority queries
                const highPriorityQueries = mappedSuggestions
                    .filter((q: QuerySuggestion) => q.priority === 'HIGH')
                    .map((q: QuerySuggestion) => q.name);
                setSelectedQueries(new Set(highPriorityQueries));
            } else {
                setError(data.message || 'Failed to generate suggestions');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load suggestions');
        } finally {
            setLoading(false);
        }
    };

    const handleToggleQuery = (queryName: string) => {
        const newSelected = new Set(selectedQueries);
        if (newSelected.has(queryName)) {
            newSelected.delete(queryName);
        } else {
            newSelected.add(queryName);
        }
        setSelectedQueries(newSelected);
    };

    const handleSelectAll = () => {
        setSelectedQueries(new Set(suggestions.map(q => q.name)));
    };

    const handleSelectNone = () => {
        setSelectedQueries(new Set());
    };

    const handleSelectHighPriority = () => {
        const highPriority = suggestions
            .filter(q => q.priority === 'HIGH')
            .map(q => q.name);
        setSelectedQueries(new Set(highPriority));
    };

    const handleAddToValidations = () => {
        const selected = suggestions.filter(q => selectedQueries.has(q.name));
        onSelectQueries(selected);
        onClose();
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'HIGH': return 'error';
            case 'MEDIUM': return 'warning';
            case 'LOW': return 'info';
            default: return 'default';
        }
    };

    const getCategoryIcon = (category: string) => {
        return '🧠';
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: { maxHeight: '90vh' }
            }}
        >
            <DialogTitle>
                <Box display="flex" alignItems="center" gap={1}>
                    <AutoAwesomeIcon color="primary" />
                    <Typography variant="h6">
                        Intelligent Query Suggestions
                    </Typography>
                </Box>
                <Typography variant="caption" color="textSecondary">
                    Based on your database metadata and table relationships
                </Typography>
            </DialogTitle>

            <DialogContent dividers>
                {loading && (
                    <Box display="flex" justifyContent="center" p={4}>
                        <CircularProgress />
                    </Box>
                )}

                {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                        <br />
                        <Typography variant="caption">
                            Make sure you've run metadata extraction first.
                        </Typography>
                    </Alert>
                )}

                {!loading && !error && suggestions.length === 0 && (
                    <Alert severity="info">
                        No metadata found. Please extract metadata first from the Metadata Extraction page.
                    </Alert>
                )}

                {!loading && !error && suggestions.length > 0 && (
                    <>
                        {/* Summary */}
                        <Paper sx={{ p: 2, mb: 2, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                            <Typography variant="body1" fontWeight="bold">
                                ✨ {suggestions.length} Intelligent Queries Generated
                            </Typography>
                            <Typography variant="body2">
                                {selectedQueries.size} selected • Ready to add to your validations
                            </Typography>
                        </Paper>

                        {/* Quick Actions */}
                        <Box mb={2} display="flex" gap={1} flexWrap="wrap">
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={handleSelectAll}
                            >
                                Select All ({suggestions.length})
                            </Button>
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={handleSelectHighPriority}
                            >
                                Select HIGH Priority Only
                            </Button>
                            <Button
                                size="small"
                                variant="outlined"
                                onClick={handleSelectNone}
                            >
                                Clear Selection
                            </Button>
                        </Box>

                        {/* Queries by Category */}
                        {Object.entries(categorizedSuggestions).map(([category, queries]) => (
                            <Accordion key={category} defaultExpanded={category === 'Basic Validation' || category === 'Metric Validation'}>
                                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                    <Box display="flex" alignItems="center" gap={1} width="100%">
                                        <Typography fontWeight="bold">
                                            {getCategoryIcon(category)} {category}
                                        </Typography>
                                        <Chip
                                            label={`${queries.length} queries`}
                                            size="small"
                                            color="primary"
                                        />
                                        <Box ml="auto">
                                            <Chip
                                                label={`${queries.filter(q => selectedQueries.has(q.name)).length} selected`}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Box>
                                    </Box>
                                </AccordionSummary>
                                <AccordionDetails>
                                    <List dense>
                                        {queries.map((query) => (
                                            <ListItem
                                                key={query.name}
                                                secondaryAction={
                                                    <Checkbox
                                                        edge="end"
                                                        checked={selectedQueries.has(query.name)}
                                                        onChange={() => handleToggleQuery(query.name)}
                                                    />
                                                }
                                                sx={{
                                                    bgcolor: selectedQueries.has(query.name) ? 'action.selected' : 'inherit',
                                                    borderRadius: 1,
                                                    mb: 0.5
                                                }}
                                            >
                                                <ListItemIcon sx={{ minWidth: 40 }}>
                                                    <Checkbox
                                                        edge="start"
                                                        checked={selectedQueries.has(query.name)}
                                                        onChange={() => handleToggleQuery(query.name)}
                                                    />
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={
                                                        <Box display="flex" alignItems="center" gap={1}>
                                                            <Typography variant="body2" fontWeight="medium">
                                                                {query.name}
                                                            </Typography>
                                                            <Chip
                                                                label={query.priority}
                                                                size="small"
                                                                color={getPriorityColor(query.priority)}
                                                                sx={{ height: 20 }}
                                                            />
                                                            <Chip
                                                                label={query.comparison_type}
                                                                size="small"
                                                                variant="outlined"
                                                                sx={{ height: 20 }}
                                                            />
                                                        </Box>
                                                    }
                                                    secondary={
                                                        <Typography variant="caption" color="textSecondary">
                                                            {query.description}
                                                        </Typography>
                                                    }
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </AccordionDetails>
                            </Accordion>
                        ))}
                    </>
                )}
            </DialogContent>

            <DialogActions>
                <Button onClick={onClose}>
                    Cancel
                </Button>
                <Button
                    variant="contained"
                    onClick={handleAddToValidations}
                    disabled={selectedQueries.size === 0}
                    startIcon={<AutoAwesomeIcon />}
                >
                    Add {selectedQueries.size} Queries to Validations
                </Button>
            </DialogActions>
        </Dialog>
    );
}
