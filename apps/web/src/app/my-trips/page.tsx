import { AppLayout } from "@/components/navigation/AppLayout";
import MyTripsView from "@/views/Trips/MyTripsView";

export const metadata = {
  title: "My Trips",
  description: "Your expeditions — active, upcoming, and completed.",
};

export default function MyTripsPage() {
  return (
    <AppLayout>
      <MyTripsView />
    </AppLayout>
  );
}
