import React, { createContext, useContext } from 'react';
import { MsalProvider, AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig, loginRequest } from './msalConfig';
import { useServiceHealth } from '@/hooks/useServiceHealth';

interface AuthContextType {
  user: { name: string; email: string } | null;
  isLocalMode: boolean;
}

const AuthContext = createContext<AuthContextType>({ user: null, isLocalMode: false });

export const useAuth = () => useContext(AuthContext);

const isLocalMode = import.meta.env.VITE_LOCAL_MODE === 'true';

const msalInstance = new PublicClientApplication(msalConfig);

function LoginScreen() {
  const { instance } = useMsal();
  return (
    <div className="flex h-screen items-center justify-center bg-bg-primary">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-text-primary mb-4">Client Intelligence Agent</h1>
        <button
          onClick={() => instance.loginRedirect(loginRequest)}
          className="px-6 py-3 bg-accent text-bg-primary font-semibold rounded-md hover:bg-accent-bright transition-colors duration-150"
        >
          Sign in with Microsoft
        </button>
      </div>
    </div>
  );
}

function AuthenticatedApp({ children }: { children: React.ReactNode }) {
  const { accounts } = useMsal();
  const account = accounts[0];
  const user = account ? { name: account.name || '', email: account.username || '' } : null;

  useServiceHealth();

  return (
    <AuthContext.Provider value={{ user, isLocalMode: false }}>
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (isLocalMode) {
    return (
      <AuthContext.Provider value={{ user: { name: 'Local Developer', email: 'dev@localhost' }, isLocalMode: true }}>
        {children}
      </AuthContext.Provider>
    );
  }

  return (
    <MsalProvider instance={msalInstance}>
      <AuthenticatedTemplate>
        <AuthenticatedApp>{children}</AuthenticatedApp>
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <LoginScreen />
      </UnauthenticatedTemplate>
    </MsalProvider>
  );
}
