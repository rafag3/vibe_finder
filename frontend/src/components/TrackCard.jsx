import { motion } from "framer-motion";

export default function TrackCard({ track, index, isPlaying, onPlay }) {
  const thumbUrl = track.youtube_video_id
    ? `https://i.ytimg.com/vi/${track.youtube_video_id}/mqdefault.jpg`
    : null;

  return (
    <motion.article
      className={`track-card${isPlaying ? " track-card--playing" : ""}`}
      onClick={() => onPlay(track)}
      whileHover={{ scale: 1.16, zIndex: 30 }}
      transition={{ type: "spring", stiffness: 320, damping: 22 }}
      style={{ zIndex: isPlaying ? 25 : 1 }}
    >
      <div
        className="track-thumb"
        style={thumbUrl ? { backgroundImage: `url(${thumbUrl})` } : undefined}
      >
        {!isPlaying && (
          <span className="track-thumb__index">{String(index + 1).padStart(2, "0")}</span>
        )}
        {isPlaying && <span className="track-thumb__badge">tocando</span>}
        <span className="track-thumb__play" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M8 5l12 7-12 7V5z" /></svg>
        </span>
      </div>
      <div className="track-info">
        <h3>{track.title}</h3>
        <p>{track.artist}</p>
      </div>
    </motion.article>
  );
}
