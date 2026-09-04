import { useMemo } from "react";
import MoodTile from "./MoodTile";

const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

// grade dinâmica: cresce com o número de faixas, em vez de um tamanho
// fixo sempre igual. Poucas faixas -> grade pequena e cheia; muitas
// faixas -> grade maior, mas ainda densa (não vira um mar vazio nem um
// aglomerado ilegível). ~2.2 células por faixa dá folga suficiente pro
// findFreeCell não precisar espalhar demais em espiral.
function computeGridSize(trackCount) {
  const targetCells = Math.max(24, Math.ceil(trackCount * 2.2));
  const cols = Math.max(6, Math.round(Math.sqrt(targetCells * (4 / 3))));
  const rows = Math.max(4, Math.ceil(targetCells / cols));
  return { cols, rows };
}

// busca em anéis crescentes ao redor da célula ideal até achar uma livre -
// é o que evita ícones se sobrepondo quando várias faixas têm valência/
// energia parecidas (comum: "triste" agrupa muita coisa na mesma região)
function findFreeCell(idealCol, idealRow, occupied, cols, rows) {
  const maxRadius = Math.max(cols, rows);
  for (let radius = 0; radius <= maxRadius; radius++) {
    for (let dc = -radius; dc <= radius; dc++) {
      for (let dr = -radius; dr <= radius; dr++) {
        if (Math.max(Math.abs(dc), Math.abs(dr)) !== radius) continue;
        const col = idealCol + dc;
        const row = idealRow + dr;
        if (col < 0 || col >= cols || row < 0 || row >= rows) continue;
        const key = `${col}-${row}`;
        if (!occupied.has(key)) return { col, row, key };
      }
    }
  }
  // grade cheia (não deveria acontecer com playlists normais) - sobrepõe
  return { col: idealCol, row: idealRow, key: `${idealCol}-${idealRow}-overflow-${Math.random()}` };
}

// escala adaptativa: em vez do intervalo fixo 0-1, usa o min/max real das
// faixas retornadas. Sem isso, um mood específico (que naturalmente ocupa
// só uma região pequena do espaço emocional) deixa o mapa vazio - a maioria
// da tela sem nada. Estica pra preencher o canvas sempre, mostrando as
// diferenças RELATIVAS entre as faixas dessa playlist (não mais a posição
// absoluta no espectro triste-feliz entre buscas diferentes).
function buildScale(values) {
  const min = Math.min(...values);
  const max = Math.min(...values) === Math.max(...values) ? min + 1 : Math.max(...values);
  const padding = (max - min) * 0.12; // não deixa ícone colado na borda
  const paddedMin = min - padding;
  const paddedMax = max + padding;
  return (v) => (v - paddedMin) / (paddedMax - paddedMin);
}

function layoutTracks(tracks) {
  const { cols, rows } = computeGridSize(tracks.length);
  const scaleValence = buildScale(tracks.map((t) => t.valence));
  const scaleEnergy = buildScale(tracks.map((t) => t.energy));

  const occupied = new Set();
  const placed = tracks.map((track) => {
    const idealCol = clamp(Math.round(scaleValence(track.valence) * (cols - 1)), 0, cols - 1);
    const idealRow = clamp(Math.round((1 - scaleEnergy(track.energy)) * (rows - 1)), 0, rows - 1); // energia alta = topo
    const { col, row, key } = findFreeCell(idealCol, idealRow, occupied, cols, rows);
    occupied.add(key);
    return { track, col, row };
  });

  return { placed, cols, rows };
}

export default function MoodMap({ tracks, nowPlayingId, resolvingTrackId, onPlay }) {
  const { placed, cols, rows } = useMemo(() => layoutTracks(tracks), [tracks]);

  return (
    <div className="mood-map">
      <span className="mood-map__axis-label mood-map__axis-label--top">energia alta</span>
      <span className="mood-map__axis-label mood-map__axis-label--bottom">energia baixa</span>
      <span className="mood-map__axis-label mood-map__axis-label--left">vibe pesada</span>
      <span className="mood-map__axis-label mood-map__axis-label--right">vibe leve</span>

      <span className="mood-map__quadrant mood-map__quadrant--tl">tensão, fúria</span>
      <span className="mood-map__quadrant mood-map__quadrant--tr">euforia, hino</span>
      <span className="mood-map__quadrant mood-map__quadrant--bl">sofrência</span>
      <span className="mood-map__quadrant mood-map__quadrant--br">chill, paz</span>

      <div className="mood-map__axis mood-map__axis--v" />
      <div className="mood-map__axis mood-map__axis--h" />

      <div className="mood-map__grid">
        {placed.map(({ track, col, row }) => (
          <MoodTile
            key={track.id}
            track={track}
            col={col}
            row={row}
            cols={cols}
            rows={rows}
            isPlaying={nowPlayingId === track.id}
            isResolving={resolvingTrackId === track.id}
            onPlay={onPlay}
          />
        ))}
      </div>
    </div>
  );
}
