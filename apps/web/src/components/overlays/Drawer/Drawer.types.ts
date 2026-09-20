export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  /** Heading shown in the drawer header */
  title: string;
  children: React.ReactNode;
  /** Additional Tailwind classes on the drawer panel */
  className?: string;
}
