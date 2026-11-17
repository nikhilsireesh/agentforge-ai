// Many screens (workspace, workflow, architecture, code, tests, docs) show one
// execution. This context remembers which one is selected across pages.
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Api } from "../services/api";
import { useAuth } from "./AuthContext";

const ExecutionContext = createContext(null);
const STORAGE_KEY = "agentforge_execution";

function readStored() {
  try {
    return Number(localStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null;
  }
}

export function ExecutionProvider({ children }) {
  const { user } = useAuth();
  const [executions, setExecutions] = useState([]);
  const [selectedId, setSelectedIdState] = useState(readStored);
  const [loaded, setLoaded] = useState(false);

  const setSelectedId = useCallback((id) => {
    setSelectedIdState(id);
    try {
      if (id) localStorage.setItem(STORAGE_KEY, String(id));
    } catch {
      /* ignore */
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!user) return [];
    try {
      const page = await Api.listExecutions({ page_size: 100 });
      setExecutions(page.items);
      setSelectedIdState((current) => {
        if (current && page.items.some((e) => e.id === current)) return current;
        return page.items[0]?.id ?? null;
      });
      return page.items;
    } finally {
      setLoaded(true);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <ExecutionContext.Provider value={{ executions, selectedId, setSelectedId, refresh, loaded }}>
      {children}
    </ExecutionContext.Provider>
  );
}

/** Selected execution id; a `?execution=ID` URL parameter takes priority. */
export function useSelectedExecution() {
  const ctx = useContext(ExecutionContext);
  const [params] = useSearchParams();
  const urlId = Number(params.get("execution")) || null;
  const { setSelectedId, executions, refresh } = ctx;

  useEffect(() => {
    if (urlId) {
      setSelectedId(urlId);
      if (!executions.some((e) => e.id === urlId)) refresh();
    }
  }, [urlId, setSelectedId, executions, refresh]);

  return { ...ctx, selectedId: urlId || ctx.selectedId };
}

export function useExecutions() {
  return useContext(ExecutionContext);
}
