export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name: string }
  | { type: "component"; component: string; props: Record<string, unknown> }
  | { type: "alert"; severity: string; props: Record<string, unknown> }
  | { type: "done" };

export interface Leg {
  train_number: string;
  train_name: string;
  from_station: string;
  to_station: string;
  departure: string;
  arrival: string;
  departure_day_offset: number;
  arrival_day_offset: number;
  travel_class: string;
  status: string;
  seats_or_position: number;
  fare_per_passenger: number;
  waitlist_band: "confirm" | "probable" | "low";
  waitlist_probability: number;
  waitlist_type: string;
  waitlist_explanation: string;
}

export interface JourneyOption {
  direct: boolean;
  interchange: string | null;
  layover_minutes: number | null;
  legs: Leg[];
}

export interface OptionCardProps {
  ambiguous_stations: { query: string; candidates: string[] }[];
  options: JourneyOption[];
}

export interface Passenger {
  name: string;
  age: number;
  berth_preference: string | null;
}

export interface PaymentSheetProps {
  train_number: string;
  train_name: string;
  from_station: string;
  to_station: string;
  date: string;
  travel_class: string;
  status: string;
  seats_or_position: number;
  passengers: Passenger[];
  fare_per_passenger: number;
  total_fare: number;
  senior_citizen_note: string | null;
}

export interface PNRConfirmationProps {
  pnr: string;
  train_number: string;
  train_name: string;
  departure: string;
  date: string;
  travel_class: string;
  status: string;
  passengers: Passenger[];
  total_fare: number;
}

export interface AlertProps {
  severity?: string;
  message?: string;
  action?: string | null;
  tdr_deadline_iso?: string | null;
  clock_offset_seconds?: number;
  [key: string]: unknown;
}

export interface MessageComponent {
  component: string;
  props: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "agent";
  content: string;
  component?: MessageComponent | null;
}

export interface SessionResponse {
  session_id: string;
  messages: (ChatMessage & { created_at: string })[];
  clock_offset_seconds: number;
  journey: unknown;
  state: unknown;
  active_deadlines: unknown[];
}
