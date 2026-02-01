import { useEffect, useState, useCallback } from "react";
import { listen } from "@tauri-apps/api/event";
import { Layout } from "@/components/layout/Layout";
import { StatusPage } from "@/pages/Status";
import { MemoriesPage } from "@/pages/Memories";
import { SettingsPage } from "@/pages/Settings";
import { MaintenancePage } from "@/pages/Maintenance";
import {
  getServiceStatus,
  checkHealth,
  getStats,
  type ServiceStatus,
  type HealthResponse,
  isServiceRunning,
  isServiceError,
} from "@/lib/api";

type UIStatus = "loading" | "healthy" | "error" | "restarting";

// Extended stats for UI display (combines API response with derived data)
interface Stats {
  backend: string;
  items: {
    total: number;
    active: number;
    archived: number;
  };
  categories: number;
}

function App() {
  const [currentPath, setCurrentPath] = useState("/");
  const [status, setStatus] = useState<UIStatus>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Convert Tauri ServiceStatus to UI status
  const updateStatusFromTauri = useCallback((tauriStatus: ServiceStatus) => {
    if (tauriStatus === "Running") {
      setStatus("healthy");
      setError(null);
    } else if (tauriStatus === "Starting") {
      setStatus("loading");
      setError(null);
    } else if (tauriStatus === "Restarting") {
      setStatus("restarting");
      setError(null);
    } else if (tauriStatus === "Stopped") {
      setStatus("error");
      setError("Service stopped");
    } else if (isServiceError(tauriStatus)) {
      setStatus("error");
      setError(tauriStatus.Error);
    }
  }, []);

  // Fetch health from API
  const fetchHealth = useCallback(async () => {
    try {
      const data = await checkHealth();
      setHealth(data);
      return true;
    } catch {
      return false;
    }
  }, []);

  // Fetch stats from API
  const fetchStats = useCallback(async () => {
    try {
      const data = await getStats();
      // API response matches UI format directly
      setStats({
        backend: data.backend || "SurrealDB",
        items: data.items || { total: 0, active: 0, archived: 0 },
        categories: data.categories || 0,
      });
    } catch {
      // Ignore stats errors
    }
  }, []);

  // Refresh all data
  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // Get service status from Rust
      const tauriStatus = await getServiceStatus();
      updateStatusFromTauri(tauriStatus);

      // If running, fetch health and stats
      if (isServiceRunning(tauriStatus)) {
        await Promise.all([fetchHealth(), fetchStats()]);
      }
    } catch (e) {
      setStatus("error");
      setError(e instanceof Error ? e.message : "Failed to get status");
    } finally {
      setIsRefreshing(false);
    }
  }, [updateStatusFromTauri, fetchHealth, fetchStats]);

  // Setup Tauri event listeners
  useEffect(() => {
    const unlisteners: (() => void)[] = [];

    // Listen for service-ready event
    listen<void>("service-ready", () => {
      console.log("[App] Service ready event received");
      setStatus("healthy");
      setError(null);
      // Fetch fresh data
      fetchHealth();
      fetchStats();
    }).then((unlisten) => unlisteners.push(unlisten));

    // Listen for service-error event
    listen<string>("service-error", (event) => {
      console.log("[App] Service error event received:", event.payload);
      setStatus("error");
      setError(event.payload);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Listen for service-restarting event
    listen<void>("service-restarting", () => {
      console.log("[App] Service restarting event received");
      setStatus("restarting");
      setError(null);
    }).then((unlisten) => unlisteners.push(unlisten));

    // Initial refresh
    refresh();

    // Periodic refresh every 10 seconds
    const interval = setInterval(refresh, 10000);

    return () => {
      clearInterval(interval);
      unlisteners.forEach((unlisten) => unlisten());
    };
  }, [refresh, fetchHealth, fetchStats]);

  const renderPage = () => {
    switch (currentPath) {
      case "/":
        return (
          <StatusPage
            health={health}
            stats={stats}
            error={error}
            status={status === "restarting" ? "loading" : status}
            isRefreshing={isRefreshing}
            onRefresh={refresh}
          />
        );
      case "/memories":
        return <MemoriesPage />;
      case "/settings":
        return <SettingsPage />;
      case "/maintenance":
        return <MaintenancePage onRefresh={refresh} />;
      default:
        return (
          <StatusPage
            health={health}
            stats={stats}
            error={error}
            status={status === "restarting" ? "loading" : status}
            isRefreshing={isRefreshing}
            onRefresh={refresh}
          />
        );
    }
  };

  return (
    <Layout
      currentPath={currentPath}
      onNavigate={setCurrentPath}
      serviceStatus={status === "restarting" ? "loading" : status}
    >
      {renderPage()}
    </Layout>
  );
}

export default App;
