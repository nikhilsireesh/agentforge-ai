import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Api, getToken, setToken } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [system, setSystem] = useState(null);
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [backendError, setBackendError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const status = await Api.systemStatus();
      setSystem(status);
      setBackendError(null);
      if (!status.auth_enabled || getToken()) {
        try {
          setUser(await Api.me());
        } catch {
          setUser(null);
        }
      }
    } catch {
      setBackendError("Cannot reach the AgentForge API. Start the backend and refresh.");
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const onUnauthorized = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("agentforge:unauthorized", onUnauthorized);
    return () => window.removeEventListener("agentforge:unauthorized", onUnauthorized);
  }, [refresh]);

  const login = async (email, password) => {
    const result = await Api.login(email, password);
    setToken(result.access_token);
    setUser(result.user);
  };

  const register = async (name, email, password) => {
    const result = await Api.register(name, email, password);
    setToken(result.access_token);
    setUser(result.user);
  };

  const demoLogin = async () => {
    const result = await Api.demoLogin();
    setToken(result.access_token);
    setUser(result.user);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  const canApprove = user && ["admin", "reviewer"].includes(user.role);

  return (
    <AuthContext.Provider
      value={{ system, user, ready, backendError, login, register, demoLogin, logout, refresh, canApprove }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
