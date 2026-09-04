import { motion, AnimatePresence } from "framer-motion";

export default function PlayerDock({ player }) {
  const { nowPlaying, isPlaying, isMuted, volume, hasNext, containerId, isPreviewMode } = player;

  return (
    <AnimatePresence>
      {nowPlaying && (
        <motion.div
          className="player-dock"
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
          <div className="player-video">
            <div id={containerId} style={isPreviewMode ? { display: "none" } : undefined} />
            {isPreviewMode && (
              <div className="player-video__preview-badge">
                <span>prévia 30s</span>
              </div>
            )}
          </div>

          <div className="player-body">
            <div className="player-meta">
              <p>{nowPlaying?.title}</p>
              <p>{nowPlaying?.artist}</p>
              {isPreviewMode && (
                <p className="player-meta__note">YouTube indisponível - tocando prévia de 30s</p>
              )}
            </div>

            <div className="player-controls">
              <button
                type="button"
                className="pc-btn"
                onClick={player.prev}
                disabled={player.currentIndex < 0}
                aria-label="Faixa anterior"
                title="Anterior"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 6v12M18 6l-8 6 8 6V6z" /></svg>
              </button>

              <button
                type="button"
                className="pc-btn pc-btn--primary"
                onClick={player.togglePlay}
                aria-label={isPlaying ? "Pausar" : "Tocar"}
                title={isPlaying ? "Pausar" : "Tocar"}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d={isPlaying ? "M8 5h3v14H8zM13 5h3v14h-3z" : "M8 5l12 7-12 7V5z"} />
                </svg>
              </button>

              <button
                type="button"
                className="pc-btn"
                onClick={player.next}
                disabled={!hasNext()}
                aria-label="Próxima faixa"
                title="Próxima"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 6v12M6 6l8 6-8 6V6z" /></svg>
              </button>

              <div className="pc-volume">
                <button
                  type="button"
                  className="pc-btn"
                  onClick={player.toggleMute}
                  aria-label={isMuted || volume === 0 ? "Ativar som" : "Mutar"}
                  title={isMuted || volume === 0 ? "Ativar som" : "Mutar"}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 9v6h4l5 4V5L8 9H4z" />
                    {!isMuted && volume > 0 && (
                      <path d="M16 8.5a4 4 0 010 7M18.5 6a7.5 7.5 0 010 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    )}
                    {(isMuted || volume === 0) && (
                      <path d="M17 9l5 6M22 9l-5 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    )}
                  </svg>
                </button>
                <input
                  type="range"
                  className="pc-slider"
                  min="0"
                  max="100"
                  step="1"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => player.setVolume(e.target.value)}
                  aria-label="Volume"
                />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
