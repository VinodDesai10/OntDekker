import { AppLayout } from "@/components/navigation/AppLayout";
import TripsView from "@/views/Trips/TripsView";

export const metadata = {
  title: "Trips",
  description: "Discover and join expeditions from around the world.",
};

export default function TripsPage() {
  return (
    <AppLayout>
      <TripsView />
    </AppLayout>
  );
}
