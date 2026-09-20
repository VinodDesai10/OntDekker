import { AppLayout } from "@/components/navigation/AppLayout";
import GuidesView from "@/views/Guides/GuidesView";

export const metadata = {
  title: "Guides",
  description: "Discover verified local guides for your next expedition.",
};

export default function GuidesPage() {
  return (
    <AppLayout>
      <GuidesView />
    </AppLayout>
  );
}
