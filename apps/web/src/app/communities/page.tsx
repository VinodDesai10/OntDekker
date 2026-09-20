import { AppLayout } from "@/components/navigation/AppLayout";
import CommunitiesView from "@/views/Communities/CommunitiesView";

export const metadata = {
  title: "Communities",
  description: "Discover and join travel communities on OntDekker.",
};

export default function CommunitiesPage() {
  return (
    <AppLayout>
      <CommunitiesView />
    </AppLayout>
  );
}
