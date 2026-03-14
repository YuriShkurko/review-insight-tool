export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const BUSINESS_TYPES = [
  "restaurant",
  "bar",
  "cafe",
  "gym",
  "salon",
  "hotel",
  "clinic",
  "retail",
  "other",
] as const;

export type BusinessType = (typeof BUSINESS_TYPES)[number];

export interface Business {
  id: string;
  place_id: string;
  name: string;
  business_type: string;
  address: string | null;
  google_maps_url: string | null;
  avg_rating: number | null;
  total_reviews: number;
  created_at: string;
  updated_at: string;
}

export interface Review {
  id: string;
  business_id: string;
  external_id: string;
  source: string;
  author: string | null;
  rating: number;
  text: string | null;
  published_at: string | null;
  created_at: string;
}

export interface InsightItem {
  label: string;
  count: number;
}

export interface Analysis {
  id: string;
  business_id: string;
  summary: string;
  top_complaints: InsightItem[];
  top_praise: InsightItem[];
  action_items: string[];
  risk_areas: string[];
  recommended_focus: string;
  created_at: string;
}

export interface Dashboard {
  business_name: string;
  business_type: string;
  address: string | null;
  avg_rating: number | null;
  total_reviews: number;
  top_complaints: InsightItem[];
  top_praise: InsightItem[];
  ai_summary: string | null;
  action_items: string[];
  risk_areas: string[];
  recommended_focus: string | null;
  analysis_created_at: string | null;
  last_updated_at: string | null;
}

export interface CompetitorRead {
  link_id: string;
  business: Business;
  has_reviews: boolean;
  has_analysis: boolean;
}

export interface BusinessSnapshot {
  business_id: string;
  name: string;
  business_type: string;
  avg_rating: number | null;
  total_reviews: number;
  summary: string;
  top_complaints: InsightItem[];
  top_praise: InsightItem[];
  action_items: string[];
  risk_areas: string[];
  recommended_focus: string;
}

export interface ComparisonResponse {
  target: BusinessSnapshot;
  competitors: BusinessSnapshot[];
  comparison_summary: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
}