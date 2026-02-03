import { Activity, Brain, Settings, Wrench } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";

interface NavItem {
  icon: React.ElementType;
  labelKey: string;
  href: string;
}

const navItems: NavItem[] = [
  { icon: Activity, labelKey: "nav.status", href: "/" },
  { icon: Brain, labelKey: "nav.memories", href: "/memories" },
  { icon: Settings, labelKey: "nav.settings", href: "/settings" },
  { icon: Wrench, labelKey: "nav.maintenance", href: "/maintenance" },
];

interface SidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  serviceStatus: "loading" | "healthy" | "error";
}

export function Sidebar({ currentPath, onNavigate, serviceStatus }: SidebarProps) {
  const { t } = useTranslation();

  return (
    <nav
      className={cn(
        "w-[200px] h-screen flex flex-col shrink-0",
        "vibrancy border-r border-border"
      )}
    >
      {/* Traffic lights 區域 (78px from left) + titlebar drag */}
      <div className="titlebar-drag h-14 pl-[78px] flex items-end pb-2">
        <div className="titlebar-no-drag">
          <h1 className="text-base font-semibold">Kiroku</h1>
          <p className="text-xs text-muted-foreground -mt-0.5">Memory</p>
        </div>
      </div>

      {/* Nav Items */}
      <div className="flex-1 px-2 pt-0 pb-4 space-y-1">
        {navItems.map((item) => (
          <NavItemButton
            key={item.href}
            icon={item.icon}
            label={t(item.labelKey)}
            active={currentPath === item.href}
            onClick={() => onNavigate(item.href)}
          />
        ))}
      </div>

      {/* Status Indicator */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-2 h-2 rounded-full transition-colors",
              serviceStatus === "healthy" && "bg-success",
              serviceStatus === "error" && "bg-destructive",
              serviceStatus === "loading" && "bg-muted animate-pulse"
            )}
          />
          <span className="text-xs text-muted-foreground">
            {t(`status.state.${serviceStatus}`)}
          </span>
        </div>
      </div>
    </nav>
  );
}

interface NavItemButtonProps {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
}

function NavItemButton({ icon: Icon, label, active, onClick }: NavItemButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm",
        "transition-colors cursor-pointer titlebar-no-drag",
        "focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2",
        active
          ? "bg-accent/15 text-accent"
          : "text-muted-foreground hover:text-foreground hover:bg-popover"
      )}
    >
      <Icon className="w-5 h-5" />
      <span>{label}</span>
    </button>
  );
}
