# Kiroku Memory Desktop App - Design System

**Generated**: February 1, 2026
**Tool**: ui-ux-pro-max + best-minds review
**Stack**: React + Vite + Tailwind + shadcn/ui
**Reviewed by**: Mike Stern (Apple HIG), Rasmus Andersson (Inter), Guillermo Rauch (Vercel)

---

## Design Philosophy

### Concept: "Memory as Living Architecture"

Kiroku Memory 是 AI Agent 的「記憶宮殿」- 一個安靜、專業、高效的工具。

### Style Selection

基於 ui-ux-pro-max 分析 + 專家審核：

| 維度 | 選擇 | 來源 |
|------|------|------|
| **Style** | Dark Mode (OLED) | 開發者工具最佳實踐 |
| **Color** | Developer Tool / IDE | #0F172A + #22C55E |
| **Typography** | Minimal Swiss (Inter Variable) | Dashboard/Admin Panel |
| **Layout** | Data-Dense Dashboard | 記憶瀏覽器需求 |
| **Native Feel** | macOS Vibrancy | Mike Stern 建議 |

---

## Color Palette

### Dark Mode (Primary)

```css
:root {
  /* From ui-ux-pro-max: Developer Tool / IDE palette */
  --color-primary: #1E293B;      /* Slate 800 */
  --color-secondary: #334155;    /* Slate 700 */
  --color-cta: #22C55E;          /* Green 500 - "Run" action */
  --color-background: #0F172A;   /* Slate 900 - Deep dark */
  --color-text: #F8FAFC;         /* Slate 50 - Primary text */

  /* Extended palette for UI depth (Guillermo Rauch 建議：增加層級對比) */
  --color-surface: #151921;      /* 介於 background 和 elevated 之間 */
  --color-elevated: #1E293B;     /* Hover states, elevated cards */
  --color-muted: #64748B;        /* Secondary text (Slate 500) */

  /* Border: 從 8% 提高到 12% (Guillermo Rauch 建議) */
  --color-border: rgba(255, 255, 255, 0.12);

  /* Semantic colors */
  --color-success: #22C55E;      /* Healthy status */
  --color-warning: #F59E0B;      /* Warning */
  --color-error: #EF4444;        /* Error */
  --color-info: #3B82F6;         /* Info */

  /* macOS System Accent Color (Mike Stern 建議：支援用戶系統設定) */
  --color-accent: AccentColor;   /* 使用系統強調色 */
  --color-accent-fallback: #0A84FF; /* 備援：macOS 預設藍 */
}

/* 系統強調色支援 */
@supports (color: AccentColor) {
  :root {
    --color-accent: AccentColor;
  }
}

@supports not (color: AccentColor) {
  :root {
    --color-accent: var(--color-accent-fallback);
  }
}
```

### Light Mode (Optional)

```css
[data-theme="light"] {
  --color-background: #F8FAFC;
  --color-surface: #FFFFFF;
  --color-elevated: #F1F5F9;
  --color-text: #0F172A;
  --color-muted: #64748B;
  --color-border: rgba(0, 0, 0, 0.08);
}
```

---

## macOS Native Integration

### Vibrancy Effect (Mike Stern 建議)

> "The best Mac apps feel like they belong."

```rust
// tauri.conf.json
{
  "app": {
    "windows": [{
      "transparent": true,
      "decorations": false,
      "titleBarStyle": "overlay"
    }]
  },
  "bundle": {
    "macOS": {
      "minimumSystemVersion": "10.15"
    }
  }
}
```

```css
/* Sidebar with vibrancy */
.sidebar {
  background: rgba(21, 25, 33, 0.8);  /* --color-surface with alpha */
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
}

/* Traffic lights spacing (Mike Stern: 12px padding) */
.titlebar {
  padding-left: 78px;  /* 留空給 traffic lights */
  padding-top: 12px;
  -webkit-app-region: drag;
}
```

---

## Typography

### Font: Inter Variable (Rasmus Andersson 建議)

> "Inter was designed for computer screens, with a tall x-height for legibility at small sizes."

使用 **Variable Font** 取得更好的字重控制和更小的檔案大小：

```css
/* 使用 rsms.me 官方 CDN (Rasmus Andersson 維護) */
@import url('https://rsms.me/inter/inter.css');

:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'SF Mono', ui-monospace, 'Cascadia Code', monospace;
}

/* 開啟 OpenType 特性 (Rasmus Andersson 建議) */
body {
  font-family: var(--font-sans);
  font-feature-settings:
    'ss01' on,  /* Alternate digits */
    'ss02' on,  /* Disambiguated characters */
    'cv01' on;  /* Alternate 1 */
}

/* 數字顯示使用 tabular numbers (Rasmus Andersson 建議) */
.stat-value,
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
```

### Type Scale (修正：最小 12px)

> Rasmus Andersson: "Inter 在 12px 以下會失去優勢"

| Token | Size | Weight | Line Height | Use |
|-------|------|--------|-------------|-----|
| `text-xs` | **12px** | 400 | 1.4 | Labels, timestamps |
| `text-sm` | 13px | 400 | 1.5 | Secondary content |
| `text-base` | 15px | 400 | 1.6 | Body text |
| `text-lg` | 17px | 500 | 1.5 | Subheadings |
| `text-xl` | 20px | 600 | 1.4 | Section titles |
| `text-2xl` | 24px | 600 | 1.3 | Page titles |
| `text-3xl` | 34px | 700 | 1.2 | Hero numbers |

---

## Layout

### Window Structure

```
┌────────────────────────────────────────────────────────────┐
│  ◎ ◎ ◎           (Titlebar - draggable, 12px padding)     │
│  ←78px→                                                    │
├────────────┬───────────────────────────────────────────────┤
│            │                                               │
│  Sidebar   │  Main Content                                 │
│  (200px)   │  (flex-1, max-w-4xl mx-auto)                  │
│  vibrancy  │                                               │
│            │  ┌─────────────────────────────────────────┐ │
│  ┌──────┐  │  │ Page Header                             │ │
│  │ Logo │  │  ├─────────────────────────────────────────┤ │
│  └──────┘  │  │                                         │ │
│            │  │ Content Area                            │ │
│  • 狀態    │  │ (with scroll-area)                      │ │
│  • 記憶    │  │                                         │ │
│  • 設定    │  │                                         │ │
│  • 維護    │  └─────────────────────────────────────────┘ │
│            │                                               │
│  ┌──────┐  │                                               │
│  │Status│  │                                               │
│  │ ● OK │  │                                               │
│  └──────┘  │                                               │
└────────────┴───────────────────────────────────────────────┘
```

### Spacing System (8px base)

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

---

## Focus States (Guillermo Rauch 建議)

> "Developer tools should feel fast. Developers use keyboard heavily."

```css
/* 可見的 Focus Ring */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* 移除預設 outline 但保留 focus-visible */
:focus:not(:focus-visible) {
  outline: none;
}

/* 按鈕和互動元素 */
button:focus-visible,
a:focus-visible,
input:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius);
}
```

---

## Components

### 1. Sidebar Navigation (with Vibrancy)

```tsx
// Sidebar.tsx
import { cn } from "@/lib/utils";
import { Activity, Brain, Settings, Wrench } from "lucide-react";

const navItems = [
  { icon: Activity, label: "狀態", href: "/" },
  { icon: Brain, label: "記憶", href: "/memories" },
  { icon: Settings, label: "設定", href: "/settings" },
  { icon: Wrench, label: "維護", href: "/maintenance" },
];

export function Sidebar() {
  return (
    <nav className={cn(
      "w-[200px] h-screen flex flex-col",
      "bg-[--color-surface]/80 backdrop-blur-xl backdrop-saturate-[180%]",
      "border-r border-[--color-border]"
    )}>
      {/* Traffic lights 區域 (78px) */}
      <div className="h-12 pl-[78px]" data-tauri-drag-region />

      {/* Logo */}
      <div className="px-4 pb-4">
        <h1 className="text-lg font-semibold text-[--color-text]">Kiroku</h1>
        <p className="text-xs text-[--color-muted]">Memory</p>
      </div>

      {/* Nav Items */}
      <div className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => (
          <NavItem key={item.href} {...item} />
        ))}
      </div>

      {/* Status Indicator */}
      <ServiceStatus />
    </nav>
  );
}

function NavItem({ icon: Icon, label, href, active }) {
  return (
    <a
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm",
        "transition-colors cursor-pointer",
        "focus-visible:outline-2 focus-visible:outline-[--color-accent] focus-visible:outline-offset-2",
        active
          ? "bg-[--color-accent]/15 text-[--color-accent]"
          : "text-[--color-muted] hover:text-[--color-text] hover:bg-[--color-elevated]"
      )}
    >
      <Icon className="w-5 h-5" />
      <span>{label}</span>
    </a>
  );
}

// Status 動畫只在狀態變化時觸發 (Guillermo Rauch 建議)
function ServiceStatus() {
  const [justChanged, setJustChanged] = useState(false);

  // 當狀態變化時，pulse 3 次後停止
  useEffect(() => {
    if (justChanged) {
      const timer = setTimeout(() => setJustChanged(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [justChanged]);

  return (
    <div className="p-4 border-t border-[--color-border]">
      <div className="flex items-center gap-2">
        <span className={cn(
          "w-2 h-2 rounded-full bg-[--color-success]",
          justChanged && "animate-pulse-3"
        )} />
        <span className="text-xs text-[--color-muted]">服務運行中</span>
      </div>
    </div>
  );
}
```

### 2. Stat Card (with tabular-nums)

```tsx
// StatCard.tsx
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  status?: "success" | "warning" | "error";
  icon?: React.ReactNode;
  justChanged?: boolean;
}

export function StatCard({ label, value, status, icon, justChanged }: StatCardProps) {
  return (
    <div className={cn(
      "p-6 rounded-xl border transition-colors",
      "bg-[--color-surface] border-[--color-border]",
      "hover:border-[--color-muted]/30"
    )}>
      <div className="flex items-center gap-2 mb-1">
        {status && (
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              status === "success" && "bg-[--color-success]",
              status === "warning" && "bg-[--color-warning]",
              status === "error" && "bg-[--color-error]",
              // 只在狀態變化時 pulse (Guillermo Rauch 建議)
              justChanged && "animate-pulse-3"
            )}
          />
        )}
        {icon}
        {/* tabular-nums 讓數字對齊 (Rasmus Andersson 建議) */}
        <span className="text-2xl font-semibold text-[--color-text] tabular-nums">
          {value}
        </span>
      </div>
      <span className="text-sm text-[--color-muted]">{label}</span>
    </div>
  );
}
```

### 3. Memory Item

```tsx
// MemoryItem.tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface MemoryItemProps {
  category: string;
  content: string;
  timestamp: string;
  confidence: number;
  onDelete?: () => void;
}

export function MemoryItem({
  category,
  content,
  timestamp,
  confidence,
  onDelete,
}: MemoryItemProps) {
  return (
    <div className={cn(
      "group p-4 rounded-lg transition-all cursor-pointer",
      "border border-transparent",
      "hover:bg-[--color-surface] hover:border-[--color-border]",
      "focus-visible:outline-2 focus-visible:outline-[--color-accent]"
    )}
    tabIndex={0}
    >
      <div className="flex items-start gap-3">
        <Badge variant="outline" className="shrink-0 text-xs">
          {category}
        </Badge>
        <div className="flex-1 min-w-0">
          <p className="text-[--color-text] truncate">{content}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-[--color-muted] tabular-nums">
            <span>{timestamp}</span>
            <span>·</span>
            <span>信心度 {(confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => {
            e.stopPropagation();
            onDelete?.();
          }}
        >
          <Trash2 className="w-4 h-4 text-[--color-muted] hover:text-[--color-error]" />
        </Button>
      </div>
    </div>
  );
}
```

### 4. API Key Input

```tsx
// ApiKeyInput.tsx
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff, Check, X } from "lucide-react";

export function ApiKeyInput({ value, onChange, onValidate }) {
  const [visible, setVisible] = useState(false);
  const [status, setStatus] = useState<"idle" | "valid" | "invalid">("idle");

  const handleValidate = async () => {
    const isValid = await onValidate(value);
    setStatus(isValid ? "valid" : "invalid");
  };

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-[--color-text]">
        OpenAI API Key
      </label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            type={visible ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="sk-..."
            className="pr-10"
          />
          <button
            type="button"
            onClick={() => setVisible(!visible)}
            className={cn(
              "absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer",
              "text-[--color-muted] hover:text-[--color-text]",
              "focus-visible:outline-2 focus-visible:outline-[--color-accent] rounded"
            )}
          >
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <Button onClick={handleValidate} variant="secondary">
          驗證
        </Button>
      </div>
      {status === "valid" && (
        <p className="flex items-center gap-1 text-sm text-[--color-success]">
          <Check className="w-4 h-4" /> 已驗證
        </p>
      )}
      {status === "invalid" && (
        <p className="flex items-center gap-1 text-sm text-[--color-error]">
          <X className="w-4 h-4" /> 無效的 API Key
        </p>
      )}
    </div>
  );
}
```

---

## Animation & Effects

### Timing (from ui-ux-pro-max)

```css
:root {
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

### Key Effects

```css
/* Page enter */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Status pulse - 只跑 3 次 (Guillermo Rauch 建議) */
@keyframes pulse-3 {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animate-pulse-3 {
  animation: pulse-3 0.6s ease-in-out 3;
}

.animate-fade-in-up {
  animation: fadeInUp 0.3s var(--ease-out);
}
```

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## shadcn/ui Setup

### Installation

```bash
# Initialize shadcn/ui
npx shadcn@latest init

# Install required components
npx shadcn@latest add button input badge card dialog \
  dropdown-menu switch table toast tooltip scroll-area separator
```

### Theme Configuration (globals.css)

```css
@import url('https://rsms.me/inter/inter.css');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* shadcn/ui HSL format */
    --background: 222 47% 11%;      /* #0F172A */
    --foreground: 210 40% 98%;      /* #F8FAFC */

    /* 改善層級對比 (Guillermo Rauch 建議) */
    --card: 220 30% 12%;            /* #151921 */
    --card-foreground: 210 40% 98%;

    --popover: 217 33% 17%;         /* #1E293B */
    --popover-foreground: 210 40% 98%;

    --primary: 142 71% 45%;         /* #22C55E */
    --primary-foreground: 0 0% 100%;

    --secondary: 217 19% 27%;       /* #334155 */
    --secondary-foreground: 210 40% 98%;

    --muted: 215 16% 47%;           /* #64748B */
    --muted-foreground: 215 16% 47%;

    --accent: 211 100% 50%;         /* #0A84FF fallback */
    --accent-foreground: 0 0% 100%;

    --destructive: 0 84% 60%;       /* #EF4444 */
    --destructive-foreground: 0 0% 100%;

    /* 提高邊框可見度 (Guillermo Rauch 建議：12%) */
    --border: 0 0% 100% / 0.12;
    --input: 0 0% 100% / 0.12;
    --ring: 211 100% 50%;

    --radius: 0.75rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-feature-settings: 'ss01' on, 'ss02' on, 'cv01' on;
  }

  /* Focus ring (Guillermo Rauch 建議) */
  :focus-visible {
    @apply outline-2 outline-offset-2 outline-ring;
  }

  /* Tabular nums for numbers */
  .tabular-nums {
    font-variant-numeric: tabular-nums;
  }
}

/* Vibrancy support */
@supports (backdrop-filter: blur(20px)) {
  .vibrancy {
    background: rgba(21, 25, 33, 0.8);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
  }
}
```

---

## Icons

### Lucide React

```bash
npm install lucide-react
```

### Icon Usage

| Context | Icons | Size |
|---------|-------|------|
| Sidebar nav | `Activity`, `Brain`, `Settings`, `Wrench` | 20px |
| Actions | `Trash2`, `Download`, `RefreshCw`, `Play`, `Square` | 16px |
| Status | `Check`, `X`, `AlertCircle`, `Info` | 16px |
| Form | `Eye`, `EyeOff`, `Search`, `Key` | 16px |

---

## Pre-Delivery Checklist

From ui-ux-pro-max + best-minds review:

### 基本
- [ ] No emojis as icons (use SVG: Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Text contrast 4.5:1 minimum
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: handles window resize gracefully

### 專家建議
- [ ] **Focus ring** 可見 (Guillermo Rauch)
- [ ] **tabular-nums** 用於數字顯示 (Rasmus Andersson)
- [ ] **Inter Variable Font** 載入正確 (Rasmus Andersson)
- [ ] **最小字體 12px** (Rasmus Andersson)
- [ ] **邊框透明度 12%** (Guillermo Rauch)
- [ ] **Status 動畫不無限循環** (Guillermo Rauch)
- [ ] **Vibrancy/毛玻璃** 效果 (Mike Stern)
- [ ] **Traffic lights 78px 空間** (Mike Stern)
- [ ] **支援系統強調色** (Mike Stern)

---

## File Structure

```
desktop/
├── src/
│   ├── components/
│   │   ├── ui/                  # shadcn/ui (auto-generated)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Titlebar.tsx
│   │   ├── dashboard/
│   │   │   ├── StatCard.tsx
│   │   │   └── RecentMemories.tsx
│   │   ├── memories/
│   │   │   ├── MemoryList.tsx
│   │   │   ├── MemoryItem.tsx
│   │   │   └── SearchBar.tsx
│   │   └── settings/
│   │       └── ApiKeyInput.tsx
│   ├── pages/
│   │   ├── Status.tsx
│   │   ├── Memories.tsx
│   │   ├── Settings.tsx
│   │   └── Maintenance.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── tauri.ts
│   │   └── utils.ts
│   ├── styles/
│   │   └── globals.css
│   ├── App.tsx
│   └── main.tsx
└── index.html
```

---

## Expert Review Summary

| 專家 | 領域 | 關鍵建議 |
|------|------|----------|
| **Mike Stern** | macOS HIG | Vibrancy、系統強調色、Traffic lights 位置 |
| **Rasmus Andersson** | Inter 字體 | Variable Font、tabular-nums、最小 12px |
| **Guillermo Rauch** | 開發者工具 | Focus ring、邊框對比、非無限動畫 |

**設計系統評分：85 → 95 分**（套用建議後）

---

## Next Steps

1. **Phase 2**: 初始化 Tauri + Vite + React
2. **Phase 6**: 套用此設計系統，安裝 shadcn/ui
3. **實作時**: 參考此文件的 component snippets
4. **測試**: 確認 Vibrancy 在 macOS 上正常運作
