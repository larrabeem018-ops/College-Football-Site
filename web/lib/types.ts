export type TeamRef = { school: string; slug: string | null; abbr: string; color: string; alt: string; logo: string | null };
export type Tier = "fav_value" | "big_gap" | "lean" | "pass";
export type Qb = { name: string; starts: number | null } | null;

export type Game = {
  id: number; week: number; kick: string; home: TeamRef; away: TeamRef;
  homeConf: string | null; awayConf: string | null; venue: string | null; neutral: boolean; confGame: boolean;
  spread: number | null; spreadOpen: number | null; overUnder: number | null;
  predHome: number | null; predAway: number | null; modelSpread: number | null; modelTotal: number | null;
  edge: number | null; tier: Tier | null; pickSide: "home" | "away" | null; pick: string | null;
  result: "Win" | "Loss" | "Push" | null; why: string[]; watch: string[]; homeQb: Qb; awayQb: Qb;
  homeScore?: number; awayScore?: number;
};

export type SeasonStats = {
  season: number; games: number; off_points_pg: number; off_yards_pg: number; off_third_down_pct: number;
  def_points_pg: number; def_yards_pg: number; def_third_down_pct: number; turnovers_committed_pg: number;
  turnovers_forced_pg: number; turnover_margin_pg: number;
} | null;
export type Returning = { pct: number | null; returning_players: number; total_players: number } | null;

export type GameDetail = Game & { homeStats: SeasonStats; awayStats: SeasonStats; homeReturning: Returning; awayReturning: Returning; mlValue?: MlRow };

export type MlRow = { week: number; id: number; kick: string; team: TeamRef; opp: string; home: boolean; line: number | null; ml: number;
  pMkt: number; pModel: number; pBlend: number; ev: number; result: "Win" | "Loss" | "Push" | "Pending"; profit: number; score: string | null };
export type MlSummary = { bets: number; won?: number; win_pct?: number; median_odds?: number; units?: number; roi?: number };
export type MlFile = {
  model: { sigma: number; market_weight: number; model_tilt: number; games: number; fitted: string;
    backtest: { all: MlSummary; by_season: Record<string, MlSummary>; every_dog: MlSummary; by_line: (MlSummary & { label: string })[] } };
  live: { bets: number; won: number; units: number; roi: number | null; pending: number };
  weeks: Record<string, MlRow[]>; log: MlRow[];
};

export type WeekFile = { week: number; season: number; games: Game[] };
export type Meta = {
  season: number; priorSeason: number; currentWeek: number | null; generated: string; teamCount: number; breakEven: number;
  weeks: { week: number; games: number; watchlist: number; edges: number }[]; bettingSeasons: number[]; qbSeasons: number[];
};

export type TierRow = { tier: Tier | "all_3plus"; label: string; wins: number; losses: number; pushes: number; win_pct: number; units: number; by_season: Record<string, [number, number]>; description: string };
export type Rec = { w: number; l: number; p: number; pct: number | null; units: number };
export type TrackRecord = {
  season: number; breakEven: number; tiers: TierRow[];
  accuracy: { Model: { margin_MAE: number; winner_pct: number; games: number }; Vegas: { margin_MAE: number; winner_pct: number; games: number } } | null;
  qbCheck: { changed: Record<string, any>; same: Record<string, any> } | null;
  season_records: { watchlist: Rec; big_gap: Rec; lean: Rec; watchlist_live: Rec; all: Rec };
  series: Record<"watchlist" | "big_gap" | "all", { week: number; units: number }[]>;
  log: { week: number; id: number; away: string; home: string; pick: string; tier: Tier; gap: number; score: string | null; result: string; source: string }[];
};

export type TeamInfo = Omit<TeamRef, "school"> & { conference: string | null; level: string | null; mascot: string | null };
export type DirectoryTeam = TeamRef & { conference: string | null; level: string | null };

export type AtsSummary = { games: number; w: number; l: number; cover: number; noCover: number; push: number; pct: number };
export type TeamBetting = {
  summary: AtsSummary; fav: AtsSummary; dog: AtsSummary; mlProfit: number; atsProfit: number;
  log: { week: number; opp: string; home: boolean; role: string; line: number | null; score: string; result: string; ats: string; atsMargin: number }[];
};
export type TPlayer = { name: string; pos: string; team: string; stars: number | null; rating: number | null; stats?: Record<string, number> };
export type TeamDoc = {
  team: TeamRef; school: string; conference: string | null; mascot: string | null; level: string | null;
  stats: SeasonStats; returning: Returning;
  schedule: { id: number; week: number; kick: string; home: boolean; opp: string; us: number | null; them: number | null; line: string | null; hasPage: boolean }[];
  overview: { roster: number; recruits: number; transfersIn: number; transfersOut: number; drafted: number; byPosition: Record<string, number> };
  production: { pos: string; returning: number; lost: number; incoming: number }[];
  units: { Offense: number; Defense: number; "Special Teams": number; Total: number; byPosition: Record<string, number> };
  drafted: { name: string | null; pick: number; pos: string | null }[];
  transfersOut: TPlayer[]; transfersIn: TPlayer[];
  recruits: { name: string; pos: string; stars: number | null; rating: number | null; home: string }[];
  roster: { name: string; pos: string; grp: string; year: number | null; height: number | null; weight: number | null; jersey: number | null }[];
  portal: { in: { n: number; total: number; avg: number | null }; out: { n: number; total: number; avg: number | null };
    flowsIn: { team: string; n: number }[]; flowsOut: { team: string; n: number }[]; differential: { cat: string; stat: string; in: number; out: number }[] };
  betting: Record<string, TeamBetting>;
};

export type BettingFile = {
  season: number; final: boolean; gamesAnalyzed: number; graded: number; favProfit: number; dogProfit: number;
  rankings: { team: string; all: AtsSummary; fav: AtsSummary; dog: AtsSummary }[];
  upsets: { week: number; team: string; opp: string; home: boolean; line: number; score: string }[];
  nailBiters: { week: number; away: string; home: string; score: string; margin: number }[];
  bigCovers: { week: number; away: string; home: string; score: string; margin: number }[];
  outcomes: Record<string, number>;
  games: { week: number; home: string; away: string; homeScore: number | null; awayScore: number | null; line: string | null; category: string | null }[];
};

export type QbRow = {
  id: number; name: string; team: string; statTeam: string; conf: string; fbs: boolean;
  att: number; comp: number; yds: number; td: number; int: number; qbr: number | null;
  compPct: number | null; ypa: number | null; rating: number | null;
  radar: Record<"att" | "qbr" | "yds" | "td" | "int", number | null>;
  games: { week: number; opp: string; comp: number; att: number; yds: number; td: number; int: number; qbr: number | null }[];
  locations: QbLocations | null;
};
export type ZoneName = "deep left" | "deep middle" | "deep right" | "short left" | "short middle" | "short right";
export type ZoneStat = { att: number; comp: number; int: number; ypa: number | null; adot: number | null; success: number | null };
export type QbLocations = { zones: Record<ZoneName, ZoneStat>; unknown: number };
export type ZoneAvg = Record<ZoneName, { pct: number | null; share: number | null; ypa: number | null }>;
export type QbFile = { season: number; final: boolean; gamesPlayed: number; zoneAvg: ZoneAvg; qbs: QbRow[] };
export type PortalRow = { team: string; in: number; out: number; net: number; nIn: number; nOut: number };
export type CompareFile = { units: Record<string, { Offense: number; Defense: number; "Special Teams": number; Total: number }>; stats: Record<string, SeasonStats>; returning: Record<string, Returning> };
