import { motion, useTransform } from "framer-motion";
import TrackCard from "./TrackCard";

const GENRE_LABELS = {
  sertanejo: "Sertanejo",
  pagode: "Pagode",
  funk: "Funk",
  forro: "Forró",
  mpb: "MPB",
  "bossa-nova": "Bossa Nova",
  "rock-nacional": "Rock Nacional",
  samba: "Samba",
  romantica: "Romântica",
  "reggae-nacional": "Reggae",
  pop: "Pop",
  rock: "Rock",
  "hip-hop": "Hip-Hop",
  synthpop: "Synthpop",
  ambient: "Ambient",
  classical: "Clássica",
  country: "Country",
  alternative: "Alternative",
  indie: "Indie",
  soul: "Soul",
  funk_en: "Funk (US)",
  jazz: "Jazz",
  folk: "Folk",
  edm: "EDM",
  soundtrack: "Trilha Sonora",
};

// linhas alternam direção do parallax (algumas seguem o mouse, outras vão
// contra) - é o que dá a sensação de profundidade/camadas, não só um
// deslocamento uniforme de tudo junto
function depthForIndex(index) {
  const base = 18 + (index % 3) * 10; // varia a intensidade por linha
  const direction = index % 2 === 0 ? 1 : -1;
  return base * direction;
}

export default function GenreRow({ genre, tracks, index, mouseX, nowPlayingId, onPlay }) {
  const depth = depthForIndex(index);
  const x = useTransform(mouseX, [-1, 1], [-depth, depth]);

  return (
    <section className="genre-row">
      <h2 className="genre-row__title">{GENRE_LABELS[genre] || genre}</h2>
      <motion.div className="genre-row__track" style={{ x }}>
        {tracks.map((track, i) => (
          <TrackCard
            key={track.id}
            track={track}
            index={i}
            isPlaying={nowPlayingId === track.id}
            onPlay={onPlay}
          />
        ))}
      </motion.div>
    </section>
  );
}
