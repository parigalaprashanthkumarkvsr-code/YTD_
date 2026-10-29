import { useEffect, useRef, useState } from "react";

import { getErrorMessage } from "./api/client";
import { ErrorBanner } from "./components/ErrorBanner";
import { FormatPicker } from "./components/FormatPicker";
import { HistoryList } from "./components/HistoryList";
import { LegalNotice } from "./components/LegalNotice";
import { Logo } from "./components/Logo";
import { PlaylistItemList } from "./components/PlaylistItemList";
import { PlaylistOptions } from "./components/PlaylistOptions";
import { ProgressBar } from "./components/ProgressBar";
import { SkeletonCard } from "./components/SkeletonCard";
import { SuccessCard } from "./components/SuccessCard";
import { ThemeToggle } from "./components/ThemeToggle";
import { UrlForm } from "./components/UrlForm";
import { VideoCard } from "./components/VideoCard";
import { useDownload } from "./hooks/useDownload";
import { useHistory } from "./hooks/useHistory";
import { useVideoInfo } from "./hooks/useVideoInfo";
import { isYouTubeUrl } from "./lib/url";
import type {
  AudioFormat,
  DownloadKind,
  PlaylistQuality,
  VideoFormat,
} from "./types";

function pickDefaultFormat(formats: VideoFormat[]): string | null {
  const videos = formats.filter((format) => format.height !== null);
  return (
    videos.find((format) => format.height === 1080) ??
    videos.find((format) => format.height === 720) ??
    videos[0]
  )?.format_id ?? null;
}

export default function App() {
  const infoQuery = useVideoInfo();
  const download = useDownload();
  const { entries, add: addHistory, clear: clearHistory } = useHistory();

  const [kind, setKind] = useState<DownloadKind>("video");
  const [selectedFormatId, setSelectedFormatId] = useState<string | null>(null);
  const [audioFormat, setAudioFormat] = useState<AudioFormat>("mp3");
  const [quality, setQuality] = useState<PlaylistQuality | null>(1080);
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [lastUrl, setLastUrl] = useState<string | null>(null);
  const [formKey, setFormKey] = useState(0);
  const recordedJob = useRef<string | null>(null);

  const info = infoQuery.data ?? null;
  const job = download.job;
  const activeJob =
    job !== null &&
    (job.status === "queued" || job.status === "downloading" || job.status === "processing");

  function handleFetch(url: string) {
    if (!isYouTubeUrl(url)) {
      return;
    }
    if (activeJob) {
      void download.cancel();
    }
    download.reset();
    infoQuery.reset();
    setLastUrl(url);
    setSelectedFormatId(null);
    setSelectedVideoIds([]);
    setKind("video");
    setQuality(1080);
    infoQuery.mutate(url, {
      onSuccess: (data) => {
        if (data.kind === "playlist") {
          setSelectedVideoIds([]);
          setKind("video");
          setQuality(1080);
          return;
        }
        const preferred = pickDefaultFormat(data.formats);
        if (preferred) {
          setSelectedFormatId(preferred);
          setKind("video");
        } else {
          setKind("audio");
        }
      },
    });
  }

  function togglePlaylistVideo(videoId: string) {
    setSelectedVideoIds((current) =>
      current.includes(videoId)
        ? current.filter((id) => id !== videoId)
        : [...current, videoId],
    );
  }

  function selectAllPlaylistVideos() {
    if (info?.kind === "playlist") {
      setSelectedVideoIds(info.items.map((item) => item.id));
    }
  }

  function clearPlaylistVideos() {
    setSelectedVideoIds([]);
  }

  function handleStartDownload() {
    if (!info || !lastUrl) {
      return;
    }
    if (info.kind === "video" && kind === "video" && !selectedFormatId) {
      return;
    }
    if (info.kind === "playlist") {
      if (selectedVideoIds.length === 0) {
        return;
      }
      void download.start({
        url: lastUrl,
        kind,
        format_id: null,
        audio_format: audioFormat,
        max_height: kind === "video" ? quality : null,
        video_ids: selectedVideoIds,
      });
      return;
    }
    void download.start({
      url: lastUrl,
      kind,
      format_id: kind === "video" ? selectedFormatId : null,
      audio_format: audioFormat,
    });
  }

  function handleAnother() {
    download.reset();
    infoQuery.reset();
    setLastUrl(null);
    setSelectedFormatId(null);
    setSelectedVideoIds([]);
    setKind("video");
    setQuality(1080);
    setFormKey((value) => value + 1);
  }

  function retryInfo() {
    if (lastUrl) {
      handleFetch(lastUrl);
    }
  }

  useEffect(() => {
    if (!job || job.status !== "done" || !job.filename || !info) {
      return;
    }
    if (recordedJob.current === job.id) {
      return;
    }
    recordedJob.current = job.id;

    let label: string;
    if (info.kind === "playlist") {
      const qualityLabel =
        kind === "video"
          ? quality === null
            ? "best quality"
            : `${quality}p`
          : audioFormat.toUpperCase();
      const countLabel =
        selectedVideoIds.length === info.video_count
          ? `${info.video_count} ${info.video_count === 1 ? "video" : "videos"}`
          : `${selectedVideoIds.length} of ${info.video_count} videos`;
      label = `${countLabel} · ${qualityLabel}`;
    } else {
      const selectedVideo = info.formats.find(
        (format) => format.format_id === selectedFormatId,
      );
      label =
        kind === "video"
          ? (selectedVideo?.label ?? "video")
          : audioFormat.toUpperCase();
    }

    addHistory({
      jobId: job.id,
      title: info.title,
      channel: info.channel,
      kind,
      label,
      audioFormat: kind === "audio" ? audioFormat : null,
      filename: job.filename,
      completedAt: new Date().toISOString(),
    });
  }, [
    job,
    info,
    kind,
    selectedFormatId,
    selectedVideoIds,
    audioFormat,
    quality,
    addHistory,
  ]);

  const selectedVideo =
    info?.kind === "video"
      ? info.formats.find((format) => format.format_id === selectedFormatId)
      : undefined;
  const selectedCount = selectedVideoIds.length;
  const playlistItems =
    info?.kind === "playlist"
      ? selectedCount === info.video_count
        ? `${info.video_count} ${info.video_count === 1 ? "video" : "videos"}`
        : `${selectedCount} of ${info.video_count} videos`
      : "playlist";
  const actionLabel =
    info?.kind === "playlist"
      ? selectedCount === 0
        ? "select videos to download"
        : kind === "video"
          ? `download ${playlistItems} · ${quality === null ? "best" : `${quality}p`}`
          : `download ${playlistItems} · ${audioFormat.toUpperCase()}`
      : kind === "video"
        ? `download ${selectedVideo?.label ?? "video"}`
        : `download ${audioFormat.toUpperCase()}`;
  const infoError = infoQuery.error ? getErrorMessage(infoQuery.error) : null;
  const starting = download.starting;
  const showOptions = !job || job.status === "error" || job.status === "cancelled";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex w-full max-w-content items-center justify-between px-5 py-4 sm:px-6">
          <div>
            <h1 className="sr-only">YTD — YouTube downloader</h1>
            <Logo />
            <p className="mt-1 text-label text-muted">paste a url. get a file.</p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto w-full max-w-content flex-1 space-y-6 px-5 py-8 sm:px-6 sm:py-12">
        <UrlForm key={formKey} onSubmit={handleFetch} busy={infoQuery.isPending || starting} />

        {infoError ? (
          <ErrorBanner
            message={infoError}
            title="could not fetch link"
            onRetry={lastUrl ? retryInfo : undefined}
          />
        ) : null}

        {infoQuery.isPending ? <SkeletonCard /> : null}

        {info ? (
          <div className="space-y-6">
            <VideoCard info={info} />

            {showOptions ? (
              <>
                {info.kind === "video" ? (
                  <FormatPicker
                    formats={info.formats}
                    kind={kind}
                    onKindChange={setKind}
                    selectedFormatId={selectedFormatId}
                    onFormatChange={setSelectedFormatId}
                    audioFormat={audioFormat}
                    onAudioFormatChange={setAudioFormat}
                  />
                ) : (
                  <>
                    <PlaylistItemList
                      items={info.items}
                      selectedIds={selectedVideoIds}
                      onToggle={togglePlaylistVideo}
                      onSelectAll={selectAllPlaylistVideos}
                      onClear={clearPlaylistVideos}
                    />
                    <PlaylistOptions
                      kind={kind}
                      onKindChange={setKind}
                      quality={quality}
                      onQualityChange={setQuality}
                      audioFormat={audioFormat}
                      onAudioFormatChange={setAudioFormat}
                      selectedCount={selectedCount}
                    />
                  </>
                )}

                {!job ? (
                  <button
                    type="button"
                    onClick={handleStartDownload}
                    disabled={
                      starting ||
                      (info.kind === "playlist" && selectedCount === 0) ||
                      (info.kind === "video" &&
                        kind === "video" &&
                        !selectedFormatId)
                    }
                    className="inline-flex h-12 w-full items-center justify-center rounded bg-accent px-6 font-bold text-on-accent transition-colors hover:bg-accent-hover active:bg-accent-press disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {starting ? "starting download..." : actionLabel}
                  </button>
                ) : null}
              </>
            ) : null}

            {activeJob && job ? <ProgressBar job={job} onCancel={() => void download.cancel()} /> : null}

            {job?.status === "done" ? <SuccessCard job={job} onAnother={handleAnother} /> : null}

            {job?.status === "error" ? (
              <ErrorBanner
                message={job.error ?? "The download failed. Please try again."}
                title="download failed"
                onRetry={handleStartDownload}
                retryLabel="try again"
              />
            ) : null}

            {job?.status === "cancelled" ? (
              <ErrorBanner
                message={job.error ?? "Download cancelled."}
                title="cancelled"
                tone="muted"
                onRetry={handleStartDownload}
                retryLabel="start again"
              />
            ) : null}
          </div>
        ) : null}

        {download.error ? (
          <ErrorBanner
            message={download.error}
            title="could not start download"
            onRetry={lastUrl ? handleStartDownload : undefined}
          />
        ) : null}

        {!info && !infoQuery.isPending && !infoError ? (
          <ol className="grid gap-2 rounded-md border border-border bg-surface p-4 text-label text-muted sm:grid-cols-3 sm:p-5">
            {[
              "paste a video or playlist url",
              "pick video or audio",
              "save the file",
            ].map(
              (step, index) => (
                <li key={step} className="flex items-baseline gap-2">
                  <span className="text-accent" aria-hidden="true">
                    0{index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ),
            )}
          </ol>
        ) : null}

        <HistoryList entries={entries} onClear={clearHistory} />
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-content px-5 py-6 sm:px-6">
          <LegalNotice />
          <p className="mt-3 text-label text-muted">
            self-hosted · no accounts · files expire automatically
          </p>
        </div>
      </footer>
    </div>
  );
}
