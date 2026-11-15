export const COUNTIES = [
  "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho",
  "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit",
  "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya",
  "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
];

export const UNITS: { value: string; label: string }[] = [
  { value: "kg", label: "kg" },
  { value: "bag", label: "bag" },
  { value: "tonne", label: "tonne" },
  { value: "crate", label: "crate" },
  { value: "piece", label: "piece" },
];

export const ORDER_STATUS_LABEL: Record<string, string> = {
  pending_payment: "Awaiting payment",
  paid: "Paid",
  completed: "Completed",
  cancelled: "Cancelled",
  expired: "Expired",
};

export const ORDER_STATUS_BADGE: Record<string, string> = {
  pending_payment: "b-low",
  paid: "b-ok",
  completed: "b-inspected",
  cancelled: "b-off",
  expired: "b-off",
};
