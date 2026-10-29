import { useMutation } from "@tanstack/react-query";

import { fetchMediaInfo } from "../api/client";
import type { MediaInfo } from "../types";

export function useVideoInfo() {
  return useMutation<MediaInfo, Error, string>({
    mutationFn: fetchMediaInfo,
  });
}
