import { motion } from "framer-motion";

// puramente decorativo, position: fixed atrás de tudo - dois blobs de
// gradiente com animação lenta em loop, mais uma grade sutil. É o que dá
// a sensação "futurista" de profundidade sem competir com o conteúdo.
export default function Background() {
  return (
    <div className="bg-scene" aria-hidden="true">
      <motion.div
        className="bg-blob bg-blob--violet"
        animate={{ x: [0, 60, -40, 0], y: [0, -40, 30, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="bg-blob bg-blob--cyan"
        animate={{ x: [0, -70, 50, 0], y: [0, 50, -30, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="bg-grid" />
    </div>
  );
}
