import { LandingScene } from "@/components/landing-scene";
import { LandingUI } from "@/components/landing-ui";

export default function HomePage() {
  return (
    <main className="relative min-h-screen bg-[#E6E2D6] overflow-hidden w-full m-0 p-0">
      <LandingScene />
      <LandingUI />
    </main>
  );
}
