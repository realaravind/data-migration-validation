import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  InputAdornment,
  IconButton,
  Paper,
  Divider,
  Grid,
  Snackbar
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Lock,
  Logout,
  Person,
  Email,
  Badge,
  Home
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

export default function UserProfile() {
  const navigate = useNavigate();
  const { user, logout, token } = useAuth();

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const handlePasswordChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setPasswordForm({ ...passwordForm, [field]: e.target.value });
  };

  const validatePasswordForm = (): string | null => {
    if (!passwordForm.currentPassword) {
      return 'Current password is required';
    }
    if (passwordForm.newPassword.length < 8) {
      return 'New password must be at least 8 characters long';
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      return 'New passwords do not match';
    }
    return null;
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    const validationError = validatePasswordForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(__API_URL__ + '/auth/me/password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to change password');
      }

      setSuccessMessage('Password changed successfully!');
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } catch (err: any) {
      setError(err.message || 'Failed to change password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  if (!user) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">
          User not found. Please log in again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper
        elevation={10}
        sx={{
          borderRadius: 3,
          overflow: 'hidden'
        }}
      >
        <Box
          sx={{
            background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
            py: 2.5,
            px: 3,
            textAlign: 'center'
          }}
        >
          <Typography variant="h5" sx={{ color: 'white', fontWeight: 'bold', mb: 0.5 }}>
            User Profile
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.9)' }}>
            Manage your account settings
          </Typography>
        </Box>

          <CardContent sx={{ p: 4 }}>
            {/* User Information Section */}
            <Card variant="outlined" sx={{ mb: 4 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                  Account Information
                </Typography>

                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Person sx={{ color: 'primary.main' }} />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Username
                        </Typography>
                        <Typography variant="body1" fontWeight="medium">
                          {user.username}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Email sx={{ color: 'primary.main' }} />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Email
                        </Typography>
                        <Typography variant="body1" fontWeight="medium">
                          {user.email}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Badge sx={{ color: 'primary.main' }} />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Full Name
                        </Typography>
                        <Typography variant="body1" fontWeight="medium">
                          {user.full_name}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Lock sx={{ color: 'primary.main' }} />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Role
                        </Typography>
                        <Typography variant="body1" fontWeight="medium" sx={{ textTransform: 'capitalize' }}>
                          {user.role}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Change Password Section */}
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
                  Change Password
                </Typography>

                {error && (
                  <Alert severity="error" sx={{ mb: 3 }}>
                    {error}
                  </Alert>
                )}

                <form onSubmit={handlePasswordSubmit}>
                  <TextField
                    fullWidth
                    label="Current Password"
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={passwordForm.currentPassword}
                    onChange={handlePasswordChange('currentPassword')}
                    margin="normal"
                    required
                    variant="outlined"
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton
                            onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                            edge="end"
                          >
                            {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        </InputAdornment>
                      )
                    }}
                  />

                  <TextField
                    fullWidth
                    label="New Password"
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordForm.newPassword}
                    onChange={handlePasswordChange('newPassword')}
                    margin="normal"
                    required
                    variant="outlined"
                    helperText="Minimum 8 characters"
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton
                            onClick={() => setShowNewPassword(!showNewPassword)}
                            edge="end"
                          >
                            {showNewPassword ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        </InputAdornment>
                      )
                    }}
                  />

                  <TextField
                    fullWidth
                    label="Confirm New Password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={passwordForm.confirmPassword}
                    onChange={handlePasswordChange('confirmPassword')}
                    margin="normal"
                    required
                    variant="outlined"
                    error={passwordForm.confirmPassword !== '' && passwordForm.newPassword !== passwordForm.confirmPassword}
                    helperText={
                      passwordForm.confirmPassword !== '' && passwordForm.newPassword !== passwordForm.confirmPassword
                        ? 'Passwords do not match'
                        : ''
                    }
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            edge="end"
                          >
                            {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        </InputAdornment>
                      )
                    }}
                  />

                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    size="large"
                    disabled={loading}
                    startIcon={<Lock />}
                    sx={{
                      mt: 3,
                      py: 1.5,
                      background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
                      }
                    }}
                  >
                    {loading ? 'Changing Password...' : 'Change Password'}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Divider sx={{ my: 3 }} />

            {/* Navigation and Logout Section */}
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
              <Button
                variant="outlined"
                color="primary"
                size="large"
                startIcon={<Home />}
                onClick={() => navigate('/')}
                sx={{ py: 1.5, px: 4 }}
              >
                Back to Home
              </Button>
              <Button
                variant="outlined"
                color="error"
                size="large"
                startIcon={<Logout />}
                onClick={handleLogout}
                sx={{ py: 1.5, px: 4 }}
              >
                Logout
              </Button>
            </Box>
          </CardContent>
        </Paper>

        {/* Success Snackbar */}
        <Snackbar
          open={!!successMessage}
          autoHideDuration={6000}
          onClose={() => setSuccessMessage('')}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={() => setSuccessMessage('')} severity="success" sx={{ width: '100%' }}>
            {successMessage}
          </Alert>
        </Snackbar>
      </Container>
  );
}
