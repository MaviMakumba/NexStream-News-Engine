// capture/capture.mjs'in yazdığı manifest.json'un tipleri. Tüm dikdörtgenler CSS pikseli,
// SAYFA koordinatı (kaydırma dahil).

export interface Rect { x: number; y: number; w: number; h: number }
export interface TextBox extends Rect { chars: number }

export interface FeedLayout { nav: Rect; market: Rect; live: Rect; trending: Rect; filters: Rect; cards: Rect[] }

export interface CardLayout {
  card: Rect; meta: Rect; source: Rect; time: Rect; topic: Rect; sentiment: Rect; corroboration: Rect; trust: Rect;
  title: Rect; chips: Rect; footer: Rect;
  buttons: { related: Rect; sources: Rect; ask: Rect; listen: Rect; save: Rect };
  panels: Rect[];
}

export interface AccountLayout {
  page: { w: number; h: number };
  sections: { title: string; rect: Rect }[];
  newsletter: Rect;
  topics: Record<string, Rect>;
  keyword: Rect;
  keywordText: TextBox | null;
  frequency: Rect[];
  save: Rect;
}

export interface Manifest {
  viewport: { width: number; height: number };
  dpr: number;
  themes: { order: string[]; frames: number; scale: number };
  feed: { clipHeight: number; before: FeedLayout; after: FeedLayout };
  card: {
    hero: number;
    states: { base: CardLayout; related: CardLayout; sources: CardLayout; listen: CardLayout; saved: CardLayout };
    userMenu: Rect;
    navLinks: { search: Rect | null; ask: Rect | null };
  };
  ask: {
    scrolls: { blank: number; typed: number; pending: number; answer: number; answerBlank: number };
    typed: { input: Rect; text: TextBox; send: Rect };
    pending: { user: Rect };
    answer: { user: Rect; answer: { bubble: Rect; text: Rect; lineHeight: number; badges: Rect; sources: Rect; alert: Rect } };
  };
  search: { scroll: number; typed: { input: Rect; text: TextBox; button: Rect }; results: { results: Rect[]; scores: Rect[] } };
  account: { picks: string[]; steps: { name: string; layout: AccountLayout }[] };
  digest: { size: { w: number; h: number }; width: number; dpr: number };
}
