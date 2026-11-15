import { Dial } from "./components/Dial";
import { RouterProvider, useRouter } from "./router";
import { CampaignOverviewView } from "./views/CampaignOverviewView";
import { PortfolioView } from "./views/PortfolioView";
import { PostureView } from "./views/PostureView";
import { SessionsView } from "./views/SessionsView";
import { SweepFindingsView } from "./views/SweepFindingsView";

function Routes() {
  const { path } = useRouter();
  if (path === "/campaign") {
    return <CampaignOverviewView />;
  }
  if (path === "/posture") {
    return <PostureView />;
  }
  if (path === "/sessions") {
    return <SessionsView />;
  }
  if (path === "/portfolio") {
    return <PortfolioView />;
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
