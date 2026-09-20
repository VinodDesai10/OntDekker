export interface DialogProps {
  isOpen: boolean;
  /** Main heading of the confirmation dialog */
  title: string;
  /** Body message explaining the action */
  message: string;
  /** Label for the confirm button — defaults to "Confirm" */
  confirmLabel?: string;
  /** Label for the cancel button — defaults to "Cancel" */
  cancelLabel?: string;
  /** Called when the user confirms the action */
  onConfirm: () => void;
  /** Called when user cancels or clicks backdrop/Escape */
  onCancel: () => void;
  /**
   * When true the confirm button uses the danger (red) variant.
   * Use for destructive actions like Delete, Remove, Leave.
   */
  destructive?: boolean;
  /** Show a loading spinner on the confirm button while async action runs */
  loading?: boolean;
}
