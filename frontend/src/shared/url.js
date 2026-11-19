// Page state that belongs in the URL (current view, filters, period), so refresh, Back and shared links work.
import { useSearchParams } from "react-router-dom";

/**
 * Like useState, but the value lives in the query string: ?key=value.
 * The default value is left out of the URL to keep links short.
 * replace=true updates the URL without adding a Back step (good for filters typed or picked often).
 */
export function useQueryState(key, fallback = "", { replace = false } = {}) {
  const [params, setParams] = useSearchParams();
  const value = params.get(key) ?? fallback;
  const set = (v) =>
    setParams((cur) => {
      const next = new URLSearchParams(cur);
      if (v === "" || v == null || String(v) === String(fallback)) next.delete(key);
      else next.set(key, String(v));
      return next;
    }, { replace });
  return [value, set];
}
