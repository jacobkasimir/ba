export const SETTINGS_KEY = "aktin.frontend.settings.v1";

function browserLanguage() {
  return /^en(?:-|$)/i.test(navigator.language || "") ? "en" : "de";
}

export const defaultSettings = () => ({
  language: browserLanguage(),
  theme: "dark",
  fontSize: "medium",
  density: "comfortable",
  reduceMotion: "auto",
  autocomplete: true,
  showSql: true,
  showDetails: true,
  displayName: "",
});

const choices = {
  language: ["de", "en"], theme: ["dark", "light", "system"],
  fontSize: ["small", "medium", "large"], density: ["comfortable", "compact"],
  reduceMotion: ["auto", "on", "off"],
};

export function loadSettings() {
  const defaults = defaultSettings();
  try {
    const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
    if (!stored || typeof stored !== "object") return defaults;
    const settings = { ...defaults, ...stored };
    for (const [key, values] of Object.entries(choices)) {
      if (!values.includes(settings[key])) settings[key] = defaults[key];
    }
    for (const key of ["autocomplete", "showSql", "showDetails"]) settings[key] = Boolean(settings[key]);
    settings.displayName = typeof settings.displayName === "string" ? settings.displayName.slice(0, 40) : "";
    return settings;
  } catch {
    return defaults;
  }
}

export function saveSettings(settings) {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch { /* Storage may be unavailable. */ }
}

export function resetSettings() {
  const settings = defaultSettings();
  saveSettings(settings);
  return settings;
}

export function applyVisualSettings(settings, colorScheme = matchMedia("(prefers-color-scheme: dark)"), motionPreference = matchMedia("(prefers-reduced-motion: reduce)")) {
  const root = document.documentElement;
  const theme = settings.theme === "system" ? (colorScheme.matches ? "dark" : "light") : settings.theme;
  root.dataset.theme = theme;
  root.dataset.themeSetting = settings.theme;
  root.dataset.fontSize = settings.fontSize;
  root.dataset.density = settings.density;
  const reduce = settings.reduceMotion === "on" || (settings.reduceMotion === "auto" && motionPreference.matches);
  root.dataset.motion = reduce ? "on" : "off";
}
