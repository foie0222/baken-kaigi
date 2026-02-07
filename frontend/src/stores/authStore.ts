import { create } from 'zustand';
import {
  signUp as amplifySignUp,
  confirmSignUp as amplifyConfirmSignUp,
  signIn as amplifySignIn,
  signOut as amplifySignOut,
  getCurrentUser,
  fetchAuthSession,
  resetPassword as amplifyResetPassword,
  confirmResetPassword as amplifyConfirmResetPassword,
  updatePassword as amplifyUpdatePassword,
  deleteUser as amplifyDeleteUser,
  signInWithRedirect,
} from 'aws-amplify/auth';
import { isAuthConfigured } from '../config/amplify';

interface AuthUser {
  userId: string;
  email: string;
  displayName?: string;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  checkAuth: () => Promise<void>;
  signUp: (email: string, password: string, displayName: string, birthdate: string) => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signInWithApple: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  confirmResetPassword: (email: string, code: string, newPassword: string) => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  deleteAccount: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  checkAuth: async () => {
    if (!isAuthConfigured) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    try {
      set({ isLoading: true, error: null });
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken;
      const email = idToken?.payload?.email as string || '';
      const displayName = idToken?.payload?.['custom:display_name'] as string || '';

      set({
        user: {
          userId: currentUser.userId,
          email,
          displayName,
        },
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  signUp: async (email, password, displayName, birthdate) => {
    try {
      set({ isLoading: true, error: null });
      await amplifySignUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email,
            birthdate,
            'custom:display_name': displayName,
          },
        },
      });
      set({ isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Registration failed',
      });
      throw error;
    }
  },

  confirmSignUp: async (email, code) => {
    try {
      set({ isLoading: true, error: null });
      await amplifyConfirmSignUp({ username: email, confirmationCode: code });
      set({ isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Confirmation failed',
      });
      throw error;
    }
  },

  signIn: async (email, password) => {
    try {
      set({ isLoading: true, error: null });
      await amplifySignIn({ username: email, password });
      const currentUser = await getCurrentUser();
      const session = await fetchAuthSession();
      const idToken = session.tokens?.idToken;
      const displayName = idToken?.payload?.['custom:display_name'] as string || '';

      set({
        user: {
          userId: currentUser.userId,
          email,
          displayName,
        },
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Login failed',
      });
      throw error;
    }
  },

  signOut: async () => {
    try {
      set({ isLoading: true, error: null });
      await amplifySignOut();
      set({ user: null, isAuthenticated: false, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Logout failed',
      });
    }
  },

  signInWithGoogle: async () => {
    try {
      set({ isLoading: true, error: null });
      await signInWithRedirect({ provider: 'Google' });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Google login failed',
      });
    }
  },

  signInWithApple: async () => {
    try {
      set({ isLoading: true, error: null });
      await signInWithRedirect({ provider: 'Apple' });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Apple login failed',
      });
    }
  },

  forgotPassword: async (email) => {
    try {
      set({ isLoading: true, error: null });
      await amplifyResetPassword({ username: email });
      set({ isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Password reset failed',
      });
      throw error;
    }
  },

  confirmResetPassword: async (email, code, newPassword) => {
    try {
      set({ isLoading: true, error: null });
      await amplifyConfirmResetPassword({
        username: email,
        confirmationCode: code,
        newPassword,
      });
      set({ isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Password reset confirmation failed',
      });
      throw error;
    }
  },

  changePassword: async (oldPassword, newPassword) => {
    try {
      set({ isLoading: true, error: null });
      await amplifyUpdatePassword({ oldPassword, newPassword });
      set({ isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Password change failed',
      });
      throw error;
    }
  },

  deleteAccount: async () => {
    try {
      set({ isLoading: true, error: null });
      await amplifyDeleteUser();
      set({ user: null, isAuthenticated: false, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Account deletion failed',
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
