import { AppLayout } from "@/components/navigation/AppLayout";
import CreateCommunityView from "@/views/Communities/CreateCommunityView";

export const metadata = {
  title: "Create Community",
  description: "Start a new travel community on OntDekker.",
};

export default function CreateCommunityPage() {
  return (
    <AppLayout>
      <CreateCommunityView />
    </AppLayout>
  );
}
