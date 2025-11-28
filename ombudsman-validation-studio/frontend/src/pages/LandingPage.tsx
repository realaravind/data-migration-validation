
import { Box, Typography, Card, CardContent, Grid } from '@mui/material';

export default function LandingPage() {
    return (
        <Box>
            <Typography variant="h3" gutterBottom>
                Welcome to Ombudsman Validation Studio
            </Typography>
            <Typography variant="body1" paragraph>
                A comprehensive data migration validation platform
            </Typography>

            <Grid container spacing={3} sx={{ mt: 4 }}>
                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="h5" gutterBottom>
                                Pipeline Editor
                            </Typography>
                            <Typography variant="body2">
                                Create and edit YAML-based validation pipelines
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="h5" gutterBottom>
                                Validation Dashboard
                            </Typography>
                            <Typography variant="body2">
                                Monitor validation results and execution status
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Card>
                        <CardContent>
                            <Typography variant="h5" gutterBottom>
                                Rules Management
                            </Typography>
                            <Typography variant="body2">
                                Define and manage validation rules
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}
