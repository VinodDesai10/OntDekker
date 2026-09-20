import { AppLayout } from "@/components/navigation/AppLayout";
import CommunityDetailView from "@/views/Communities/CommunityDetailView";

export const metadata = {
  title: "Community",
  description: "View community details, rules, and recent discussions on OntDekker.",
};

export default function CommunityDetailPage() {
  return (
    <AppLayout>
      <CommunityDetailView />
    </AppLayout>
  );
}
