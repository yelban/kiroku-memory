import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, Activity, Database, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HealthResponse } from "@/lib/api";

interface Stats {
  backend: string;
  items: {
    total: number;
    active: number;
    archived: number;
  };
  categories: number;
}

interface StatusPageProps {
  health: HealthResponse | null;
  stats: Stats | null;
  error: string | null;
  status: "loading" | "healthy" | "error";
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function StatusPage({
  health,
  stats,
  error,
  status,
  isRefreshing,
  onRefresh,
}: StatusPageProps) {
  return (
    <>
      {/* Status Card */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "w-3 h-3 rounded-full transition-colors",
                  status === "healthy" && "bg-success",
                  status === "error" && "bg-destructive",
                  status === "loading" && "bg-muted animate-pulse"
                )}
              />
              <CardTitle>
                {status === "loading"
                  ? "連線中..."
                  : status === "healthy"
                    ? "服務運行中"
                    : "服務錯誤"}
              </CardTitle>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={cn("w-4 h-4", isRefreshing && "animate-spin")}
              />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="text-sm text-destructive mb-4">錯誤: {error}</p>
          )}

          {health && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">狀態:</span>
                <span className="font-medium">{health.status}</span>
              </div>
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">版本:</span>
                <span className="font-medium tabular-nums">
                  {health.version}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard
            icon={<Layers className="w-5 h-5" />}
            value={stats.items.total}
            label="總項目"
          />
          <StatCard
            icon={<Activity className="w-5 h-5" />}
            value={stats.items.active}
            label="活躍"
          />
          <StatCard
            icon={<Database className="w-5 h-5" />}
            value={stats.categories}
            label="分類"
          />
        </div>
      )}

      {/* Backend Info */}
      {stats && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">後端</span>
              <span className="font-medium">{stats.backend}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}

interface StatCardProps {
  icon: React.ReactNode;
  value: number;
  label: string;
}

function StatCard({ icon, value, label }: StatCardProps) {
  return (
    <Card className="text-center hover:border-muted-foreground/30 transition-colors cursor-default">
      <CardContent className="pt-6">
        <div className="flex justify-center text-muted-foreground mb-2">
          {icon}
        </div>
        <div className="text-3xl font-semibold tabular-nums">{value}</div>
        <div className="text-sm text-muted-foreground">{label}</div>
      </CardContent>
    </Card>
  );
}
