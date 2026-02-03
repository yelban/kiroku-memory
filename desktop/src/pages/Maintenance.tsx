import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  Wrench,
  RefreshCw,
  Square,
  Play,
  FolderOpen,
  Trash2,
  Loader2,
  Check,
  AlertTriangle,
} from "lucide-react";
import { restartService, stopService, getDataDir, getServiceStatus, isServiceRunning } from "../lib/api";

interface MaintenancePageProps {
  onRefresh: () => void;
}

export function MaintenancePage({ onRefresh }: MaintenancePageProps) {
  const { t } = useTranslation();
  const [isRestarting, setIsRestarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [dataDir, setDataDir] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [dir, status] = await Promise.all([getDataDir(), getServiceStatus()]);
      setDataDir(dir);
      setIsRunning(isServiceRunning(status));
    } catch (error) {
      console.error("Failed to load maintenance data:", error);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRestart = async () => {
    setIsRestarting(true);
    setMessage(null);
    try {
      await restartService();
      setMessage({ type: "success", text: t("maintenance.messages.restartSuccess") });
      onRefresh();
    } catch (error) {
      setMessage({ type: "error", text: t("maintenance.messages.restartFailed", { error: String(error) }) });
    } finally {
      setIsRestarting(false);
      loadData();
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    setMessage(null);
    try {
      await stopService();
      setMessage({ type: "success", text: t("maintenance.messages.stopSuccess") });
      onRefresh();
    } catch (error) {
      setMessage({ type: "error", text: t("maintenance.messages.stopFailed", { error: String(error) }) });
    } finally {
      setIsStopping(false);
      loadData();
    }
  };

  const handleStart = async () => {
    setIsStopping(true); // reuse the same loading state
    setMessage(null);
    try {
      await restartService(); // restart also starts a stopped service
      setMessage({ type: "success", text: t("maintenance.messages.startSuccess") });
      onRefresh();
    } catch (error) {
      setMessage({ type: "error", text: t("maintenance.messages.startFailed", { error: String(error) }) });
    } finally {
      setIsStopping(false);
      loadData();
    }
  };

  const handleOpenDataDir = async () => {
    if (dataDir) {
      // Use Tauri shell plugin to open folder
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(dataDir);
    }
  };

  return (
    <div className="space-y-4">
      {message && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            message.type === "success"
              ? "bg-green-500/10 text-green-500"
              : "bg-destructive/10 text-destructive"
          }`}
        >
          {message.type === "success" ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wrench className="w-5 h-5" />
            {t("maintenance.serviceControlTitle")}
          </CardTitle>
          <CardDescription>{t("maintenance.serviceControlDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">{t("maintenance.restartServiceTitle")}</p>
              <p className="text-sm text-muted-foreground">{t("maintenance.restartServiceDescription")}</p>
            </div>
            <Button onClick={handleRestart} disabled={isRestarting || isStopping}>
              {isRestarting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              {t("maintenance.restart")}
            </Button>
          </div>

          <div className="border-t border-border" />

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">
                {isRunning ? t("maintenance.stopServiceTitle") : t("maintenance.startServiceTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {isRunning ? t("maintenance.serviceRunning") : t("maintenance.serviceStopped")}
              </p>
            </div>
            <Button
              variant={isRunning ? "outline" : "default"}
              onClick={isRunning ? handleStop : handleStart}
              disabled={isRestarting || isStopping}
            >
              {isStopping ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : isRunning ? (
                <Square className="w-4 h-4 mr-2" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              {isRunning ? t("maintenance.stop") : t("maintenance.start")}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="w-5 h-5" />
            {t("maintenance.dataDirTitle")}
          </CardTitle>
          <CardDescription>{t("maintenance.dataDirDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="font-mono text-sm truncate text-muted-foreground">
                {dataDir || t("maintenance.dataDirLoading")}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleOpenDataDir} disabled={!dataDir}>
              <FolderOpen className="w-4 h-4 mr-2" />
              {t("maintenance.open")}
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>{t("maintenance.dataDirIncludes")}</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>{t("maintenance.dataDirItemDb")}</li>
              <li>{t("maintenance.dataDirItemSettings")}</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="w-5 h-5" />
            {t("maintenance.dangerTitle")}
          </CardTitle>
          <CardDescription>{t("maintenance.dangerDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">{t("maintenance.wipeAllTitle")}</p>
              <p className="text-sm text-muted-foreground">{t("maintenance.wipeAllDescription")}</p>
            </div>
            <Button variant="destructive" disabled>
              <Trash2 className="w-4 h-4 mr-2" />
              {t("maintenance.wipeAll")}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {t("maintenance.wipeAllNotImplemented")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
