const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

export async function generatePlaylist(mood) {
  const res = await fetch(`${API_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Algo deu errado. Tenta de novo.");
  }
  return data;
}

export async function getTrackVideo(trackId) {
  const res = await fetch(`${API_URL}/tracks/${trackId}/video`);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Não consegui carregar essa música.");
  }
  return data;
}
