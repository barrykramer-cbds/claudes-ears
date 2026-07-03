import { queryOptions } from "@tanstack/react-query";
import { fetchLibrary } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function libraryQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.library.list,
    queryFn: fetchLibrary,
    staleTime: 30_000,
  });
}
