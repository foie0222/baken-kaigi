import { Amplify } from 'aws-amplify';

const cognitoConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
      loginWith: {
        oauth: {
          domain: import.meta.env.VITE_COGNITO_DOMAIN || '',
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [window.location.origin + '/auth/callback'],
          redirectSignOut: [window.location.origin],
          responseType: 'code' as const,
        },
      },
    },
  },
};

export function configureAmplify() {
  Amplify.configure(cognitoConfig);
}
