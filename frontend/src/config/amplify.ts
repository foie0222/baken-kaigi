import { Amplify } from 'aws-amplify';

export let isAuthConfigured = false;

export function configureAmplify() {
  const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID || '';
  const userPoolClientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '';

  if (!userPoolId || !userPoolClientId) {
    console.warn(
      '[Amplify] VITE_COGNITO_USER_POOL_ID または VITE_COGNITO_CLIENT_ID が未設定です。認証機能は動作しません。'
    );
    return;
  }

  const cognitoConfig = {
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          oauth: {
            domain: import.meta.env.VITE_COGNITO_DOMAIN || '',
            scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
            redirectSignIn: [`${window.location.origin}/auth/callback`],
            redirectSignOut: [window.location.origin],
            responseType: 'code' as const,
          },
        },
      },
    },
  };

  Amplify.configure(cognitoConfig);
  isAuthConfigured = true;
}
