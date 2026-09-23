import { format, isValid, parseISO, subYears } from "date-fns";

export function todayISO(date = new Date()): string {
  return format(date, "yyyy-MM-dd");
}

export function yearsAgoISO(years: number, date = new Date()): string {
  return format(subYears(date, years), "yyyy-MM-dd");
}

export function formatChartAxisDate(value: string): string {
  const date = parseISO(value);
  return isValid(date) ? format(date, "MMM yyyy") : value;
}

export function formatChartTooltipDate(value: string): string {
  const date = parseISO(value);
  return isValid(date) ? format(date, "MMM d, yyyy") : value;
}
