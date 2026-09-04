import { motion } from "framer-motion";

export default function Hero({ mood, setMood, onSubmit, loading, error }) {
  function handleKeyDown(e) {
    // Enter envia; Shift+Enter quebra linha (padrão de textarea multi-linha)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  }

  return (
    <section className="hero">
      <motion.p
        className="hero-eyebrow"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        gerador de playlist
      </motion.p>
      <motion.h1
        className="hero-title"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        Qual é a vibe agora?
      </motion.h1>

      <motion.form
        className="mood-form"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <textarea
          value={mood}
          onChange={(e) => setMood(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={300}
          rows={2}
          placeholder="triste e com saudade, animado pra treinar, calmo pra estudar..."
          className="mood-input"
          disabled={loading}
        />
        <button type="submit" className="mood-submit" disabled={loading || !mood.trim()}>
          {loading ? "montando..." : "montar playlist"}
        </button>
      </motion.form>

      {error && <p className="mood-error">{error}</p>}
    </section>
  );
}
