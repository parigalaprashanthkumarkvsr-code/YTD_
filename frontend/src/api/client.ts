import type {
  ApiErrorBody,
  DownloadAccepted,
  DownloadPayload,
  MediaInfo,
} from "../types";

const configuredBase = import.meta.env.VITE_API_BASE as string | undefined;
const API_BASE = (configuredBase?.trim() || "/api").replace(/\/+$/, "");

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code = "INTERNAL", status = 0) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
  }
}

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiClientError(
      "Could not reach the server. Is the backend running?",
      "INTERNAL",
      0,
    );
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiClientError(
      body?.error?.message ?? "The request failed. Please try again.",
      body?.error?.code ?? "INTERNAL",
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function fetchMediaInfo(url: string): Promise<MediaInfo> {
  return request<MediaInfo>("/info", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function createDownload(payload: DownloadPayload): Promise<DownloadAccepted> {
  return request<DownloadAccepted>("/downloads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelDownload(jobId: string): Promise<void> {
  await request<void>(`/downloads/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
}

export function jobFileUrl(jobId: string): string {
  return apiUrl(`/downloads/${encodeURIComponent(jobId)}/file`);
}

export function jobEventsUrl(jobId: string): string {
  return apiUrl(`/downloads/${encodeURIComponent(jobId)}/events`);
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
