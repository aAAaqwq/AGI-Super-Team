(function () {
  try {
    var stored = localStorage.getItem("agi-skills-atlas:theme");
    if (stored === "light" || stored === "dark") {
      document.documentElement.dataset.theme = stored;
      document.documentElement.style.colorScheme = stored;
    } else {
      document.documentElement.dataset.theme = "auto";
    }
  } catch (error) {
    // Private mode or blocked storage: fall back to the system preference.
    document.documentElement.dataset.theme = "auto";
  }
})();
