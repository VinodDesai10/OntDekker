import { AppLayout } from "@/components/navigation/AppLayout";
import MyGuidesView from "@/views/Guides/MyGuides/MyGuidesView";

export const metadata = {
  title: "My Guides",
  description: "Guides you have saved or connected with.",
};

export default function MyGuidesPage() {
  return (
    <AppLayout>
      <MyGuidesView />
    </AppLayout>
  );
}
