export type RankedAsset = {
  rank: number;
  symbol: string;
  name: string;
  price: number;
  change: number;
  volume: number;
  score: number;
  confidence: number;
  signal: "BULLISH" | "BEARISH" | "NEUTRAL";
  momentum: number;
};

export const rankedAssets: RankedAsset[] = [
  { rank: 1, symbol: "SOL", name: "Solana", price: 184.42, change: 12.84, volume: 3.86e9, score: 94.2, confidence: 0.91, signal: "BULLISH", momentum: 88 },
  { rank: 2, symbol: "INJ", name: "Injective", price: 27.61, change: 9.31, volume: 411e6, score: 91.7, confidence: 0.87, signal: "BULLISH", momentum: 85 },
  { rank: 3, symbol: "ETH", name: "Ethereum", price: 3421.78, change: 5.44, volume: 16.22e9, score: 88.5, confidence: 0.85, signal: "BULLISH", momentum: 76 },
  { rank: 4, symbol: "TIA", name: "Celestia", price: 8.17, change: 6.91, volume: 286e6, score: 84.8, confidence: 0.81, signal: "BULLISH", momentum: 79 },
  { rank: 5, symbol: "BTC", name: "Bitcoin", price: 103842.18, change: 2.18, volume: 39.3e9, score: 81.4, confidence: 0.89, signal: "BULLISH", momentum: 68 },
  { rank: 6, symbol: "ONDO", name: "Ondo", price: 1.18, change: -1.73, volume: 198e6, score: 68.1, confidence: 0.71, signal: "NEUTRAL", momentum: 51 },
  { rank: 7, symbol: "AVAX", name: "Avalanche", price: 35.6, change: -4.12, volume: 521e6, score: 43.9, confidence: 0.76, signal: "BEARISH", momentum: 29 },
  { rank: 8, symbol: "DOGE", name: "Dogecoin", price: 0.171, change: -6.44, volume: 1.47e9, score: 31.6, confidence: 0.68, signal: "BEARISH", momentum: 22 },
];

export const equityCurve = [
  { time: "00:00", value: 42 }, { time: "02:00", value: 48 }, { time: "04:00", value: 45 }, { time: "06:00", value: 59 },
  { time: "08:00", value: 55 }, { time: "10:00", value: 72 }, { time: "12:00", value: 68 }, { time: "14:00", value: 84 },
  { time: "16:00", value: 80 }, { time: "18:00", value: 93 }, { time: "20:00", value: 89 }, { time: "22:00", value: 97 },
];

export const heatmapAssets = [
  ["SOL", 12.8], ["INJ", 9.3], ["ETH", 5.4], ["TIA", 6.9], ["BTC", 2.2], ["ONDO", -1.7], ["AVAX", -4.1], ["DOGE", -6.4], ["LINK", 3.8], ["SUI", 7.1], ["AAVE", 4.5], ["ARB", -2.5],
] as const;
