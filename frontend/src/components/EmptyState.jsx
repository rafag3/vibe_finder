import { motion } from "framer-motion";

export default function EmptyState() {
  return (
    <motion.section
      className="empty-state"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3, duration: 0.5 }}
    >
      <div className="empty-orb" aria-hidden="true" />
      <p>Descreva como você tá se sentindo e a playlist aparece aqui.</p>
    </motion.section>
  );
}
