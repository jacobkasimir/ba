(() => {
  const key = "aktin.frontend.settings.v1";
  const root = document.documentElement;
  const back = document.querySelector(".back-to-assistant");

  function applyApplicationPreferences() {
    let settings = {};
    try {
      settings = JSON.parse(localStorage.getItem(key) || "{}") || {};
    } catch {
      settings = {};
    }

    const language = settings.language === "de" || settings.language === "en"
      ? settings.language
      : (/^en(?:-|$)/i.test(navigator.language || "") ? "en" : "de");
    const storedTheme = settings.theme;
    const dark = storedTheme === "dark"
      || (storedTheme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);

    root.lang = language;
    root.dataset.mdColorScheme = dark ? "slate" : "default";
    if (back) {
      back.textContent = language === "en" ? back.dataset.backEn : back.dataset.backDe;
    }
  }

  applyApplicationPreferences();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    try {
      const settings = JSON.parse(localStorage.getItem(key) || "{}") || {};
      if (!settings.theme || settings.theme === "system") applyApplicationPreferences();
    } catch {
      applyApplicationPreferences();
    }
  });
})();
