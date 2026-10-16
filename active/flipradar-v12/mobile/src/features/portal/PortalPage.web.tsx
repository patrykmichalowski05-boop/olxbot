import React, { useCallback, useEffect, useRef, useState } from "react";
import Head from "expo-router/head";
import {
  Redirect,
  useFocusEffect,
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/AuthContext";
import { ApiError, apiErrorMessage } from "@/api/errors";
import {
  getAccount,
  getAdminData,
  getPublicConfig,
  operationId,
  publicPriceSearch,
  requestPlan,
  updateMemberAccess,
  deleteMemberAccount,
} from "@/api/endpoints/portal";
import { saveReturnPath } from "@/api/session";
import { mapRadarItem } from "@/api/mappers/opportunity";
import type { RadarApiItem } from "@/api/types/radar";
import { portalEnabled } from "@/utils/config";
import { formatMoneyMinor } from "@/utils/money";
import { publicPlans, questions, steps } from "./content";
import type {
  Account,
  PlanCode,
  PortalPageProps,
  PortalPlan,
  PriceResult,
} from "./types";
import "./portal.css";

function SiteLink({
  href,
  onClick,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const router = useRouter();
  return (
    <a
      href={href}
      {...props}
      onClick={(event) => {
        onClick?.(event);
        if (
          !event.defaultPrevented &&
          href.startsWith("/") &&
          !event.ctrlKey &&
          !event.metaKey &&
          !event.shiftKey &&
          event.button === 0
        ) {
          event.preventDefault();
          const hash = href.includes("#") ? href.split("#")[1] : null;
          const anchor = hash ? document.getElementById(hash) : null;
          if (anchor && window.location.pathname === "/") {
            anchor.scrollIntoView({ block: "start" });
            window.history.replaceState(null, "", href);
            return;
          }
          router.push(href as never);
        }
      }}
    />
  );
}
function Check() {
  return (
    <svg className="fr-check" viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="m4.5 10 3.4 3.4 7.6-7.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
function Header() {
  const { signedIn } = useAuth();
  return (
    <header className="fr-header fr-wrap">
      <SiteLink
        href="/"
        className="fr-logo"
        aria-label="FlipRadar — strona główna"
      >
        Flip<span>Radar</span>
      </SiteLink>
      <nav className="fr-nav" aria-label="Nawigacja główna">
        <SiteLink className="fr-links" href="/#jak-to-dziala">
          Jak to działa
        </SiteLink>
        <SiteLink className="fr-links" href="/#cennik">
          Cennik
        </SiteLink>
        <SiteLink className="fr-links" href="/#faq">
          FAQ
        </SiteLink>
        <span className="fr-header-actions">
          <SiteLink
            className="fr-btn fr-btn-small fr-login-link"
            href={signedIn ? "/account" : "/login"}
          >
            {signedIn ? "Moje konto" : "Zaloguj"}
          </SiteLink>
          <SiteLink className="fr-btn fr-btn-small fr-btn-primary" href="/bot">
            Przejdź do bota <span aria-hidden="true">→</span>
          </SiteLink>
        </span>
      </nav>
    </header>
  );
}
function Footer() {
  return (
    <footer className="fr-footer">
      <div className="fr-wrap fr-footer-inner">
        <span>© {new Date().getFullYear()} FlipRadar</span>
        <nav aria-label="Informacje o usłudze">
          <SiteLink href="/info?topic=terms">Zasady</SiteLink>
          <SiteLink href="/info?topic=privacy">Prywatność</SiteLink>
          <SiteLink href="/info?topic=contact">Kontakt</SiteLink>
        </nav>
      </div>
    </footer>
  );
}
function Notice({
  children,
  success = false,
}: {
  children: React.ReactNode;
  success?: boolean;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`fr-alert${success ? " fr-success" : ""}`}
    >
      {children}
    </div>
  );
}
function Loading({ text = "Sprawdzamy Twoje konto…" }: { text?: string }) {
  return (
    <div className="fr-loader" role="status" aria-live="polite">
      {text}
    </div>
  );
}
function SectionHead({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="fr-section-head">
      <h2>{title}</h2>
      {children ? <p>{children}</p> : null}
    </div>
  );
}

function ResultCard({
  item,
  example = false,
}: {
  item: RadarApiItem;
  example?: boolean;
}) {
  const card = mapRadarItem(item);
  const market = item.valuation?.market;
  const median =
    market &&
    typeof market === "object" &&
    "median_minor" in market &&
    typeof market.median_minor === "number"
      ? market.median_minor
      : null;
  const discount =
    median && card.purchaseMinor
      ? Math.round(((median - card.purchaseMinor) * 100) / median)
      : null;
  const currentLabel =
    card.purchaseMinor === null
      ? "Cena niedostępna"
      : formatMoneyMinor(card.purchaseMinor);
  const typicalLabel =
    median === null ? "Za mało danych" : formatMoneyMinor(median);
  const priceRatio =
    median && card.purchaseMinor ? card.purchaseMinor / median : null;
  return (
    <article className="fr-result-card">
      {example ? (
        <span className="fr-pill fr-example-label">Przykład</span>
      ) : null}
      <h3>{card.title}</h3>
      <p className="fr-result-meta">
        {card.platform.replaceAll("_", " ")} ·{" "}
        {example ? "Dane przykładowe" : "Dostępne porównanie rynku"}
      </p>
      <div className="fr-result-price">
        <strong>{currentLabel}</strong>
        <span
          className={`fr-pill fr-deal-pill${discount === null || discount <= 0 ? " fr-warning-pill" : ""}`}
        >
          {discount !== null && discount > 0 ? (
            <>
              <Check /> Okazja — o {discount}% poniżej mediany
            </>
          ) : discount !== null ? (
            "Porównaj cenę i stan"
          ) : (
            "Brak pełnej wyceny"
          )}
        </span>
      </div>
      {priceRatio !== null ? (
        <>
          <div className="fr-price-bar" aria-hidden="true">
            <span
              className="fr-price-mark"
              style={{ left: `${Math.max(5, Math.min(90, priceRatio * 55))}%` }}
            />
            <span
              className="fr-price-mark fr-price-mark-typical"
              style={{ left: "55%" }}
            />
          </div>
          <div className="fr-price-labels">
            <span>Ta oferta: {currentLabel}</span>
            <span>Typowa cena: {typicalLabel}</span>
          </div>
        </>
      ) : null}
      <p className="fr-result-explain">
        {example
          ? "Przykładowy wynik porównania pokazuje różnicę względem mediany. Przed zakupem sprawdź stan sprzętu i gwarancję."
          : (card.insight ??
            "Sprawdź dokładny wariant, stan przedmiotu oraz koszty przed podjęciem decyzji.")}
      </p>
      {!example ? (
        <div className="fr-result-actions">
          <small>
            {card.operatingProfitMinor !== null
              ? `Prognoza po kosztach: ${formatMoneyMinor(card.operatingProfitMinor)} · przed podatkiem`
              : "Brak wystarczających danych do prognozy zysku"}
          </small>
          {item.url &&
          /^https:\/\/(www\.)?(olx\.pl|facebook\.com|allegrolokalnie\.pl|otomoto\.pl|vinted\.pl)\//.test(
            item.url,
          ) ? (
            <a
              className="fr-btn fr-btn-small"
              href={item.url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Zobacz ofertę ↗
            </a>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
const exampleItem: RadarApiItem = {
  snapshot_id: 0,
  title: "Komputer gamingowy i5 / GTX 1630 / 8 GB / SSD 120 + HDD 500 GB",
  platform: "OLX",
  decision: "WATCH",
  observed_at: null,
  price_minor: 185000,
  url: null,
  valuation: { market: { median_minor: 299900 } },
};

function Pricing({
  plans = publicPlans,
  onChoose,
}: {
  plans?: PortalPlan[];
  onChoose: (plan: PlanCode) => void;
}) {
  return (
    <>
      <div className="fr-plans">
        {plans
          .filter((p) => p.code !== "LEGACY")
          .map((plan) => (
            <article
              key={plan.code}
              className={`fr-plan${plan.code === "STANDARD" ? " fr-plan-featured" : ""}`}
            >
              <div className="fr-plan-name">
                <h3>{plan.name}</h3>
                {plan.code === "STANDARD" ? (
                  <span className="fr-pill fr-popular">Polecany pakiet</span>
                ) : null}
              </div>
              <p className="fr-plan-price">{plan.price_minor / 100} zł</p>
              <ul>
                <li>
                  {plan.searches}{" "}
                  {plan.searches === 3 ? "wyszukiwania" : "wyszukiwań"}
                </li>
                <li>
                  {plan.notifications
                    ? "Powiadomienia o nowych okazjach"
                    : "OLX i Facebook oraz podłączone źródła"}
                </li>
                <li>
                  {plan.days
                    ? `Ważne ${plan.days} dni`
                    : "Darmowy start bez karty"}
                </li>
              </ul>
              <button
                className={`fr-btn${plan.code === "STANDARD" ? " fr-btn-primary" : ""}`}
                onClick={() => onChoose(plan.code)}
              >
                {plan.code === "START" ? "Wypróbuj" : "Wybierz"}
              </button>
            </article>
          ))}
      </div>
      <p className="fr-plans-note">
        Nazwy i ceny przykładowe. Płatny pakiet aktywuje operator po
        potwierdzeniu zgłoszenia.
      </p>
    </>
  );
}

function Landing() {
  const { mode, ready, signedIn } = useAuth();
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const searchAttempt = useRef<{ query: string; operation: string } | null>(
    null,
  );
  useFocusEffect(
    useCallback(() => {
      if (window.location.hash) {
        const id = window.location.hash.slice(1);
        setTimeout(
          () => document.getElementById(id)?.scrollIntoView({ block: "start" }),
          0,
        );
      }
    }, []),
  );
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PriceResult | null>(null);
  const [demoLeft, setDemoLeft] = useState(3);
  const config = useQuery({
    queryKey: ["portal-public-config"],
    queryFn: getPublicConfig,
    enabled: mode === "live" && portalEnabled(),
    retry: false,
  });
  const choose = async (plan: PlanCode) => {
    if (plan === "START") {
      input.current?.focus();
      input.current?.scrollIntoView({ block: "center" });
      return;
    }
    await saveReturnPath(`/account?plan=${plan}`);
    router.push(
      (signedIn ? `/account?plan=${plan}` : `/register?plan=${plan}`) as never,
    );
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (query.trim().length < 3) {
      setError("Wpisz co najmniej 3 znaki, np. RTX 4060.");
      return;
    }
    setLoading(true);
    try {
      if (mode === "demo" || !portalEnabled()) {
        if (demoLeft <= 0) {
          setError(
            "Wykorzystano 3 przykładowe wyszukiwania. Przejdź do bota, aby zobaczyć podgląd panelu.",
          );
          return;
        }
        setResult({
          items: [exampleItem],
          query: query.trim(),
          example: true,
          remaining: demoLeft - 1,
        });
        setDemoLeft((left) => left - 1);
      } else {
        if (
          !searchAttempt.current ||
          searchAttempt.current.query !== query.trim()
        ) {
          searchAttempt.current = {
            query: query.trim(),
            operation: operationId(),
          };
        }
        setResult(
          await publicPriceSearch(
            query.trim(),
            searchAttempt.current.operation,
          ),
        );
        searchAttempt.current = null;
      }
      setTimeout(
        () =>
          resultsRef.current?.scrollIntoView({
            block: "nearest",
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
              .matches
              ? "auto"
              : "smooth",
          }),
        0,
      );
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 503
          ? "Porównania cen są chwilowo niedostępne. Możesz przejść do swojego radaru i zapisać wyszukiwanie."
          : apiErrorMessage(e),
      );
    } finally {
      setLoading(false);
    }
  };
  return (
    <>
      <section className="fr-hero fr-wrap" aria-labelledby="hero-title">
        <h1 id="hero-title">Czy ta cena jest dobra?</h1>
        <p className="fr-lead">
          Wpisz, czego szukasz. Porównaj oferty z OLX i Facebooka z cenami
          podobnych przedmiotów i sprawdź, które są naprawdę tanie.
        </p>
        <form className="fr-search" onSubmit={submit} role="search">
          <label className="fr-sr" htmlFor="price-query">
            Czego szukasz?
          </label>
          <input
            ref={input}
            id="price-query"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            minLength={3}
            maxLength={120}
            placeholder="Czego szukasz? np. RTX 4060, laptop do gier"
            required
          />
          <button
            type="submit"
            className="fr-btn fr-btn-primary"
            disabled={loading || !ready}
          >
            {loading ? "Sprawdzamy…" : "Sprawdź ceny"}
          </button>
        </form>
        <p className="fr-free-note">
          <Check />
          {signedIn
            ? "Wyszukiwania zgodnie z pakietem na Twoim koncie"
            : "3 darmowe wyszukiwania bez zakładania konta"}
        </p>
        <span className="fr-platforms">
          OLX · Facebook Marketplace · Allegro Lokalnie · Otomoto · Vinted
        </span>
        {error ? (
          <Notice>
            {error}{" "}
            <SiteLink href={signedIn ? "/account" : "/register"}>
              {signedIn ? "Moje konto" : "Utwórz konto"}
            </SiteLink>
          </Notice>
        ) : null}
        {result ? (
          <div className="fr-results" ref={resultsRef} aria-live="polite">
            <h2 className="fr-results-head">
              {result.example
                ? "Przykład działania"
                : `Wyniki dla „${result.query}”`}
            </h2>
            {result.example ? (
              <p className="fr-plans-note">
                To ilustracja interfejsu. Przykładowa oferta nie jest wynikiem
                wyszukiwania na żywo.
              </p>
            ) : null}
            <div className="fr-results-grid">
              {result.items.length ? (
                result.items.map((item) => (
                  <ResultCard
                    key={item.snapshot_id}
                    item={item}
                    example={result.example}
                  />
                ))
              ) : (
                <Notice>
                  Nie ma jeszcze zebranych ofert pasujących do tego zapytania.
                  Zapisz dokładny model w swoim radarze.
                </Notice>
              )}
            </div>
            <p className="fr-plans-note">
              {result.remaining === null
                ? "Dostęp bez limitu wyszukiwań"
                : `Pozostało wyszukiwań: ${result.remaining}`}
            </p>
          </div>
        ) : null}
      </section>
      <section className="fr-section fr-wrap" id="jak-to-dziala">
        <SectionHead title="Jak to działa">
          Trzy kroki, bez przeglądania setek ogłoszeń.
        </SectionHead>
        <div className="fr-steps">
          {steps.map((step, index) => (
            <article className="fr-step" key={step.title}>
              <span className="fr-number" aria-hidden="true">
                {index + 1}
              </span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="fr-section fr-example fr-wrap">
        <SectionHead title="Tak wygląda wynik">
          Jasna odpowiedź zamiast tabel i wykresów.
        </SectionHead>
        <ResultCard item={exampleItem} example />
      </section>
      <section className="fr-section fr-price-section fr-wrap" id="cennik">
        <SectionHead title="Cennik">
          Płacisz za liczbę wyszukiwań.{" "}
          <span className="fr-pill">Pakiety przykładowe</span>
        </SectionHead>
        <Pricing
          plans={config.data?.plans}
          onChoose={(plan) => {
            void choose(plan);
          }}
        />
      </section>
      <section className="fr-section fr-faq fr-wrap" id="faq">
        <SectionHead title="Najczęstsze pytania" />
        {questions.map((question, index) => (
          <details key={question.title} open={index === 0}>
            <summary>{question.title}</summary>
            <p>{question.text}</p>
          </details>
        ))}
      </section>
      <section className="fr-bottom-cta fr-wrap">
        <div>
          <h2>Twoje okazje w jednym miejscu.</h2>
          <p>Zapisz model, ustaw warunki i sprawdzaj swój radar.</p>
        </div>
        <SiteLink className="fr-btn fr-btn-primary" href="/bot">
          Przejdź do bota <span aria-hidden="true">→</span>
        </SiteLink>
      </section>
    </>
  );
}

function AuthForm({ register = false }: { register?: boolean }) {
  const auth = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const params = useLocalSearchParams<{ plan?: string }>();
  const plan =
    params.plan === "STANDARD" || params.plan === "PLUS" ? params.plan : null;
  useEffect(() => {
    if (plan) void saveReturnPath(`/account?plan=${plan}`);
  }, [plan]);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (register && (password.length < 12 || password !== confirmation)) {
      setError(
        "Hasło musi mieć co najmniej 12 znaków i być takie samo w obu polach.",
      );
      return;
    }
    if (register && (auth.mode !== "live" || !portalEnabled())) {
      setError(
        "Rejestracja jest dostępna w połączonej usłudze. W podglądzie możesz zalogować się i obejrzeć panel demonstracyjny.",
      );
      return;
    }
    setBusy(true);
    try {
      if (register) await auth.register(username, email, password);
      else await auth.login(username, password);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? "Nieprawidłowy login lub hasło."
          : apiErrorMessage(e),
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="fr-auth fr-wrap">
      <h1>{register ? "Załóż konto FlipRadar" : "Witaj ponownie."}</h1>
      <p className="fr-auth-intro">
        {register
          ? "Zapisuj wybrane modele i miej swoje okazje pod kontrolą."
          : "Zaloguj się, aby przejść do swojego radaru."}
      </p>
      <form onSubmit={submit}>
        <label className="fr-field">
          {register ? "Login" : "Adres e-mail (administrator: login)"}
          <input
            type="text"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            minLength={3}
            maxLength={register ? 32 : 200}
            pattern={register ? "[a-zA-Z][a-zA-Z0-9_.-]{2,31}" : undefined}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={register ? "Wybierz login" : "E-mail lub login administratora"}
            required
          />
        </label>
        {register ? (
          <label className="fr-field">
            Adres e-mail — wymagany
            <input type="email" name="email" autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)} maxLength={200} required
              placeholder="twoj@email.pl" />
          </label>
        ) : null}
        <label className="fr-field">
          Hasło
          <input
            type="password"
            name="password"
            autoComplete={register ? "new-password" : "current-password"}
            minLength={register ? 12 : 1}
            maxLength={register ? 256 : 512}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={register ? "Co najmniej 12 znaków" : "Twoje hasło"}
            required
          />
        </label>
        {register ? (
          <label className="fr-field">
            Powtórz hasło
            <input
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={256}
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              required
            />
          </label>
        ) : null}
        <button
          type="submit"
          className="fr-btn fr-btn-primary"
          disabled={busy || !auth.ready}
        >
          {busy
            ? "Chwila…"
            : register
              ? "Utwórz konto"
              : "Zaloguj i przejdź do bota"}
        </button>
        {error ? <Notice>{error}</Notice> : null}
      </form>
      <p className="fr-auth-links">
        {register ? "Masz już konto?" : "Nie masz konta?"}{" "}
        <SiteLink
          href={`${register ? "/login" : "/register"}${plan ? `?plan=${plan}` : ""}`}
        >
          {register ? "Zaloguj się" : "Zarejestruj się"}
        </SiteLink>
      </p>
      <small>
        Po zalogowaniu dostęp do bota wynika z pakietu przypisanego do Twojego
        konta.{" "}
        <SiteLink href="/info?topic=privacy">Informacje o prywatności</SiteLink>
        .
      </small>
    </div>
  );
}

function AccessState({ account }: { account: Account }) {
  return (
    <div className="fr-auth fr-wrap">
      <span className="fr-pill fr-warning-pill">Dostęp nieaktywny</span>
      <h1 style={{ marginTop: 20 }}>
        {account.access.reason === "EXPIRED"
          ? "Twój pakiet wygasł."
          : "Dostęp jest wstrzymany."}
      </h1>
      <p className="fr-auth-intro">
        Na koncie sprawdzisz aktualny pakiet i zgłosisz jego aktywację.
      </p>
      <SiteLink href="/account" className="fr-btn fr-btn-primary">
        Przejdź do konta
      </SiteLink>
    </div>
  );
}
export function PortalBotGate({ children }: { children?: React.ReactNode }) {
  const auth = useAuth();
  const account = useQuery({
    queryKey: ["portal-account", auth.userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: auth.signedIn && auth.mode === "live" && portalEnabled(),
    retry: 1,
    staleTime: 15000,
  });
  if (!auth.ready || !auth.signedIn) return <Loading />;
  if (auth.mode === "demo" || !portalEnabled())
    return children ?? <Redirect href="/radar" />;
  if (account.isPending) return <Loading />;
  if (account.isError)
    return (
      <div className="fr-auth fr-wrap">
        <Notice>{apiErrorMessage(account.error)}</Notice>
        <button
          className="fr-btn"
          onClick={() => {
            void account.refetch();
          }}
        >
          Spróbuj ponownie
        </button>
        <SiteLink href="/account" className="fr-btn">
          Moje konto
        </SiteLink>
      </div>
    );
  if (!account.data.access.can_open_bot)
    return <AccessState account={account.data} />;
  return children ?? <Redirect href="/radar" />;
}

function AdminPanel() {
  const cache = useQueryClient();
  const data = useQuery({
    queryKey: ["portal-admin"],
    queryFn: ({ signal }) => getAdminData(signal),
  });
  const [selected, setSelected] = useState<Record<string, PlanCode>>({});
  const [pending, setPending] = useState<{
    userId: string;
    username: string;
    action: "activate" | "disable";
    plan?: PlanCode;
    operation: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirmButton = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (pending && dialog.current && !dialog.current.open) {
      dialog.current.showModal();
      confirmButton.current?.focus();
    }
  }, [pending]);
  const deleteMember = async (userId: string, username: string) => {
    const confirm = window.prompt(`Usunięcie konta ${username} jest nieodwracalne. Wpisz dokładnie login:`);
    if (confirm !== username) return;
    setBusy(true);
    setError("");
    try {
      await deleteMemberAccount(userId, confirm);
      await cache.invalidateQueries({ queryKey: ["portal-admin"] });
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally { setBusy(false); }
  };
  const commit = async () => {
    if (!pending) return;
    setBusy(true);
    setError("");
    try {
      await updateMemberAccess(
        pending.userId,
        pending.action,
        pending.plan,
        pending.operation,
      );
      await cache.invalidateQueries({ queryKey: ["portal-admin"] });
      setPending(null);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  if (data.isPending) return <Loading text="Wczytujemy konta…" />;
  if (data.isError) return <Notice>{apiErrorMessage(data.error)}</Notice>;
  return (
    <section className="fr-admin">
      <h2>Zarządzanie dostępem</h2>
      {data.data.requests.length ? (
        <Notice>
          {data.data.requests.length} zgłoszeń czeka na aktywację pakietu.
        </Notice>
      ) : null}
      <div className="fr-admin-list">
        {data.data.accounts
          .filter((member) => member.role !== "OWNER")
          .map((member) => {
            const requested = data.data.requests.find(
              (request) => request.user_id === member.user_id,
            );
            const plan =
              selected[member.user_id] ??
              requested?.plan ??
              (member.plan === "LEGACY" ? "START" : member.plan);
            return (
              <div className="fr-member" key={member.user_id}>
                <div>
                  <strong>{member.username}</strong>
                  <br />
                  <small>
                    {member.enabled ? "Aktywne konto" : "Konto wstrzymane"} ·{" "}
                    {member.plan} · wykorzystano: {member.used}
                    {requested ? ` · Zgłoszenie: ${requested.plan}` : ""}
                  </small>
                </div>
                <div className="fr-member-actions">
                  <label className="fr-sr" htmlFor={`plan-${member.user_id}`}>
                    Pakiet dla {member.username}
                  </label>
                  <select
                    id={`plan-${member.user_id}`}
                    value={plan}
                    onChange={(event) =>
                      setSelected((current) => ({
                        ...current,
                        [member.user_id]: event.target.value as PlanCode,
                      }))
                    }
                  >
                    <option value="START">Start</option>
                    <option value="STANDARD">Standard</option>
                    <option value="PLUS">Plus</option>
                  </select>
                  <button
                    className="fr-btn fr-btn-small fr-btn-primary"
                    onClick={() =>
                      setPending({
                        userId: member.user_id,
                        username: member.username,
                        action: "activate",
                        plan,
                        operation: operationId(),
                      })
                    }
                  >
                    Aktywuj
                  </button>
                  <button
                    className="fr-btn fr-btn-small fr-btn-danger"
                    onClick={() =>
                      setPending({
                        userId: member.user_id,
                        username: member.username,
                        action: "disable",
                        operation: operationId(),
                      })
                    }
                  >
                    Wstrzymaj
                  </button>
                  <button className="fr-btn fr-btn-small fr-btn-danger"
                    disabled={busy} onClick={() => {void deleteMember(member.user_id,member.username);}}>
                    Usuń konto
                  </button>
                </div>
              </div>
            );
          })}
      </div>
      <p className="fr-plans-note">Dodatkowe ustawienia ról i platform:
        {" "}<a href="/admin/uzytkownicy?legacy=1">zarządzanie zaawansowane</a>.
      </p>
      {!data.data.accounts.some((member) => member.role !== "OWNER") ? (
        <p className="fr-plans-note">
          Nowe konta i zgłoszenia pojawią się tutaj po rejestracji.
        </p>
      ) : null}
      {pending ? (
        <dialog
          ref={dialog}
          className="fr-modal"
          aria-modal="true"
          aria-labelledby="access-confirm-title"
          onCancel={(event) => {
            event.preventDefault();
            if (!busy) setPending(null);
          }}
        >
          <h2 id="access-confirm-title">
            {pending.action === "activate"
              ? "Aktywować pakiet?"
              : "Wstrzymać dostęp?"}
          </h2>
          <p>
            {pending.username}
            {pending.plan
              ? ` · ${pending.plan}. Nowa aktywacja rozpocznie okres pakietu i odnowi jego limit.`
              : " nie będzie mieć dostępu do bota."}
          </p>
          <div className="fr-modal-actions">
            <button
              className="fr-btn"
              disabled={busy}
              onClick={() => setPending(null)}
            >
              Anuluj
            </button>
            <button
              ref={confirmButton}
              className="fr-btn fr-btn-primary"
              disabled={busy}
              onClick={() => {
                void commit();
              }}
            >
              {busy ? "Zapisujemy…" : "Potwierdź"}
            </button>
          </div>
          {error ? <Notice>{error}</Notice> : null}
        </dialog>
      ) : null}
    </section>
  );
}

function AccountPage() {
  const auth = useAuth();
  const router = useRouter();
  const cache = useQueryClient();
  const params = useLocalSearchParams<{ plan?: string }>();
  const sentPlan = useRef<string | null>(null);
  const account = useQuery({
    queryKey: ["portal-account", auth.userId],
    queryFn: ({ signal }) => getAccount(signal),
    enabled: auth.signedIn && auth.mode === "live" && portalEnabled(),
    refetchInterval: 60000,
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const choose = useCallback(
    async (plan: PlanCode) => {
      setError("");
      setMessage("");
      if (plan === "START") {
        router.push("/bot");
        return;
      }
      if (auth.mode !== "live" || !portalEnabled()) {
        setMessage(
          "To podgląd konta. Zgłoszenia pakietów są dostępne po połączeniu z usługą.",
        );
        return;
      }
      setBusy(true);
      try {
        await requestPlan(plan);
        await cache.invalidateQueries({
          queryKey: ["portal-account", auth.userId],
        });
        setMessage(
          `Zgłoszenie pakietu ${plan === "PLUS" ? "Plus" : "Standard"} zostało zapisane. Dostęp zmieni się po aktywacji przez operatora.`,
        );
      } catch (e) {
        setError(apiErrorMessage(e));
      } finally {
        setBusy(false);
      }
    },
    [auth.mode, auth.userId, cache, router],
  );
  useEffect(() => {
    if (
      (params.plan === "STANDARD" || params.plan === "PLUS") &&
      auth.signedIn &&
      sentPlan.current !== params.plan
    ) {
      sentPlan.current = params.plan;
      void choose(params.plan);
    }
  }, [params.plan, auth.signedIn, choose]);
  if (!auth.ready || !auth.signedIn) return <Loading />;
  if (auth.mode === "live" && portalEnabled() && account.isPending)
    return <Loading />;
  if (account.isError)
    return (
      <div className="fr-auth fr-wrap">
        <Notice>{apiErrorMessage(account.error)}</Notice>
        <button
          className="fr-btn"
          onClick={() => {
            void account.refetch();
          }}
        >
          Spróbuj ponownie
        </button>
      </div>
    );
  const current: Account = account.data ?? {
    user_id: "demo",
    username: "Konto demonstracyjne",
    role: "MEMBER",
    plan: publicPlans[0],
    access: {
      can_open_bot: true,
      can_search: true,
      can_receive_notifications: false,
      reason: "ACTIVE",
      remaining: 3,
      limit: 3,
      used: 0,
      expires_at: null,
    },
    plan_request: null,
  };
  return (
    <div className="fr-account fr-wrap">
      <div className="fr-account-head">
        <div>
          <h1>Twoje konto</h1>
          <p>
            {current.username} · wszystko, czego potrzebujesz do swojego radaru.
          </p>
        </div>
        <button
          className="fr-btn"
          onClick={async () => {
            try {
              await auth.logout();
            } catch (e) {
              setError(apiErrorMessage(e));
            }
          }}
        >
          Wyloguj się
        </button>
      </div>
      <div className="fr-account-grid">
        <section className="fr-panel">
          <h2>Twój pakiet</h2>
          <span className="fr-pill">
            {current.role === "OWNER" ? "Konto właściciela" : current.plan.name}
          </span>
          <div className="fr-balance">
            {current.access.remaining === null
              ? "Bez limitu"
              : current.access.remaining}
          </div>
          <p>
            {current.access.remaining === null
              ? "Masz dostęp do wszystkich funkcji swojego radaru."
              : `pozostałych wyszukiwań z ${current.access.limit} w pakiecie`}
          </p>
          {current.access.limit ? (
            <div
              className="fr-progress"
              role="meter"
              aria-label="Pozostałe wyszukiwania"
              aria-valuemin={0}
              aria-valuemax={current.access.limit}
              aria-valuenow={current.access.remaining ?? 0}
            >
              <span
                style={{
                  width: `${Math.max(0, Math.min(100, ((current.access.remaining ?? 0) / current.access.limit) * 100))}%`,
                }}
              />
            </div>
          ) : null}
          <div className="fr-account-actions">
            <SiteLink href="/bot" className="fr-btn fr-btn-primary">
              Przejdź do bota →
            </SiteLink>
            <SiteLink href="/searches" className="fr-btn">
              Moje wyszukiwania
            </SiteLink>
          </div>
        </section>
        <section className="fr-panel">
          <h2>Dostęp do usługi</h2>
          <div className="fr-detail-row">
            <span>Status</span>
            <strong>
              {current.access.can_open_bot
                ? "Aktywny"
                : current.access.reason === "EXPIRED"
                  ? "Pakiet wygasł"
                  : "Wstrzymany"}
            </strong>
          </div>
          <div className="fr-detail-row">
            <span>Ważność</span>
            <strong>
              {current.access.expires_at
                ? new Date(current.access.expires_at).toLocaleDateString(
                    "pl-PL",
                  )
                : "Bezterminowo"}
            </strong>
          </div>
          <div className="fr-detail-row">
            <span>Powiadomienia</span>
            <strong>
              {current.access.can_receive_notifications
                ? "Włączone w pakiecie"
                : "Dostępne w Standard i Plus"}
            </strong>
          </div>
          <div className="fr-detail-row">
            <span>Twoje dane</span>
            <strong>Prywatny radar i wyszukiwania</strong>
          </div>
          {current.plan_request?.status === "PENDING" ? (
            <Notice>
              Zgłoszenie {current.plan_request.plan} czeka na aktywację.
            </Notice>
          ) : null}
        </section>
      </div>
      {message ? <Notice success>{message}</Notice> : null}
      {error ? <Notice>{error}</Notice> : null}
      {busy ? (
        <p role="status" className="fr-plans-note">
          Zapisujemy zgłoszenie…
        </p>
      ) : null}
      {current.role === "OWNER" && auth.mode === "live" && portalEnabled() ? (
        <AdminPanel />
      ) : null}
      <section id="pakiety">
        <SectionHead title="Wybierz dostęp dla siebie">
          Liczba wyszukiwań i powiadomienia zgodnie z Twoim pakietem.
        </SectionHead>
        <Pricing
          onChoose={(plan) => {
            if (!busy) void choose(plan);
          }}
        />
      </section>
    </div>
  );
}

function InfoPage() {
  const { topic } = useLocalSearchParams<{ topic?: string }>();
  return (
    <article className="fr-prose fr-wrap">
      {topic === "privacy" ? (
        <>
          <h1>Prywatność w FlipRadar</h1>
          <h2>Twoje konto i radar</h2>
          <p>
            Konto przechowuje login, zabezpieczone dane logowania, przypisany
            pakiet, wykorzystane wyszukiwania i zgłoszenia aktywacji. Zapisane
            modele oraz powiadomienia są dostępne na koncie, do którego należą.
          </p>
          <h2>Sesja i darmowe wyszukiwania</h2>
          <p>
            Strona używa niezbędnych plików sesji do utrzymania logowania oraz
            limitowania darmowych zapytań. Nie zapisuje hasła w przeglądarce.
            Limity gości uwzględniają również połączenie sieciowe, aby
            ograniczyć nadużycia.
          </p>
          <h2>Kontrola dostępu</h2>
          <p>
            Możesz wylogować się z konta i usuwać zapisane wyszukiwania.
            Właściciel usługi zarządza aktywnością kont i okresem dostępu.
          </p>
        </>
      ) : topic === "contact" ? (
        <>
          <h1>Kontakt w sprawie dostępu</h1>
          <p>
            W sprawach pakietu przejdź do swojego konta i wybierz Standard lub
            Plus. Twoje zgłoszenie trafi do panelu operatora. Status aktywacji
            zobaczysz w tym samym miejscu.
          </p>
          <SiteLink href="/account" className="fr-btn fr-btn-primary">
            Przejdź do konta
          </SiteLink>
        </>
      ) : (
        <>
          <h1>Zasady działania</h1>
          <h2>Porównanie cen</h2>
          <p>
            FlipRadar pokazuje porównania z zebranymi, podobnymi ofertami.
            Zakres wyników zależy od podłączonych źródeł i dostępnych danych.
            Nie jest to pełny katalog wszystkich ogłoszeń.
          </p>
          <h2>Ocena oferty</h2>
          <p>
            Prognoza odsprzedaży i wyniku po kosztach pomaga podjąć decyzję, ale
            nie jest gwarancją ceny, stanu przedmiotu ani zysku. Transakcję
            zawierasz bezpośrednio ze sprzedawcą na wybranej platformie.
          </p>
          <h2>Pakiety</h2>
          <p>
            Trzy wyszukiwania umożliwiają wypróbowanie usługi. Pakiety Standard
            i Plus mają odrębny limit oraz okres ważności widoczny na koncie.
            Ceny na tej stronie są przykładowe; zgłoszenie pakietu nie pobiera
            płatności ani nie aktywuje go automatycznie.
          </p>
          <h2>Wyszukiwania i alerty</h2>
          <p>
            Nowe profile oraz zmiana wybranego modelu wykorzystują wyszukiwanie
            w pakiecie. Zmiana samych kosztów lub progów alertu nie pobiera
            kolejnego wyszukiwania. Powiadomienia dotyczą wyłącznie Twoich
            zapisanych profili.
          </p>
        </>
      )}
    </article>
  );
}

export default function PortalPage({ page }: PortalPageProps) {
  const { mode } = useAuth();
  const publicConfig = useQuery({
    queryKey: ["portal-public-config"],
    queryFn: getPublicConfig,
    enabled: mode === "live" && portalEnabled(),
    retry: false,
    staleTime: 60000,
  });
  const title =
    page === "landing"
      ? "FlipRadar — czy ta cena jest dobra?"
      : page === "register"
        ? "Załóż konto — FlipRadar"
        : page === "login"
          ? "Zaloguj się — FlipRadar"
          : page === "account"
            ? "Twoje konto — FlipRadar"
            : page === "bot"
              ? "Twój bot — FlipRadar"
              : "Informacje — FlipRadar";
  return (
    <div className="fr-site">
      <Head>
        <title>{title}</title>
        <meta
          name="description"
          content="Sprawdź ceny, porównuj okazje i ustaw własny radar. OLX, Facebook Marketplace i pozostałe podłączone źródła w jednym miejscu."
        />
        <meta name="theme-color" content="#ffffff" />
        {page !== "landing" && page !== "info" ? (
          <meta name="robots" content="noindex,nofollow" />
        ) : null}
      </Head>
      <a className="fr-skip" href="#tresc">
        Przejdź do treści
      </a>
      {mode === "demo" || publicConfig.data?.demo_data ? (
        <div className="fr-demo-note">
          Podgląd FlipRadar · przykładowe dane, bez połączenia z ofertami na
          żywo
        </div>
      ) : null}
      <Header />
      <main id="tresc">
        {page === "landing" ? (
          <Landing />
        ) : page === "login" ? (
          <AuthForm />
        ) : page === "register" ? (
          <AuthForm register />
        ) : page === "account" ? (
          <AccountPage />
        ) : page === "bot" ? (
          <PortalBotGate />
        ) : (
          <InfoPage />
        )}
      </main>
      <Footer />
    </div>
  );
}
