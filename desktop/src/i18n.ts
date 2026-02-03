import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en/translation.json";
import ja from "./locales/ja/translation.json";
import zhTW from "./locales/zh-TW/translation.json";

/**
 * Detect user's preferred locale
 * - Chinese (any variant) → zh-TW
 * - Japanese → ja
 * - Others → en
 */
const detectLocale = (): string => {
  const candidates = [
    navigator.language,
    ...(navigator.languages ?? []),
  ].filter(Boolean).map((l) => l.toLowerCase());

  if (candidates.some((l) => l.startsWith("zh"))) return "zh-TW";
  if (candidates.some((l) => l.startsWith("ja"))) return "ja";
  return "en";
};

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ja: { translation: ja },
      "zh-TW": { translation: zhTW },
    },
    lng: detectLocale(),
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });

// Expose i18n to window for dev testing (e.g., window.__i18n__.changeLanguage('ja'))
// @ts-expect-error Vite import.meta.env
if (import.meta.env?.DEV) {
  (window as unknown as { __i18n__: typeof i18n }).__i18n__ = i18n;
}

export default i18n;
