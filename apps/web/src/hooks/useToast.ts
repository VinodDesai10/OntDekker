/**
 * useToast
 *
 * Public hook for triggering toasts from any component in the application.
 *
 * Usage:
 *   const { showToast, dismissToast } = useToast();
 *
 *   showToast("Expedition saved.", "success");
 *   showToast("Something went wrong.", "error");
 *   showToast("Invite sent.");          // defaults to "info"
 *
 * The hook must be called inside a component that is a descendant of
 * <ToastProvider> (already wired into the AppShell in page.tsx).
 */

export { useToastContext as useToast } from "@/components/overlays/Toast";
