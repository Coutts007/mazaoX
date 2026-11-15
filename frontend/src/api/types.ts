export type Role = "farmer" | "buyer" | "admin";

export interface User {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: Role;
  date_joined: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface Envelope<T> {
  data: T;
  pagination?: Pagination;
  unread_count?: number;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
}

export interface ListingImage {
  id: string;
  url: string;
  width: number;
  height: number;
  position: number;
}

export interface Listing {
  id: string;
  farmer_id: string;
  category: Category;
  produce_name: string;
  variety: string;
  description: string;
  declared_grade: string;
  grade_source: "farmer_declared";
  grade_verified: boolean;
  images: ListingImage[];
  availability: { available: string; in_stock: boolean } | null;
  price_per_unit: string;
  quantity_unit: string;
  county: string;
  locality: string;
  harvest_date: string | null;
  status: "active" | "inactive";
  moderation_hidden: boolean;
  moderation_reason: string;
  created_at: string;
  updated_at: string;
}

export interface PublicFarmer {
  id: string;
  full_name: string;
  farm_name: string;
  county: string;
  locality: string;
  bio: string;
  member_since: string;
}

export type OrderStatus = "pending_payment" | "paid" | "completed" | "cancelled" | "expired";

export interface OrderLine {
  listing_id: string;
  produce_name: string;
  unit_price: string;
  quantity: string;
  quantity_unit: string;
  line_total: string;
}

export interface Order {
  id: string;
  buyer_id: string;
  farmer_id: string;
  status: OrderStatus;
  delivery_method: "collection" | "delivery";
  delivery_location: string;
  total_amount: string;
  currency: string;
  lines: OrderLine[];
  payment_due_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderHistoryItem {
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface PaymentAttempt {
  id: string;
  order_id: string;
  amount: string;
  currency: string;
  status: "pending" | "succeeded" | "failed";
  failure_reason: string;
  mode: "simulated";
  created_at: string;
  completed_at: string | null;
}

export interface Delivery {
  id: string;
  order_id: string;
  method: string;
  location: string;
  status: "pending" | "dispatched" | "delivered" | "failed";
  events: { from_status: string; to_status: string; note: string; created_at: string }[];
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  kind: string;
  title: string;
  message: string;
  order_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface Issue {
  id: string;
  order_id: string;
  category: "quality" | "delivery" | "payment" | "other";
  description: string;
  status: "open" | "investigating" | "resolved" | "dismissed";
  resolution: string;
  created_at: string;
  updated_at: string;
}

export interface Review {
  id: string;
  order_id: string;
  rating: number;
  comment: string;
  created_at: string;
  reviewer_name?: string;
}

export interface ReviewList {
  summary?: { average_rating: number | null; review_count: number; distribution: Record<string, number> };
}

export interface Inspection {
  id: string;
  listing_id: string;
  source: string;
  inspected_on: string;
  scope: string;
  result: string;
  assessed_grade: string;
  notes: string;
  updated_at: string;
}

export interface DemandRequest {
  id: string;
  produce_name: string;
  quantity: string;
  quantity_unit: string;
  target_price_per_unit: string | null;
  county: string;
  required_by: string;
  status: "open" | "closed" | "expired";
  created_at: string;
}

export interface Match {
  score: number;
  reasons: string[];
  available: string;
  listing: Listing;
}

export interface Profile {
  county: string;
  locality: string;
  farm_name: string;
  bio: string;
  updated_at: string;
}

export interface StockSummary {
  listing_id: string;
  unit: string;
  on_hand: string;
  reserved: string;
  available: string;
}

export interface StockMovement {
  id: string;
  movement_type: "addition" | "correction" | "spoilage" | "sale";
  quantity_delta: string;
  resulting_on_hand: string;
  reason: string;
  order_id: string | null;
  created_at: string;
}

export interface MarketDemand extends DemandRequest {}

export interface AdminUser {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: "farmer" | "buyer" | "admin";
  is_active: boolean;
  date_joined: string;
}

export interface AdminReview {
  id: string;
  order_id: string;
  farmer_id: string;
  rating: number;
  comment: string;
  is_hidden: boolean;
  moderation_reason: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface AdminSummary {
  users: { total: number; by_role: Record<string, number>; suspended: number };
  listings: { total: number; active_visible: number; inactive: number; hidden_by_admin: number };
  orders: { total: number; by_status: Record<string, number>; paid_value_ksh: string };
  payments: { by_status: Record<string, number> };
  deliveries: { by_status: Record<string, number> };
  issues: { total: number; by_status: Record<string, number> };
  reviews: { total: number; hidden: number };
  inspections: { total: number; published: number };
  demand_requests: { by_status: Record<string, number> };
}
