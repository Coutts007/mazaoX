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
