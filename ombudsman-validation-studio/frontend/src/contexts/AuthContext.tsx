import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string, fullName: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load token and user from localStorage on mount
  useEffect(() => {
    const loadAuth = async () => {
      const savedToken = localStorage.getItem('auth_token');

      if (savedToken) {
        setToken(savedToken);
        try {
          // Verify token and get user info
          const response = await fetch(__API_URL__ + '/auth/me', {
            headers: {
              'Authorization': `Bearer ${savedToken}`
            }
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token invalid, clear it
            localStorage.removeItem('auth_token');
            setToken(null);
          }
        } catch (error) {
          console.error('Error loading user:', error);
          localStorage.removeItem('auth_token');
          setToken(null);
        }
      }

      setIsLoading(false);
    };

    loadAuth();
  }, []);

  const login = async (username: string, password: string) => {
    console.log('[AuthContext] Login attempt started for username:', username);

    try {
      console.log(`[AuthContext] Sending POST request to ${__API_URL__}/auth/login`);

      const response = await fetch(__API_URL__ + '/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password })
      });

      console.log('[AuthContext] Response received, status:', response.status);

      if (!response.ok) {
        const error = await response.json();
        console.error('[AuthContext] Login failed with error:', error);
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      console.log('[AuthContext] Login successful, received token');
      const accessToken = data.access_token;

      // Store token
      localStorage.setItem('auth_token', accessToken);
      setToken(accessToken);
      console.log('[AuthContext] Token stored in localStorage');

      // Get user info
      console.log('[AuthContext] Fetching user info from /auth/me');
      const userResponse = await fetch(__API_URL__ + '/auth/me', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        console.log('[AuthContext] User data received:', userData.username);
        setUser(userData);
      } else {
        console.error('[AuthContext] Failed to fetch user info, status:', userResponse.status);
      }

      console.log('[AuthContext] Login process completed successfully');
    } catch (error) {
      console.error('[AuthContext] Login error caught:', error);
      console.error('[AuthContext] Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      });
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  };

  const register = async (username: string, email: string, password: string, fullName: string) => {
    try {
      const response = await fetch(__API_URL__ + '/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
          full_name: fullName
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      // Auto-login after registration
      await login(username, password);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    register
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
