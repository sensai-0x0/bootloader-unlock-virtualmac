import { Dial } from "./components/Dial";
import { RouterProvider, useRouter } from "./router";
import { CampaignOverviewView } from "./views/CampaignOverviewView";
import { SweepFindingsView } from "./views/SweepFindingsView";

function Routes() {
  const { path } = useRouter();
  return path === "/campaign" ? <CampaignOverviewView /> : <SweepFindingsView />;
}

export function App() {
  return (
    <RouterProvider>
      <Dial />
      <Routes />
    </RouterProvider>
  );
}
