import { PlayPage } from "./pages/PlayPage";
import { GamesPage } from "./pages/GamesPage";
import { ReplayPage } from "./pages/ReplayPage";
import { StatsPage } from "./pages/StatsPage";
import { useHashRoute } from "./hooks/useHashRoute";

export function App() {
  const [route] = useHashRoute();
  if (route.name === "games") return <GamesPage scope={route.scope} />;
  if (route.name === "stats") return <StatsPage scope={route.scope} />;
  if (route.name === "replay")
    return <ReplayPage gameId={route.gameId} scope={route.scope} />;
  return <PlayPage />;
}
