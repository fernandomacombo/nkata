import { useCallback, useEffect, useState } from "react";
import {
  fetchPushConfiguration,
  removePushSubscription,
  savePushSubscription,
} from "../services/api.js";
import { getReadyServiceWorker, urlBase64ToUint8Array } from "../services/pwa.js";

function browserSupportsPush() {
  return window.isSecureContext
    && "serviceWorker" in navigator
    && "PushManager" in window
    && "Notification" in window;
}

export default function usePushNotifications() {
  const [state, setState] = useState({
    status: "loading",
    loading: true,
    message: "",
  });
  const [configuration, setConfiguration] = useState(null);

  const inspect = useCallback(async ({ signal } = {}) => {
    if (!browserSupportsPush()) {
      setState({ status: "unsupported", loading: false, message: "" });
      return;
    }

    setState((current) => ({ ...current, loading: true, message: "" }));
    try {
      const config = await fetchPushConfiguration({ signal });
      setConfiguration(config);
      if (!config.supported || !config.public_key) {
        setState({ status: "unconfigured", loading: false, message: "" });
        return;
      }

      if (Notification.permission === "denied") {
        setState({ status: "denied", loading: false, message: "" });
        return;
      }

      const registration = await getReadyServiceWorker();
      const subscription = await registration?.pushManager.getSubscription();
      setState({
        status: subscription && config.subscribed ? "enabled" : "disabled",
        loading: false,
        message: "",
      });
    } catch (error) {
      if (error.name !== "AbortError") {
        setState({ status: "error", loading: false, message: error.message || "" });
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    inspect({ signal: controller.signal });
    return () => controller.abort();
  }, [inspect]);

  const enable = useCallback(async () => {
    if (!configuration?.public_key) return;
    setState((current) => ({ ...current, loading: true, message: "" }));

    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setState({ status: permission === "denied" ? "denied" : "disabled", loading: false, message: "" });
        return;
      }

      const registration = await getReadyServiceWorker();
      if (!registration) throw new Error("A aplicação segura ainda não está disponível neste navegador.");

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(configuration.public_key),
      });
      await savePushSubscription(subscription.toJSON());
      setState({ status: "enabled", loading: false, message: "" });
    } catch (error) {
      setState({ status: "error", loading: false, message: error.message || "" });
    }
  }, [configuration]);

  const disable = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, message: "" }));
    try {
      const registration = await getReadyServiceWorker();
      const subscription = await registration?.pushManager.getSubscription();
      if (subscription) {
        await removePushSubscription(subscription.endpoint);
        await subscription.unsubscribe();
      }
      setState({ status: "disabled", loading: false, message: "" });
    } catch (error) {
      setState({ status: "error", loading: false, message: error.message || "" });
    }
  }, []);

  return { ...state, enable, disable, refresh: inspect };
}
