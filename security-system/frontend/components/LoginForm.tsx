/**
 * Comprehensive login form component with multi-factor authentication support.
 * Supports local authentication, OAuth2 providers, and SAML SSO.
 */

import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Alert, 
  Divider, 
  IconButton,
  InputAdornment,
  Tabs,
  Tab,
  CircularProgress,
  Link,
  Checkbox,
  FormControlLabel
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Google as GoogleIcon,
  GitHub as GitHubIcon,
  Microsoft as MicrosoftIcon,
  Security as SecurityIcon,
  Email as EmailIcon,
  Lock as LockIcon
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { authService } from '../services/authService';

interface LoginFormProps {
  onLoginSuccess: (user: any) => void;
  onLoginError: (error: string) => void;
  redirectUrl?: string;
  enableOAuth2?: boolean;
  enableSAML?: boolean;
  enableRememberMe?: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`login-tabpanel-${index}`}
      aria-labelledby={`login-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const loginValidationSchema = Yup.object({
  email: Yup.string()
    .email('Invalid email address')
    .required('Email is required'),
  password: Yup.string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
  rememberMe: Yup.boolean()
});

const mfaValidationSchema = Yup.object({
  mfaCode: Yup.string()
    .matches(/^[0-9]{6}$/, 'MFA code must be 6 digits')
    .required('MFA code is required')
});

export const LoginForm: React.FC<LoginFormProps> = ({
  onLoginSuccess,
  onLoginError,
  redirectUrl,
  enableOAuth2 = true,
  enableSAML = true,
  enableRememberMe = true
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaToken, setMfaToken] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Login form
  const loginFormik = useFormik({
    initialValues: {
      email: '',
      password: '',
      rememberMe: false
    },
    validationSchema: loginValidationSchema,
    onSubmit: async (values) => {
      setLoading(true);
      setError('');
      
      try {
        const response = await authService.login(
          values.email,
          values.password,
          values.rememberMe
        );
        
        if (response.mfaRequired) {
          setMfaRequired(true);
          setMfaToken(response.mfaToken);
          setSuccess('Please enter your MFA code to complete login');
        } else {
          onLoginSuccess(response.user);
        }
      } catch (err: any) {
        setError(err.message || 'Login failed');
        onLoginError(err.message || 'Login failed');
      } finally {
        setLoading(false);
      }
    }
  });

  // MFA form
  const mfaFormik = useFormik({
    initialValues: {
      mfaCode: ''
    },
    validationSchema: mfaValidationSchema,
    onSubmit: async (values) => {
      setLoading(true);
      setError('');
      
      try {
        const response = await authService.verifyMFA(mfaToken, values.mfaCode);
        onLoginSuccess(response.user);
      } catch (err: any) {
        setError(err.message || 'MFA verification failed');
        onLoginError(err.message || 'MFA verification failed');
      } finally {
        setLoading(false);
      }
    }
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError('');
    setSuccess('');
  };

  const handleOAuth2Login = async (provider: string) => {
    setLoading(true);
    setError('');
    
    try {
      const authUrl = await authService.getOAuth2AuthUrl(provider, redirectUrl);
      window.location.href = authUrl;
    } catch (err: any) {
      setError(err.message || `${provider} login failed`);
      onLoginError(err.message || `${provider} login failed`);
      setLoading(false);
    }
  };

  const handleSAMLLogin = async (provider: string) => {
    setLoading(true);
    setError('');
    
    try {
      const authUrl = await authService.getSAMLAuthUrl(provider, redirectUrl);
      window.location.href = authUrl;
    } catch (err: any) {
      setError(err.message || 'SAML login failed');
      onLoginError(err.message || 'SAML login failed');
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    // Navigate to forgot password page
    window.location.href = '/auth/forgot-password';
  };

  const handleBackToLogin = () => {
    setMfaRequired(false);
    setMfaToken('');
    setError('');
    setSuccess('');
    mfaFormik.resetForm();
  };

  if (mfaRequired) {
    return (
      <Box
        component="form"
        onSubmit={mfaFormik.handleSubmit}
        sx={{
          maxWidth: 400,
          mx: 'auto',
          p: 3,
          border: 1,
          borderColor: 'divider',
          borderRadius: 2,
          boxShadow: 3
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <SecurityIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="h5" component="h1" gutterBottom>
            Multi-Factor Authentication
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter the 6-digit code from your authenticator app
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <TextField
          fullWidth
          id="mfaCode"
          name="mfaCode"
          label="MFA Code"
          type="text"
          inputProps={{ maxLength: 6, pattern: '[0-9]*' }}
          value={mfaFormik.values.mfaCode}
          onChange={mfaFormik.handleChange}
          onBlur={mfaFormik.handleBlur}
          error={mfaFormik.touched.mfaCode && Boolean(mfaFormik.errors.mfaCode)}
          helperText={mfaFormik.touched.mfaCode && mfaFormik.errors.mfaCode}
          sx={{ mb: 3 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SecurityIcon />
              </InputAdornment>
            ),
          }}
        />

        <Button
          type="submit"
          fullWidth
          variant="contained"
          disabled={loading}
          sx={{ mb: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Verify Code'}
        </Button>

        <Button
          fullWidth
          variant="text"
          onClick={handleBackToLogin}
          disabled={loading}
        >
          Back to Login
        </Button>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        maxWidth: 500,
        mx: 'auto',
        p: 3,
        border: 1,
        borderColor: 'divider',
        borderRadius: 2,
        boxShadow: 3
      }}
    >
      <Typography variant="h4" component="h1" align="center" gutterBottom>
        Sign In
      </Typography>

      <Tabs value={tabValue} onChange={handleTabChange} centered sx={{ mb: 2 }}>
        <Tab label="Email & Password" />
        {enableOAuth2 && <Tab label="Social Login" />}
        {enableSAML && <Tab label="Enterprise SSO" />}
      </Tabs>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      {/* Email & Password Tab */}
      <TabPanel value={tabValue} index={0}>
        <Box component="form" onSubmit={loginFormik.handleSubmit}>
          <TextField
            fullWidth
            id="email"
            name="email"
            label="Email Address"
            type="email"
            autoComplete="email"
            value={loginFormik.values.email}
            onChange={loginFormik.handleChange}
            onBlur={loginFormik.handleBlur}
            error={loginFormik.touched.email && Boolean(loginFormik.errors.email)}
            helperText={loginFormik.touched.email && loginFormik.errors.email}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <EmailIcon />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            fullWidth
            id="password"
            name="password"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            value={loginFormik.values.password}
            onChange={loginFormik.handleChange}
            onBlur={loginFormik.handleBlur}
            error={loginFormik.touched.password && Boolean(loginFormik.errors.password)}
            helperText={loginFormik.touched.password && loginFormik.errors.password}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LockIcon />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label="toggle password visibility"
                    onClick={() => setShowPassword(!showPassword)}
                    edge="end"
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {enableRememberMe && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={loginFormik.values.rememberMe}
                  onChange={loginFormik.handleChange}
                  name="rememberMe"
                />
              }
              label="Remember me"
              sx={{ mb: 2 }}
            />
          )}

          <Button
            type="submit"
            fullWidth
            variant="contained"
            disabled={loading}
            sx={{ mb: 2 }}
          >
            {loading ? <CircularProgress size={24} /> : 'Sign In'}
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Link
              component="button"
              variant="body2"
              onClick={handleForgotPassword}
              sx={{ textDecoration: 'none' }}
            >
              Forgot your password?
            </Link>
          </Box>
        </Box>
      </TabPanel>

      {/* OAuth2 Social Login Tab */}
      {enableOAuth2 && (
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<GoogleIcon />}
              onClick={() => handleOAuth2Login('google')}
              disabled={loading}
              sx={{ py: 1.5 }}
            >
              Continue with Google
            </Button>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<GitHubIcon />}
              onClick={() => handleOAuth2Login('github')}
              disabled={loading}
              sx={{ py: 1.5 }}
            >
              Continue with GitHub
            </Button>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<MicrosoftIcon />}
              onClick={() => handleOAuth2Login('microsoft')}
              disabled={loading}
              sx={{ py: 1.5 }}
            >
              Continue with Microsoft
            </Button>
          </Box>
        </TabPanel>
      )}

      {/* SAML Enterprise SSO Tab */}
      {enableSAML && (
        <TabPanel value={tabValue} index={enableOAuth2 ? 2 : 1}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Sign in with your organization's single sign-on (SSO) provider.
            </Typography>

            <Button
              fullWidth
              variant="outlined"
              startIcon={<SecurityIcon />}
              onClick={() => handleSAMLLogin('enterprise')}
              disabled={loading}
              sx={{ py: 1.5 }}
            >
              Enterprise SSO
            </Button>

            <Divider sx={{ my: 1 }}>
              <Typography variant="body2" color="text.secondary">
                or
              </Typography>
            </Divider>

            <TextField
              fullWidth
              label="Organization Domain"
              placeholder="company.com"
              helperText="Enter your organization's domain to find your SSO provider"
              sx={{ mb: 2 }}
            />

            <Button
              fullWidth
              variant="contained"
              disabled={loading}
              sx={{ py: 1.5 }}
            >
              Find SSO Provider
            </Button>
          </Box>
        </TabPanel>
      )}
    </Box>
  );
};

