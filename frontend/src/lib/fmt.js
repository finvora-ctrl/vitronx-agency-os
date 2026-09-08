// Indian Rupee + Indian number formatting utilities
export function fmtINR(n, opts = {}) {
  const num = Number(n) || 0;
  const decimals = opts.decimals ?? 0;
  // Indian grouping: 1,50,000 / 12,50,000
  const parts = num.toFixed(decimals).split(".");
  let x = parts[0];
  const neg = x.startsWith("-");
  if (neg) x = x.slice(1);
  const last3 = x.slice(-3);
  const rest = x.slice(0, -3);
  const grouped = rest ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + last3 : last3;
  const dec = parts[1] ? "." + parts[1] : "";
  return (neg ? "-" : "") + "₹" + grouped + dec;
}

export function fmtNumberIN(n) {
  const num = Number(n) || 0;
  const s = Math.round(num).toString();
  const neg = s.startsWith("-");
  const abs = neg ? s.slice(1) : s;
  const last3 = abs.slice(-3);
  const rest = abs.slice(0, -3);
  const grouped = rest ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + last3 : last3;
  return (neg ? "-" : "") + grouped;
}

export function fmtDateIN(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export const INDIAN_STATES = [
  "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat","Haryana",
  "Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra",
  "Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim",
  "Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",
];
