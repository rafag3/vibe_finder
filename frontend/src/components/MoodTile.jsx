import { motion } from "framer-motion";

export default function MoodTile({ track, col, row, cols, rows, isPlaying, isResolving, onPlay }) {
  // capa vem grátis na busca (iTunes, sem cota) - o video_id só é resolvido
  // no play (YouTube, com cota). São fontes diferentes de propósito.
  const thumbUrl = track.cover_url || null;

  return (
    <motion.article
      className={`mood-tile${isPlaying ? " mood-tile--playing" : ""}${isResolving ? " mood-tile--resolving" : ""}`}
      style={{
        left: `${(col / cols) * 100}%`,
        top: `${(row / rows) * 100}%`,
        width: `${100 / cols}%`,
        height: `${100 / rows}%`,
      }}
      onClick={() => onPlay(track)}
      whileHover={{ scale: 1.6, zIndex: 40 }}
      transition={{ type: "spring", stiffness: 340, damping: 24 }}
    >
      <div
        className="mood-tile__thumb"
        style={thumbUrl ? { backgroundImage: `url(${thumbUrl})` } : undefined}
      >
        {/* sem cover_url = a busca no iTunes não achou capa pra essa música
            (raro, mas acontece com faixas menos conhecidas) - ícone
            genérico só nesse caso, não por causa do vídeo do YouTube
            (esse é resolvido à parte, só no play) */}
        {!thumbUrl && (
          <svg className="mood-tile__placeholder-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
        )}
        {isPlaying && <span className="mood-tile__badge" aria-hidden="true" />}
        {isResolving && <span className="mood-tile__spinner" aria-hidden="true" />}
      </div>
      <div className="mood-tile__tooltip">
        <p>{track.title}</p>
        <p>{track.artist}</p>
      </div>
    </motion.article>
  );
}
