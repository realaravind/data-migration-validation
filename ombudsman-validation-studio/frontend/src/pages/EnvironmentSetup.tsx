import { useState } from 'react';
import { Box, Card, CardContent, Typography, TextField, Button } from '@mui/material';

export default function EnvironmentSetup() {
    const [sourceDb, setSourceDb] = useState('');
    const [targetDb, setTargetDb] = useState('');

    const saveConfig = async () => {
        await fetch('/environment/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sourceDb, targetDb })
        });
        alert('Configuration saved');
    };

    return (
        <Box>
            <Typography variant="h4" mb={3}>
                Environment Setup
            </Typography>

            <Card>
                <CardContent>
                    <Typography variant="h6" mb={2}>
                        Database Configuration
                    </Typography>

                    <TextField
                        fullWidth
                        label="Source Database Connection"
                        value={sourceDb}
                        onChange={(e) => setSourceDb(e.target.value)}
                        sx={{ mb: 2 }}
                    />

                    <TextField
                        fullWidth
                        label="Target Database Connection"
                        value={targetDb}
                        onChange={(e) => setTargetDb(e.target.value)}
                        sx={{ mb: 2 }}
                    />

                    <Button variant="contained" onClick={saveConfig}>
                        Save Configuration
                    </Button>
                </CardContent>
            </Card>
        </Box>
    );
}
