import { AppLayout } from "@/components/navigation/AppLayout";
import EditCommunityView from "@/views/Communities/EditCommunityView";

export const metadata = {
  title: "Edit Community",
  description: "Edit community settings on OntDekker.",
};

export default function EditCommunityPage() {
  return (
    <AppLayout>
      <EditCommunityView />
    </AppLayout>
  );
}
