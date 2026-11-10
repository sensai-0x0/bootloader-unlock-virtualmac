import { Dial } from "./components/Dial";
import { RouterProvider, useRouter } from "./router";
import { CampaignOverviewView } from "./views/CampaignOverviewView";
import { PostureView } from "./views/PostureView";
import { SweepFindingsView } from "./views/SweepFindingsView";

function Routes() {
  const { path } = useRouter();
  if (path === "/campaign") {
    return <CampaignOverviewView />;
  }
  if (path === "/posture") {
    return <PostureView />;
  }
  return <SweepFindingsView />;
}

export function App() {
  return (
    <RouterProvider>
      <Dial />
      <Routes />
    </RouterProvider>
  );
}
