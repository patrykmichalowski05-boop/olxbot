import type { PortalPlan } from "./types";

export const publicPlans: PortalPlan[] = [
  {
    code: "START",
    name: "Start",
    price_minor: 0,
    searches: 3,
    days: null,
    notifications: false,
    prices_are_examples: true,
  },
  {
    code: "STANDARD",
    name: "Standard",
    price_minor: 1900,
    searches: 20,
    days: 30,
    notifications: true,
    prices_are_examples: true,
  },
  {
    code: "PLUS",
    name: "Plus",
    price_minor: 3900,
    searches: 60,
    days: 90,
    notifications: true,
    prices_are_examples: true,
  },
];
export const steps = [
  {
    title: "Wpisz, czego szukasz",
    text: "Model karty, laptop do gier, telefon albo cały zestaw — wystarczy kilka słów.",
  },
  {
    title: "Porównujemy podobne oferty",
    text: "Zbieramy dane z podłączonych źródeł i sprawdzamy ceny tego samego modelu i wariantu.",
  },
  {
    title: "Widzisz, co jest tanie",
    text: "Dostajesz ocenę ceny, prognozę po kosztach i informację, co sprawdzić przed zakupem.",
  },
];
export const questions = [
  {
    title: "Skąd wiecie, czy cena jest dobra?",
    text: "Porównujemy przedmiot z podobnymi ofertami z ostatnich dni. Uwzględniamy model, wariant i dostępne informacje o stanie. Przy zbyt małej liczbie porównań pokazujemy brak wyceny.",
  },
  {
    title: "Czy kupuję przez FlipRadar?",
    text: "Nie. FlipRadar pomaga znaleźć i ocenić ofertę. Zakupu dokonujesz bezpośrednio w serwisie, w którym sprzedawca opublikował ogłoszenie.",
  },
  {
    title: "Czy ocena to gwarancja?",
    text: "Ocena i potencjalny wynik są prognozą. Ceny ofertowe nie dowodzą zawarcia transakcji. Przed zakupem sprawdź stan przedmiotu, sprzedawcę, koszty i warunki sprzedaży.",
  },
  {
    title: "Jak działa dostęp do bota?",
    text: "Po zalogowaniu widzisz własny radar i zapisane wyszukiwania. Dostępne wyszukiwania, powiadomienia i okres dostępu wynikają z pakietu przypisanego do Twojego konta.",
  },
];
