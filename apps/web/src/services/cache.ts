/**
 * OntDekker SWR Cache Helpers
 *
 * Provides:
 *   1. Generic SWR fetchers backed by the shared Axios instance.
 *   2. Typed SWR key factories for Guide, Expedition, and Community domains.
 *
 * Usage:
 *   import useSWR from "swr";
 *   import { swrFetcherWithParams, guideKeys, expeditionKeys, communityKeys } from "@/services/cache";
 */

export { swrFetcher, swrFetcherWithParams } from "./cache/sharedCache";
export { guideKeys } from "./cache/guideCache";
export { expeditionKeys } from "./cache/expeditionCache";
export { communityKeys } from "./cache/communityCache";
export { feedKeys } from "./cache/feedCache";
export { tripKeys } from "./cache/tripCache";
