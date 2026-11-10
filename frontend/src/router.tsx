import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

interface RouterState {
  path: string;
  navigate: (path: string) => void;
}

const RouterContext = createContext<RouterState | null>(null);

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() => window.location.pathname);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = (next: string) => {
    if (next !== window.location.pathname) {
      window.history.pushState(null, "", next);
      setPath(next);
    }
  };

  const value = useMemo(() => ({ path, navigate }), [path]);

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter(): RouterState {
  const ctx = useContext(RouterContext);
  if (!ctx) {
    throw new Error("useRouter must be used within a RouterProvider");
  }
  return ctx;
}
