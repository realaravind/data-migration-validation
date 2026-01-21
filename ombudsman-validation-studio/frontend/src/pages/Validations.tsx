import { useState } from 'react';
import { Box, Card, CardContent, Typography, Button, List, ListItem, ListItemText } from '@mui/material';

interface ValidationsProps {
    currentProject?: any;
}

export default function Validations(_props: ValidationsProps) {
    const [validations, setValidations] = useState<any[]>([]);

    const runValidations = async () => {
        const res = await fetch('/validations/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        setValidations(data.results || []);
    };

    return (
        <Box>
            <Typography variant="h4" mb={3}>
                Validations
            </Typography>

            <Card>
                <CardContent>
                    <Typography variant="h6" mb={2}>
                        Run Validation Checks
                    </Typography>

                    <Button variant="contained" onClick={runValidations}>
                        Run All Validations
                    </Button>

                    {validations.length > 0 && (
                        <List sx={{ mt: 3 }}>
                            {validations.map((v, idx) => (
                                <ListItem key={idx}>
                                    <ListItemText
                                        primary={v.name}
                                        secondary={`Status: ${v.status} - ${v.message}`}
                                    />
                                </ListItem>
                            ))}
                        </List>
                    )}
                </CardContent>
            </Card>
        </Box>
    );
}
