import { useState } from "react";
import Header from "./components/Header";
import Hero from "./components/Hero";
import EmptyState from "./components/EmptyState";
import SkeletonGrid from "./components/SkeletonGrid";
import MoodMap from "./components/MoodMap";
import PlayerDock from "./components/PlayerDock";
import Background from "./components/Background";
import { generatePlaylist } from "./api";
import { usePlayer } from "./hooks/usePlayer";

export default function App() {
  const [mood, setMood] = useState("");
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // quando uma faixa é resolvida (video_id buscado na hora do play), troca
  // o objeto dela na lista - é isso que atualiza o ícone genérico pra capa
  // real na tela sem precisar gerar a playlist de novo
  function handleTrackResolved(resolved) {
    setTracks((prev) => prev.map((t) => (t.id === resolved.id ? { ...t, ...resolved } : t)));
  }

  const player = usePlayer(tracks, handleTrackResolved);

  async function handleSubmit() {
    if (!mood.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await generatePlaylist(mood);
      setTracks(data.tracks);
    } catch (err) {
      // "Failed to fetch" é o erro cru do navegador quando nem consegue
      // completar a requisição (servidor fora do ar, porta errada, CORS
      // bloqueando) - mostrar isso direto pro usuário não ajuda em nada.
      const isNetworkError = err instanceof TypeError;
      setError(
        isNetworkError
          ? "Não consegui conectar ao servidor. Confirma se o backend (python app.py) tá rodando em localhost:5000."
          : err.message || "Algo deu errado. Tenta de novo."
      );
      setTracks([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Background />
      <Header />
      <main className="app-main">
        <Hero mood={mood} setMood={setMood} onSubmit={handleSubmit} loading={loading} error={error} />

        {loading && <SkeletonGrid />}
        {!loading && tracks.length === 0 && <EmptyState />}
        {!loading && tracks.length > 0 && (
          <section className="results">
            <MoodMap
              tracks={tracks}
              nowPlayingId={player.nowPlaying?.id}
              resolvingTrackId={player.resolvingTrackId}
              onPlay={player.play}
            />
          </section>
        )}

        {player.playerError && <p className="mood-error player-error-toast">{player.playerError}</p>}
      </main>

      <PlayerDock player={player} />
    </>
  );
}
