export type JobStatus =
  | "queued"
  | "downloading"
  | "processing"
  | "done"
  | "error"
  | "cancelled";

export type DownloadKind = "video" | "audio";
export type AudioFormat = "mp3" | "m4a";
export type PlaylistQuality = 2160 | 1440 | 1080 | 720 | 480 | 360;

export interface VideoFormat {
  format_id: string;
  label: string;
  ext: string;
  height: number | null;
  filesize: number | null;
}

export interface VideoInfo {
  kind: "video";
  id: string;
  title: string;
  channel: string;
  duration: number;
  thumbnail: string | null;
  formats: VideoFormat[];
}

export interface PlaylistItem {
  id: string;
  title: string;
  duration: number;
  thumbnail: string | null;
}

export interface PlaylistInfo {
  kind: "playlist";
  id: string;
  title: string;
  channel: string;
  video_count: number;
  duration: number;
  thumbnail: string | null;
  items: PlaylistItem[];
}

export type MediaInfo = VideoInfo | PlaylistInfo;

export interface PlaylistProgress {
  total_items: number;
  completed_items: number;
  current_item: number | null;
  current_title: string | null;
  skipped_items: number;
}

export interface JobState {
  id: string;
  status: JobStatus;
  percent: number;
  speed: string | null;
  eta: number | null;
  filename: string | null;
  error: string | null;
  created_at: string;
  playlist: PlaylistProgress | null;
}

export interface DownloadPayload {
  url: string;
  kind: DownloadKind;
  format_id: string | null;
  audio_format: AudioFormat;
  max_height?: PlaylistQuality | null;
  video_ids?: string[] | null;
}

export interface DownloadAccepted {
  job_id: string;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
  };
}
