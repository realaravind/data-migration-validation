import { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    Grid,
    Chip,
    CircularProgress,
    Alert,
    Divider
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import LockResetIcon from '@mui/icons-material/LockReset';

export default function ConnectionStatus() {
    const [loading, setLoading] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState<any>(null);
    const [testResults, setTestResults] = useState<any>({});

    useEffect(() => {
        fetchConnectionStatus();

        // Listen for OAuth success from popup window
        const handleOAuthMessage = (event: MessageEvent) => {
            if (event.data?.type === 'snowflake_oauth_success') {
                console.log('[ConnectionStatus] OAuth success received, refreshing');
                fetchConnectionStatus();
                setTestResults({});  // Clear old test results
            }
        };
        window.addEventListener('message', handleOAuthMessage);
        return () => window.removeEventListener('message', handleOAuthMessage);
    }, []);

    const handleReauthenticate = () => {
        // Open OAuth in popup window
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        window.open(
            __API_URL__ + '/oauth/snowflake/authorize',
            'oauth_popup',
            `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
        );
    };

    // Check if Snowflake error is OAuth-related
    const isOAuthError = (message: string) => {
        if (!message) return false;
        const oauthPatterns = ['OAuth', 'token', 'refresh', 'expired', '400', 'authentication'];
        return oauthPatterns.some(pattern => message.toLowerCase().includes(pattern.toLowerCase()));
    };

    const fetchConnectionStatus = async () => {
        setLoading(true);
        try {
            const response = await fetch(__API_URL__ + '/connections/status');
            const data = await response.json();
            setConnectionStatus(data.connections);
        } catch (error) {
            console.error('Failed to fetch connection status:', error);
        }
        setLoading(false);
    };

    const testSqlServer = async () => {
        setLoading(true);
        try {
            const response = await fetch(__API_URL__ + '/connections/sqlserver', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ use_env: true })
            });
            const result = await response.json();
            setTestResults({ ...testResults, sqlserver: result });
            await fetchConnectionStatus();
        } catch (error) {
            setTestResults({ ...testResults, sqlserver: { status: 'error', message: String(error) } });
        }
        setLoading(false);
    };

    const testSnowflake = async () => {
        setLoading(true);
        try {
            const response = await fetch(__API_URL__ + '/connections/snowflake', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ use_env: true })
            });
            const result = await response.json();
            setTestResults({ ...testResults, snowflake: result });
            await fetchConnectionStatus();
        } catch (error) {
            setTestResults({ ...testResults, snowflake: { status: 'error', message: String(error) } });
        }
        setLoading(false);
    };

    const getStatusIcon = (status: string) => {
        if (status === 'success') return <CheckCircleIcon color="success" />;
        if (status === 'error') return <ErrorIcon color="error" />;
        return <WarningIcon color="warning" />;
    };

    const getStatusColor = (status: string) => {
        if (status === 'success') return 'success';
        if (status === 'error') return 'error';
        return 'warning';
    };

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Database Connection Testing
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
                Test and monitor your SQL Server and Snowflake database connections
            </Typography>

            {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                    <CircularProgress />
                </Box>
            )}

            <Grid container spacing={3}>
                {/* SQL Server Connection */}
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                {connectionStatus?.sqlserver && getStatusIcon(connectionStatus.sqlserver.status)}
                                <Typography variant="h5" sx={{ ml: 1 }}>
                                    SQL Server
                                </Typography>
                            </Box>

                            {connectionStatus?.sqlserver && (
                                <>
                                    <Chip
                                        label={connectionStatus.sqlserver.configured ? 'Configured' : 'Not Configured'}
                                        color={connectionStatus.sqlserver.configured ? 'success' : 'warning'}
                                        size="small"
                                        sx={{ mb: 2 }}
                                    />

                                    <Typography variant="body2" color="text.secondary">
                                        <strong>Host:</strong> {connectionStatus.sqlserver.host}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        <strong>Port:</strong> {connectionStatus.sqlserver.port}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                        <strong>Database:</strong> {connectionStatus.sqlserver.database}
                                    </Typography>

                                    {connectionStatus.sqlserver.message && (
                                        <Alert severity={getStatusColor(connectionStatus.sqlserver.status)} sx={{ mb: 2 }}>
                                            {connectionStatus.sqlserver.message}
                                        </Alert>
                                    )}
                                </>
                            )}

                            <Button
                                variant="contained"
                                onClick={testSqlServer}
                                disabled={loading}
                                fullWidth
                            >
                                Test SQL Server Connection
                            </Button>

                            {testResults.sqlserver && (
                                <Box sx={{ mt: 2 }}>
                                    <Divider sx={{ my: 2 }} />
                                    <Typography variant="subtitle2" gutterBottom>
                                        Test Result:
                                    </Typography>
                                    <Alert severity={getStatusColor(testResults.sqlserver.status)}>
                                        {testResults.sqlserver.message}
                                    </Alert>
                                    {testResults.sqlserver.server_version && (
                                        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                                            Server Version: {testResults.sqlserver.server_version.substring(0, 100)}...
                                        </Typography>
                                    )}
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Snowflake Connection */}
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                {connectionStatus?.snowflake && getStatusIcon(connectionStatus.snowflake.status)}
                                <Typography variant="h5" sx={{ ml: 1 }}>
                                    Snowflake
                                </Typography>
                            </Box>

                            {connectionStatus?.snowflake && (
                                <>
                                    <Chip
                                        label={connectionStatus.snowflake.configured ? 'Configured' : 'Not Configured'}
                                        color={connectionStatus.snowflake.configured ? 'success' : 'warning'}
                                        size="small"
                                        sx={{ mb: 2 }}
                                    />

                                    <Typography variant="body2" color="text.secondary">
                                        <strong>Account:</strong> {connectionStatus.snowflake.account}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        <strong>Database:</strong> {connectionStatus.snowflake.database}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                        <strong>Schema:</strong> {connectionStatus.snowflake.schema}
                                    </Typography>

                                    {connectionStatus.snowflake.message && (
                                        <Alert severity={getStatusColor(connectionStatus.snowflake.status)} sx={{ mb: 2 }}>
                                            {connectionStatus.snowflake.message}
                                        </Alert>
                                    )}
                                </>
                            )}

                            <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
                                <Button
                                    variant="contained"
                                    onClick={testSnowflake}
                                    disabled={loading}
                                    fullWidth
                                >
                                    Test Snowflake Connection
                                </Button>

                                {/* Show Re-authenticate button if OAuth error or connection failed */}
                                {connectionStatus?.snowflake?.status === 'error' &&
                                 isOAuthError(connectionStatus.snowflake.message) && (
                                    <Button
                                        variant="outlined"
                                        color="warning"
                                        onClick={handleReauthenticate}
                                        disabled={loading}
                                        fullWidth
                                        startIcon={<LockResetIcon />}
                                    >
                                        Re-authenticate with Snowflake
                                    </Button>
                                )}
                            </Box>

                            {testResults.snowflake && (
                                <Box sx={{ mt: 2 }}>
                                    <Divider sx={{ my: 2 }} />
                                    <Typography variant="subtitle2" gutterBottom>
                                        Test Result:
                                    </Typography>
                                    <Alert severity={getStatusColor(testResults.snowflake.status)}>
                                        {testResults.snowflake.message}
                                    </Alert>
                                    {testResults.snowflake.server_version && (
                                        <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                                            Snowflake Version: {testResults.snowflake.server_version}
                                        </Typography>
                                    )}
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Refresh Button */}
            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
                <Button
                    variant="outlined"
                    onClick={fetchConnectionStatus}
                    disabled={loading}
                >
                    Refresh Status
                </Button>
            </Box>
        </Box>
    );
}
