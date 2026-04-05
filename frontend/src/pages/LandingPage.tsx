import type { LucideIcon } from "lucide-react"
import { ArrowRight, GitBranch, Lightbulb, ShieldCheck, Users } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  CardCurtain,
  CardCurtainReveal,
  CardCurtainRevealBody,
  CardCurtainRevealDescription,
  CardCurtainRevealFooter,
  CardCurtainRevealTitle,
} from "@/components/ui/card-curtain-reveal"
import { ScrollCueAuroraGlass } from "@/components/scroll-cue-variants"
import { ParticleTextEffect } from "@/components/ui/particle-text-effect"
import { cn } from "@/lib/utils"

const CAPABILITY_CARDS: {
  icon: LucideIcon
  title: string
  description: string
  image: string
  imageAlt: string
  liClassName?: string
}[] = [
  {
    icon: Lightbulb,
    title: "Assumptions",
    description:
      "An explicit assumption log: what you are taking as given, why, and what breaks if you are wrong.",
    image:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&q=80&w=800",
    imageAlt: "Planning documents and laptop on a desk",
  },
  {
    icon: GitBranch,
    title: "Plan",
    description:
      "Phases and tasks, dependencies, and critical-path-style reasoning.",
    image:
      "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&q=80&w=800",
    imageAlt: "Team reviewing a timeline on a whiteboard",
  },
  {
    icon: ShieldCheck,
    title: "Risks",
    description:
      "A risk register with scoring, mitigations, and contingencies.",
    image:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=800",
    imageAlt: "Analytics charts on a display",
  },
  {
    icon: Users,
    title: "Staffing",
    description:
      "Roles, hours, and phase involvement aligned to the plan.",
    image:
      "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80&w=800",
    imageAlt: "Colleagues collaborating in an office",
  },
  {
    icon: ShieldCheck,
    title: "Approval gates",
    description:
      "Refine with human feedback, approve when ready, or start a fresh run with the same PRD. Gates surface when the model flags extra risk.",
    image:
      "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?auto=format&fit=crop&q=80&w=800",
    imageAlt: "Team discussion at a meeting table",
    liClassName: "sm:col-span-2 lg:col-span-1",
  },
]

const LANDING_WORDS: string[] = [
  "PLANR",
  "ASSUME",
  "PLAN",
  "RISK",
  "STAFF",
]

export function LandingPage() {
  return (
    <div className="bg-black text-zinc-100 antialiased">
      <section
        className="relative min-h-[90dvh] bg-black"
        aria-label="PLANR hero"
      >
        <div className="absolute inset-0 z-0" aria-hidden>
          <ParticleTextEffect
            words={LANDING_WORDS}
            embedded
            hideCaption
            fullBleed
          />
        </div>

        <header className="relative z-20 px-6 py-4 sm:py-5">
          <span className="font-semibold tracking-[0.2em] text-lg text-white">
            PLANR
          </span>
        </header>

        <ScrollCueAuroraGlass className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2" />
      </section>

      <main>
        <section
          id="about"
          className="scroll-mt-8 border-t border-zinc-900 px-6 py-16 md:py-24 max-w-3xl mx-auto min-h-[72dvh] flex flex-col"
        >
          <p className="mb-3 text-sm font-medium uppercase tracking-widest text-zinc-300">
            About
          </p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-6">
            Give it a brief. Get a plan worth signing off on.
          </h1>
          <p className="mb-6 text-lg leading-relaxed text-zinc-200">
            PLANR turns any project input, from a napkin idea to a full PRD, into
            the four things a senior PM would produce before anyone writes a line
            of code: assumptions, project plan, risk register, and staffing plan.
          </p>
          <p className="mb-6 text-lg leading-relaxed text-zinc-200">
            Built-in approval gates mean nothing moves forward until a human says
            so. Push back, add a constraint you missed, refine the scope. The plan
            updates, and the gates hold.
          </p>
          <p className="mb-10 text-lg leading-relaxed text-zinc-200">
            The name is intentional. Dead simple, and it works as a verb. &quot;Let
            me Planr this first.&quot;
          </p>
          <div className="flex flex-wrap gap-3">
            <Button type="button" asChild>
              <Link to="/plan">
                Get started
                <ArrowRight className="opacity-80" aria-hidden />
              </Link>
            </Button>
            <Button variant="outline" type="button" asChild>
              <a href="#capabilities">See capabilities</a>
            </Button>
          </div>
        </section>

        <section
          id="capabilities"
          className="border-t border-zinc-900 bg-zinc-950/50 px-6 py-16 scroll-mt-8"
        >
          <div className="max-w-7xl mx-auto">
            <h2 className="text-2xl font-semibold text-white mb-10 text-center">
              What you get
            </h2>
            <ul className="grid list-none gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {CAPABILITY_CARDS.map(
                ({ icon: Icon, title, description, image, imageAlt, liClassName }) => (
                  <li
                    key={title}
                    className={cn("min-h-0", liClassName)}
                  >
                    <CardCurtainReveal className="h-full w-full rounded-xl border border-zinc-800 bg-black/40">
                      <CardCurtainRevealBody className="relative flex flex-col">
                        <Icon
                          className="mb-3 h-8 w-8 shrink-0 text-zinc-200"
                          strokeWidth={1.5}
                          aria-hidden
                        />
                        <CardCurtainRevealTitle className="mb-1 font-medium text-white">
                          {title}
                        </CardCurtainRevealTitle>
                        <CardCurtainRevealDescription className="text-sm leading-relaxed text-zinc-200">
                          <p>{description}</p>
                        </CardCurtainRevealDescription>
                        <CardCurtain className="bg-zinc-400/25" />
                      </CardCurtainRevealBody>
                      <CardCurtainRevealFooter className="relative isolate mt-0 h-20 w-full shrink-0">
                        <img
                          src={image}
                          alt={imageAlt}
                          width={800}
                          height={320}
                          className="h-full w-full object-cover"
                          loading="lazy"
                          decoding="async"
                        />
                      </CardCurtainRevealFooter>
                    </CardCurtainReveal>
                  </li>
                )
              )}
            </ul>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-900 px-6 py-6 text-center text-xs text-zinc-400">
        Particle hero • shadcn-style UI + Tailwind
      </footer>
    </div>
  )
}
