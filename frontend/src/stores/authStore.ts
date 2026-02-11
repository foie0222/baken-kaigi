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
  updateUserAttributes,
} from 'aws-amplify/auth';
import { isAuthConfigured } from '../config/amplify';
import { apiClient } from '../api/client';

/** Cognitoの英語エラーメッセージを日本語に変換する */
export function toJapaneseAuthError(error: string | undefined, fallback: string): string {
  if (!error) return fallback;
  if (error.includes('Incorrect username or password')) return 'メールアドレスまたはパスワードが正しくありません';
  if (error.includes('User already exists')) return 'このメールアドレスは既に登録されています';
  if (error.includes('Password did not conform with policy')) return 'パスワードが要件を満たしていません（8文字以上、大文字・小文字・数字を含む）';
  if (error.includes('Invalid verification code')) return '確認コードが正しくありません';
  if (error.includes('Attempt limit exceeded')) return '試行回数の上限に達しました。しばらくしてからお試しください';
  if (error.includes('User is not confirmed')) return 'メールアドレスの確認が完了していません';
  if (error.includes('Username/client id combination not found')) return 'アカウントが見つかりません';
  if (error.includes('Incorrect current password') || error.includes('Incorrect password')) return '現在のパスワードが正しくありません';
  if (error.includes('Password attempts exceeded')) return 'パスワードの試行回数を超えました。しばらくしてからお試しください';
  if (error === 'Failed to fetch') return '通信エラーが発生しました';
  // ASCII印刷可能文字のみのメッセージはフォールバックに変換
  if (/^[\x20-\x7E]+$/.test(error)) return fallback;
  return error;
}

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
  completeOAuthRegistration: (displayName: string, birthdate: string) => Promise<void>;
  updateProfile: (displayName: string) => Promise<void>;
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, '登録に失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, '確認に失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'ログインに失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'ログアウトに失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'Googleログインに失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'Appleログインに失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'パスワードリセットに失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'パスワードリセットの確認に失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'パスワード変更に失敗しました'),
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
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'アカウント削除に失敗しました'),
      });
      throw error;
    }
  },

  completeOAuthRegistration: async (displayName, birthdate) => {
    try {
      set({ isLoading: true, error: null });
      const now = new Date().toISOString();
      await updateUserAttributes({
        userAttributes: {
          birthdate,
          'custom:display_name': displayName,
          'custom:terms_accepted_at': now,
          'custom:privacy_accepted_at': now,
        },
      });
      set((state) => ({
        user: state.user ? { ...state.user, displayName } : null,
        isLoading: false,
      }));
    } catch (error) {
      set({
        isLoading: false,
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'プロフィール更新に失敗しました'),
      });
      throw error;
    }
  },

  updateProfile: async (displayName) => {
    try {
      set({ isLoading: true, error: null });
      const result = await apiClient.updateUserProfile({ displayName });
      if (!result.success) {
        throw new Error(result.error || 'プロフィール更新に失敗しました');
      }
      await updateUserAttributes({
        userAttributes: {
          'custom:display_name': displayName,
        },
      });
      set((state) => ({
        user: state.user ? { ...state.user, displayName } : null,
        isLoading: false,
      }));
    } catch (error) {
      set({
        isLoading: false,
        error: toJapaneseAuthError(error instanceof Error ? error.message : undefined, 'プロフィール更新に失敗しました'),
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));
