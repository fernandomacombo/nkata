import { useEffect, useState } from "react";
import { fetchMoments, groupMomentsByProfile, MOMENTS_REFRESH_MS } from "../../services/momentsApi.js";
import AutoplayMomentViewer from "./AutoplayMomentViewer.jsx";
import MomentCarousel from "./MomentCarousel.jsx";

export default function HomeMoments({ english, onCreate, onOpenProfile }) {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewer, setViewer] = useState(null);

  useEffect(() => {
    let activeRequest;
    let stopped = false;
    async function refresh() {
      if (stopped || activeRequest || document.hidden) return;
      const controller = new AbortController();
      activeRequest = controller;
      try {
        const data = await fetchMoments({ signal: controller.signal });
        if (!stopped) setGroups(groupMomentsByProfile(data.results || []));
      } catch {
        // Keep the visible feed on temporary network errors.
      } finally {
        activeRequest = undefined;
        if (!stopped) setLoading(false);
      }
    }

    refresh();
    const timer = window.setInterval(refresh, MOMENTS_REFRESH_MS);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      stopped = true;
      activeRequest?.abort();
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, []);

  return (
    <div className="nk-home-moments">
      <MomentCarousel
        groups={groups}
        loading={loading}
        english={english}
        onCreate={onCreate}
        onOpen={(group) => setViewer({ groups, index: groups.indexOf(group) })}
      />
      {viewer && (
        <AutoplayMomentViewer
          groups={viewer.groups}
          initialGroupIndex={viewer.index}
          onClose={() => setViewer(null)}
          onOpenProfile={(profile) => {
            setViewer(null);
            onOpenProfile(profile);
          }}
        />
      )}
    </div>
  );
}
