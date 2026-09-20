import { AppLayout } from "@/components/navigation/AppLayout";
import { FeedView } from "@/views/Feed";

export const metadata = {
  title: "Discover Feed",
  description: "Explore authentic travel stories from the OntDekker community.",
};

export default function FeedPage() {
  return (
    <AppLayout>
      <FeedView />
    </AppLayout>
  );
}
