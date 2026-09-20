import { AppLayout } from "@/components/navigation/AppLayout";
import GuideApplyView from "@/views/Guides/GuideApplyView";

export const metadata = {
  title: "Become a Guide",
  description: "Apply to become a verified guide on OntDekker.",
};

export default function GuideApplyPage() {
  return (
    <AppLayout>
      <GuideApplyView />
    </AppLayout>
  );
}
