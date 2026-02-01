import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
  currentPath: string;
  onNavigate: (path: string) => void;
  serviceStatus: "loading" | "healthy" | "error";
}

export function Layout({
  children,
  currentPath,
  onNavigate,
  serviceStatus,
}: LayoutProps) {
  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={onNavigate}
        serviceStatus={serviceStatus}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Titlebar drag region for main area */}
        <div className="titlebar-drag h-12 border-b border-border shrink-0" />

        {/* Scrollable content */}
        <main className="flex-1 overflow-auto">
          <div className="p-6 max-w-4xl mx-auto animate-fade-in-up">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
