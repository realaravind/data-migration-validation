import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Box,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  InputAdornment,
  IconButton,
  Paper,
  Divider
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
  PersonAdd
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const from = (location.state as any)?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('[Login] Form submitted, username:', username);
    setError('');
    setLoading(true);

    try {
      console.log('[Login] Calling login function...');
      await login(username, password);
      console.log('[Login] Login successful, navigating to:', from);
      navigate(from, { replace: true });
    } catch (err: any) {
      console.error('[Login] Login failed:', err);
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
      console.log('[Login] Login process finished, loading state reset');
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
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
            py: 1.5,
            px: 3,
            textAlign: 'center'
          }}
        >
          <Typography variant="h5" sx={{ color: 'white', fontWeight: 'bold', mb: 0.5 }}>
            Ombudsman.AI
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)' }}>
            Data Migration Validation Platform
          </Typography>
        </Box>

          <CardContent sx={{ p: 2.5, pb: 3 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                margin="dense"
                required
                autoFocus
                autoComplete="username"
                variant="outlined"
                size="small"
              />

              <TextField
                fullWidth
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                margin="dense"
                required
                autoComplete="current-password"
                variant="outlined"
                size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                disabled={loading}
                startIcon={<LoginIcon />}
                sx={{
                  mt: 1.5,
                  mb: 1,
                  py: 1.2,
                  background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
                  }
                }}
              >
                {loading ? 'Signing In...' : 'Sign In'}
              </Button>

              <Divider sx={{ my: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  OR
                </Typography>
              </Divider>

              <Button
                fullWidth
                variant="outlined"
                component={Link}
                to="/register"
                startIcon={<PersonAdd />}
                sx={{ py: 1 }}
              >
                Create New Account
              </Button>
            </form>
          </CardContent>
        </Paper>
    </Container>
  );
}
