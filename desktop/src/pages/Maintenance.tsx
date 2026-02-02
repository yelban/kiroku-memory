import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  Wrench,
  RefreshCw,
  Square,
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
      setMessage({ type: "success", text: "服務重啟成功" });
      onRefresh();
    } catch (error) {
      setMessage({ type: "error", text: `重啟失敗: ${error}` });
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
      setMessage({ type: "success", text: "服務已停止" });
      onRefresh();
    } catch (error) {
      setMessage({ type: "error", text: `停止失敗: ${error}` });
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
            服務控制
          </CardTitle>
          <CardDescription>管理 Python 後端服務的生命週期</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">重啟服務</p>
              <p className="text-sm text-muted-foreground">停止並重新啟動 Python 服務</p>
            </div>
            <Button onClick={handleRestart} disabled={isRestarting || isStopping}>
              {isRestarting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              重啟
            </Button>
          </div>

          <div className="border-t border-border" />

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">停止服務</p>
              <p className="text-sm text-muted-foreground">
                {isRunning ? "服務目前運行中" : "服務目前已停止"}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={handleStop}
              disabled={isRestarting || isStopping || !isRunning}
            >
              {isStopping ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Square className="w-4 h-4 mr-2" />
              )}
              停止
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="w-5 h-5" />
            資料目錄
          </CardTitle>
          <CardDescription>應用程式資料儲存位置</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="font-mono text-sm truncate text-muted-foreground">
                {dataDir || "載入中..."}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleOpenDataDir} disabled={!dataDir}>
              <FolderOpen className="w-4 h-4 mr-2" />
              開啟
            </Button>
          </div>

          <div className="text-sm text-muted-foreground">
            <p>此目錄包含：</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>SurrealDB 資料庫檔案</li>
              <li>應用程式設定</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="w-5 h-5" />
            危險操作
          </CardTitle>
          <CardDescription>這些操作無法復原，請謹慎使用</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">清除所有資料</p>
              <p className="text-sm text-muted-foreground">刪除所有記憶、事實和摘要</p>
            </div>
            <Button variant="destructive" disabled>
              <Trash2 className="w-4 h-4 mr-2" />
              清除
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            此功能尚未實作，將在未來版本提供
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
