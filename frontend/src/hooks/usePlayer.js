import { useCallback, useEffect, useRef, useState } from "react";
import { getTrackVideo } from "../api";

const ERROR_MESSAGES = {
  2: "vídeo inválido",
  5: "erro ao carregar o vídeo",
  100: "vídeo indisponível",
  101: "vídeo bloqueado pra reprodução externa",
  150: "vídeo bloqueado pra reprodução externa",
};

function loadYouTubeApi() {
  return new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }
    window.onYouTubeIframeAPIReady = resolve;
    if (document.getElementById("yt-iframe-api")) return;
    const tag = document.createElement("script");
    tag.id = "yt-iframe-api";
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
  });
}

/**
 * Player com dois modos:
 *  - YouTube (padrão): música inteira, resolvida sob demanda no play.
 *  - Preview de 30s (fallback): quando o YouTube esgota todos os
 *    candidatos (cota estourada, todos os uploads bloqueados) ou nem
 *    consegue resolver a busca, cai pra um preview de 30s via iTunes
 *    (mesma fonte já usada pra capa - sem cota, sem chave) em vez de
 *    simplesmente desistir da faixa.
 *
 * onTrackResolved(track) atualiza o objeto da faixa na lista de quem
 * chamou o hook (App) com o video_id real - troca o ícone genérico pela
 * capa de verdade (a capa em si já vem de graça no /generate, isso é só
 * pro estado "tocando"/candidatos).
 */
export function usePlayer(tracks, onTrackResolved) {
  const [nowPlaying, setNowPlaying] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolumeState] = useState(100);
  const [playerError, setPlayerError] = useState(null);
  const [resolvingTrackId, setResolvingTrackId] = useState(null);
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  const ytPlayerRef = useRef(null);
  const playerReadyRef = useRef(false);
  const audioRef = useRef(null);
  const previewModeRef = useRef(false);
  const currentTrackRef = useRef(null);
  const candidateQueueRef = useRef([]);
  const pendingVideoIdRef = useRef(null);
  const containerIdRef = useRef("yt-player");
  const errorTimeoutRef = useRef(null);
  const tracksRef = useRef(tracks);
  tracksRef.current = tracks;
  const currentIndexRef = useRef(-1);
  const goToOffsetRef = useRef(() => {});

  function getAudio() {
    if (!audioRef.current) {
      const audio = new Audio();
      audio.addEventListener("play", () => setIsPlaying(true));
      audio.addEventListener("pause", () => setIsPlaying(false));
      audio.addEventListener("ended", () => goToOffsetRef.current(1));
      audioRef.current = audio;
    }
    return audioRef.current;
  }

  const playPreview = useCallback((track) => {
    if (!track.preview_url) {
      setPlayerError(`"${track.title}" não tem prévia disponível. Pulando pra próxima.`);
      clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = setTimeout(() => setPlayerError(null), 4000);
      goToOffsetRef.current(1);
      return;
    }
    if (ytPlayerRef.current && playerReadyRef.current) ytPlayerRef.current.pauseVideo();
    previewModeRef.current = true;
    setIsPreviewMode(true);
    const audio = getAudio();
    audio.src = track.preview_url;
    audio.volume = (isMuted ? 0 : volume) / 100;
    audio.play().catch(() => {});
  }, [isMuted, volume]);

  const createPlayer = useCallback((videoId) => {
    ytPlayerRef.current = new window.YT.Player(containerIdRef.current, {
      videoId,
      playerVars: { autoplay: 1, playsinline: 1, rel: 0 },
      events: {
        onReady: (e) => {
          playerReadyRef.current = true;
          setVolumeState(e.target.getVolume());
          setIsMuted(e.target.isMuted());
          if (pendingVideoIdRef.current && pendingVideoIdRef.current !== videoId) {
            e.target.loadVideoById(pendingVideoIdRef.current);
          }
          pendingVideoIdRef.current = null;
        },
        onStateChange: (e) => {
          const YTS = window.YT.PlayerState;
          setIsPlaying(e.data === YTS.PLAYING);
          if (e.data === YTS.ENDED) goToOffsetRef.current(1);
        },
        onError: (e) => {
          if (candidateQueueRef.current.length > 0) {
            loadVideo(candidateQueueRef.current.shift());
            return;
          }
          // esgotou todos os candidatos do YouTube - tenta o preview de
          // 30s antes de desistir da faixa de vez
          if (currentTrackRef.current?.preview_url) {
            playPreview(currentTrackRef.current);
            return;
          }
          setIsPlaying(false);
          setPlayerError(
            `${ERROR_MESSAGES[e.data] || "não pôde ser reproduzido"} (sem alternativa disponível). Pulando pra próxima.`
          );
          clearTimeout(errorTimeoutRef.current);
          errorTimeoutRef.current = setTimeout(() => setPlayerError(null), 4000);
          goToOffsetRef.current(1);
        },
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playPreview]);

  const loadVideo = useCallback(
    (videoId) => {
      if (!videoId) return;
      previewModeRef.current = false;
      setIsPreviewMode(false);
      if (audioRef.current) audioRef.current.pause();
      if (ytPlayerRef.current && playerReadyRef.current) {
        ytPlayerRef.current.loadVideoById(videoId);
        return;
      }
      pendingVideoIdRef.current = videoId;
      if (ytPlayerRef.current) return;
      loadYouTubeApi().then(() => createPlayer(pendingVideoIdRef.current));
    },
    [createPlayer]
  );

  // resolve o video_id da faixa (busca na API se ainda não tiver, senão usa
  // o que já veio cacheado) e começa a tocar
  const resolveAndPlay = useCallback(
    async (track, index) => {
      currentIndexRef.current = index;
      setCurrentIndex(index);
      setNowPlaying(track);
      currentTrackRef.current = track;

      let resolved = track;
      if (!track.youtube_video_id) {
        setResolvingTrackId(track.id);
        try {
          const video = await getTrackVideo(track.id);
          resolved = { ...track, youtube_video_id: video.youtube_video_id, youtube_alt_ids: video.youtube_alt_ids };
          onTrackResolved?.(resolved);
        } catch {
          // busca do YouTube nem completou (rede/cota) - cai pro preview
          // de 30s em vez de perder a faixa inteira
          setResolvingTrackId(null);
          currentTrackRef.current = track;
          setNowPlaying(track);
          playPreview(track);
          return;
        }
        setResolvingTrackId(null);
      }

      setNowPlaying(resolved);
      currentTrackRef.current = resolved;
      candidateQueueRef.current = [resolved.youtube_video_id, ...(resolved.youtube_alt_ids || [])].filter(Boolean);
      loadVideo(candidateQueueRef.current.shift());
    },
    [loadVideo, onTrackResolved, playPreview]
  );

  const play = useCallback(
    (track) => {
      const idx = tracksRef.current.findIndex((t) => t.id === track.id);
      resolveAndPlay(track, idx);
    },
    [resolveAndPlay]
  );

  // usado por next/prev/onEnded/onError - navega N posições a partir do
  // índice atual, sem duplicar a lógica de resolução acima. Guardado em
  // ref (não useCallback) pra quebrar a dependência circular com
  // resolveAndPlay sem precisar duplicar a chamada em cada callback do
  // player (onEnded, onError) e nos controles (next/prev).
  goToOffsetRef.current = function goToOffset(offset) {
    const newIdx = currentIndexRef.current + offset;
    const track = tracksRef.current[newIdx];
    if (!track) return;
    resolveAndPlay(track, newIdx);
  };

  const hasNext = useCallback(() => currentIndex > -1 && currentIndex < tracks.length - 1, [currentIndex, tracks]);
  const hasPrev = useCallback(() => currentIndex > 0, [currentIndex]);

  function next() {
    goToOffsetRef.current(1);
  }

  function prev() {
    if (previewModeRef.current && audioRef.current && audioRef.current.currentTime > 3) {
      audioRef.current.currentTime = 0;
      return;
    }
    if (!previewModeRef.current && ytPlayerRef.current && playerReadyRef.current && ytPlayerRef.current.getCurrentTime() > 3) {
      ytPlayerRef.current.seekTo(0, true);
      return;
    }
    goToOffsetRef.current(-1);
  }

  const togglePlay = useCallback(() => {
    if (previewModeRef.current) {
      if (!audioRef.current) return;
      if (isPlaying) audioRef.current.pause();
      else audioRef.current.play().catch(() => {});
      return;
    }
    if (!ytPlayerRef.current || !playerReadyRef.current) return;
    if (isPlaying) ytPlayerRef.current.pauseVideo();
    else ytPlayerRef.current.playVideo();
  }, [isPlaying]);

  const setVolume = useCallback((v) => {
    const clamped = Math.max(0, Math.min(100, Math.round(v)));
    setVolumeState(clamped);
    if (previewModeRef.current) {
      if (audioRef.current) audioRef.current.volume = clamped / 100;
      setIsMuted(clamped === 0);
      return;
    }
    if (!ytPlayerRef.current || !playerReadyRef.current) return;
    ytPlayerRef.current.setVolume(clamped);
    if (clamped === 0) {
      ytPlayerRef.current.mute();
      setIsMuted(true);
    } else if (isMuted) {
      ytPlayerRef.current.unMute();
      setIsMuted(false);
    }
  }, [isMuted]);

  const toggleMute = useCallback(() => {
    if (previewModeRef.current) {
      if (!audioRef.current) return;
      const nextMuted = !isMuted;
      audioRef.current.muted = nextMuted;
      setIsMuted(nextMuted);
      return;
    }
    if (!ytPlayerRef.current || !playerReadyRef.current) return;
    if (isMuted) {
      ytPlayerRef.current.unMute();
      setIsMuted(false);
      if (volume === 0) setVolume(50);
    } else {
      ytPlayerRef.current.mute();
      setIsMuted(true);
    }
  }, [isMuted, volume, setVolume]);

  useEffect(() => () => {
    clearTimeout(errorTimeoutRef.current);
    audioRef.current?.pause();
  }, []);

  return {
    nowPlaying,
    currentIndex,
    isPlaying,
    isMuted,
    volume,
    playerError,
    resolvingTrackId,
    isPreviewMode,
    containerId: containerIdRef.current,
    play,
    next,
    prev,
    hasNext,
    hasPrev,
    togglePlay,
    toggleMute,
    setVolume,
  };
}
