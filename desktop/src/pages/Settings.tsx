import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Settings, Key, Eye, EyeOff, Check, X, Loader2 } from "lucide-react";
import {
  hasOpenAIKey,
  setOpenAIKey,
  deleteOpenAIKey,
  getSettings,
  saveSettings,
  type AppSettings,
} from "../lib/api";

export function SettingsPage() {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [settings, setSettingsState] = useState<AppSettings | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [keyExists, appSettings] = await Promise.all([hasOpenAIKey(), getSettings()]);
      setHasKey(keyExists);
      setSettingsState(appSettings);
    } catch (error) {
      console.error("Failed to load settings:", error);
      setMessage({ type: "error", text: t("settings.messages.loadFailed") });
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSaveApiKey = async () => {
    if (!apiKey.trim()) {
      setMessage({ type: "error", text: t("settings.messages.missingApiKey") });
      return;
    }

    setIsSaving(true);
    try {
      await setOpenAIKey(apiKey.trim());
      setHasKey(true);
      setApiKey("");
      setShowKey(false);
      setMessage({ type: "success", text: t("settings.messages.apiKeyStored") });
    } catch (error) {
      setMessage({ type: "error", text: t("settings.messages.saveFailed") });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteApiKey = async () => {
    setIsSaving(true);
    try {
      await deleteOpenAIKey();
      setHasKey(false);
      setMessage({ type: "success", text: t("settings.messages.apiKeyDeleted") });
    } catch (error) {
      setMessage({ type: "error", text: t("settings.messages.saveFailed") });
    } finally {
      setIsSaving(false);
    }
  };

  const updateSettings = async (updates: Partial<AppSettings>) => {
    if (!settings) return;

    const newSettings = { ...settings, ...updates };
    try {
      await saveSettings(newSettings);
      setSettingsState(newSettings);
      setMessage({ type: "success", text: t("settings.messages.settingsSaved") });
    } catch (error) {
      setMessage({ type: "error", text: t("settings.messages.saveFailed") });
    }
  };

  const handleToggleAutoStart = async (checked: boolean) => {
    await updateSettings({ auto_start_service: checked });
  };

  const handleToggleStartHidden = async (checked: boolean) => {
    await updateSettings({ start_hidden: checked });
  };

  const handleToggleLaunchAtLogin = async (checked: boolean) => {
    await updateSettings({ launch_at_login: checked });
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

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
          {message.type === "success" ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            {t("settings.apiKeyTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("settings.apiKeyDescription")}
          </p>

          {hasKey ? (
            <div className="flex items-center gap-3">
              <div className="flex-1 px-3 py-2 bg-muted rounded-md font-mono text-sm">
                ••••••••••••••••••••••••
              </div>
              <Button variant="destructive" size="sm" onClick={handleDeleteApiKey} disabled={isSaving}>
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : t("settings.delete")}
              </Button>
            </div>
          ) : (
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  type={showKey ? "text" : "password"}
                  placeholder="sk-..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="pr-10 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <Button onClick={handleSaveApiKey} disabled={isSaving || !apiKey.trim()}>
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : t("settings.save")}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            {t("settings.generalTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="auto-start">{t("settings.autoStartTitle")}</Label>
              <p className="text-sm text-muted-foreground">{t("settings.autoStartDescription")}</p>
            </div>
            <Switch
              id="auto-start"
              checked={settings?.auto_start_service ?? true}
              onCheckedChange={handleToggleAutoStart}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="start-hidden">{t("settings.startHiddenTitle")}</Label>
              <p className="text-sm text-muted-foreground">{t("settings.startHiddenDescription")}</p>
            </div>
            <Switch
              id="start-hidden"
              checked={settings?.start_hidden ?? false}
              onCheckedChange={handleToggleStartHidden}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="launch-at-login">{t("settings.launchAtLoginTitle")}</Label>
              <p className="text-sm text-muted-foreground">
                {t("settings.launchAtLoginDescription")}
              </p>
            </div>
            <Switch
              id="launch-at-login"
              checked={settings?.launch_at_login ?? false}
              onCheckedChange={handleToggleLaunchAtLogin}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
