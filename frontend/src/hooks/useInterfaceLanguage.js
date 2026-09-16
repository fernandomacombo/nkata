import { useEffect, useState } from "react";

function readLanguage() {
  return document.documentElement.dataset.nkataLanguage === "EN" ? "EN" : "PT";
}

export default function useInterfaceLanguage() {
  const [language, setLanguage] = useState(readLanguage);

  useEffect(() => {
    const handlePreferences = (event) => {
      setLanguage(event.detail?.idioma === "EN" ? "EN" : readLanguage());
    };

    window.addEventListener("nkata:preferences-applied", handlePreferences);
    return () => window.removeEventListener("nkata:preferences-applied", handlePreferences);
  }, []);

  return language;
}
