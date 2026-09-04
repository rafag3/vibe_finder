import { useMemo, useRef } from "react";
import { useMotionValue } from "framer-motion";
import GenreRow from "./GenreRow";

function groupByGenre(tracks) {
  const groups = [];
  const index = new Map();
  for (const track of tracks) {
    const genre = track.genre || "outros";
    if (!index.has(genre)) {
      index.set(genre, groups.length);
      groups.push({ genre, tracks: [] });
    }
    groups[index.get(genre)].tracks.push(track);
  }
  return groups;
}

export default function ResultsGrid({ tracks, nowPlayingId, onPlay }) {
  const containerRef = useRef(null);
  // valor de movimento puro (sem passar por state/re-render do React) -
  // com várias linhas escutando o mouse a cada pixel, useState aqui
  // geraria um re-render inteiro da árvore por frame e travaria a UI.
  const mouseX = useMotionValue(0);
  const groups = useMemo(() => groupByGenre(tracks), [tracks]);

  function handleMouseMove(e) {
    const rect = containerRef.current.getBoundingClientRect();
    const relativeX = (e.clientX - rect.left) / rect.width; // 0..1
    mouseX.set(relativeX * 2 - 1); // -1..1
  }

  return (
    <div className="results-grid" ref={containerRef} onMouseMove={handleMouseMove}>
      {groups.map((group, i) => (
        <GenreRow
          key={group.genre}
          genre={group.genre}
          tracks={group.tracks}
          index={i}
          mouseX={mouseX}
          nowPlayingId={nowPlayingId}
          onPlay={onPlay}
        />
      ))}
    </div>
  );
}
