/**
 * OntDekker — Shared SWR Fetchers
 *
 * Generic SWR fetcher utilities backed by the shared Axios instance.
 * Domain cache modules and consumers import from here (or via cache.ts).
 */

import apiClient from "../axios";

/**
 * Fetches the given URL using the shared Axios client and returns the
 * response body.  Errors thrown here are caught by SWR and surfaced in
 * the `error` field of the useSWR return value.
 */
export async function swrFetcher<T>(url: string): Promise<T> {
  const { data } = await apiClient.get<T>(url);
  return data;
}

/**
 * Fetcher with query params serialised from a [url, params] tuple key.
 * Use with useSWR([url, params], swrFetcherWithParams).
 */
export async function swrFetcherWithParams<T>(
  url: string,
  params: Record<string, unknown>,
): Promise<T> {
  const { data } = await apiClient.get<T>(url, { params });
  return data;
}
